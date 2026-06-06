"""Robot health monitoring -- aggregate per-robot health scores."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class JointHealth:
    """Health state for a single joint."""

    joint_id: int
    position: float = 0.0
    velocity: float = 0.0
    torque: float = 0.0
    temperature: float = 25.0
    current: float = 0.0
    vibration: float = 0.0
    error_code: int = 0
    score: float = 100.0
    last_update: float = field(default_factory=time.time)


@dataclass
class RobotState:
    """Full state for one robot."""

    robot_id: str
    vendor: str
    model: str
    joints: dict[int, JointHealth] = field(default_factory=dict)
    status: str = "unknown"
    safety_state: str = "normal"
    health_score: float = 100.0
    last_update: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"RobotState({self.robot_id} {self.vendor}/{self.model} health={self.health_score:.0f})"


METRIC_THRESHOLDS: dict[str, dict[str, float]] = {
    "temperature": {"warning": 65.0, "critical": 80.0, "max": 90.0},
    "torque": {"warning": 100.0, "critical": 130.0, "max": 150.0},
    "vibration": {"warning": 4.0, "critical": 7.0, "max": 10.0},
    "current": {"warning": 7.0, "critical": 9.0, "max": 10.0},
}


class RobotHealthMonitor:
    """Track and score health for all robots in the fleet."""

    def __init__(self) -> None:
        self._robots: dict[str, RobotState] = {}

    def register_robot(self, robot_id: str, vendor: str, model: str, num_joints: int = 6) -> None:
        """Register a robot for monitoring."""
        state = RobotState(robot_id=robot_id, vendor=vendor, model=model)
        for j in range(1, num_joints + 1):
            state.joints[j] = JointHealth(joint_id=j)
        self._robots[robot_id] = state
        log.info("monitor.registered", robot_id=robot_id, vendor=vendor, model=model)

    def update_joint(self, robot_id: str, joint_id: int, metric: str, value: float) -> RobotState | None:
        """Update a single joint metric and recalculate health."""
        state = self._robots.get(robot_id)
        if not state:
            return None
        joint = state.joints.get(joint_id)
        if not joint:
            return None

        setattr(joint, metric, value)
        joint.last_update = time.time()
        joint.score = self._score_joint(joint)
        state.health_score = self._score_robot(state)
        state.last_update = time.time()
        return state

    def update_status(self, robot_id: str, status: str) -> None:
        """Update robot operational status."""
        state = self._robots.get(robot_id)
        if state:
            state.status = status

    def get_state(self, robot_id: str) -> RobotState | None:
        """Get current state for a robot."""
        return self._robots.get(robot_id)

    def get_all_states(self) -> dict[str, RobotState]:
        """Get states for all robots."""
        return dict(self._robots)

    def _score_joint(self, joint: JointHealth) -> float:
        """Score a single joint 0-100 based on all metrics."""
        scores: list[float] = []
        for metric, thresholds in METRIC_THRESHOLDS.items():
            val = abs(getattr(joint, metric, 0.0))
            warning = thresholds["warning"]
            critical = thresholds["critical"]
            max_val = thresholds["max"]

            if val <= warning:
                scores.append(100.0)
            elif val <= critical:
                ratio = (val - warning) / (critical - warning)
                scores.append(100.0 - ratio * 50.0)
            elif val <= max_val:
                ratio = (val - critical) / (max_val - critical)
                scores.append(50.0 - ratio * 50.0)
            else:
                scores.append(0.0)

        if joint.error_code != 0:
            scores.append(0.0)

        return min(100.0, max(0.0, sum(scores) / len(scores))) if scores else 100.0

    def _score_robot(self, state: RobotState) -> float:
        """Score: min(joints) * 0.4 + avg(joints) * 0.6. Bad joint drags score."""
        if not state.joints:
            return 100.0
        joint_scores = [j.score for j in state.joints.values()]
        return round(min(joint_scores) * 0.4 + (sum(joint_scores) / len(joint_scores)) * 0.6, 1)

    def to_dict(self) -> dict[str, Any]:
        """Serialize all robot states for API/WebSocket."""
        result = {}
        for rid, state in self._robots.items():
            result[rid] = {
                "robot_id": state.robot_id,
                "vendor": state.vendor,
                "model": state.model,
                "status": state.status,
                "safety_state": state.safety_state,
                "health_score": state.health_score,
                "last_update": state.last_update,
                "joints": {
                    jid: {
                        "joint_id": j.joint_id,
                        "position": round(j.position, 4),
                        "velocity": round(j.velocity, 4),
                        "torque": round(j.torque, 2),
                        "temperature": round(j.temperature, 1),
                        "current": round(j.current, 2),
                        "vibration": round(j.vibration, 3),
                        "error_code": j.error_code,
                        "score": round(j.score, 1),
                    }
                    for jid, j in state.joints.items()
                },
            }
        return result

    def __repr__(self) -> str:
        return f"RobotHealthMonitor(robots={list(self._robots.keys())})"
