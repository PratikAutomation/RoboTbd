"""Alarm engine -- threshold detection, deduplication, auto-resolve."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

log = structlog.get_logger()


@dataclass
class Alarm:
    """A single alarm instance."""

    alarm_id: str
    robot_id: str
    joint_id: int
    metric: str
    severity: str
    message: str
    value: float
    threshold: float
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_at: float | None = None

    def __repr__(self) -> str:
        status = "RESOLVED" if self.resolved else "ACTIVE"
        return f"Alarm({self.severity} {self.robot_id} J{self.joint_id} {self.metric} [{status}])"


ALARM_THRESHOLDS: dict[str, list[dict[str, Any]]] = {
    "temperature": [
        {"level": 65.0, "severity": "warning", "msg": "temperature elevated"},
        {"level": 80.0, "severity": "critical", "msg": "temperature critical"},
    ],
    "torque": [
        {"level": 100.0, "severity": "warning", "msg": "torque high"},
        {"level": 130.0, "severity": "critical", "msg": "torque critical"},
    ],
    "vibration": [
        {"level": 4.0, "severity": "warning", "msg": "vibration elevated"},
        {"level": 7.0, "severity": "critical", "msg": "vibration critical"},
    ],
    "current": [
        {"level": 7.0, "severity": "warning", "msg": "current draw high"},
        {"level": 9.0, "severity": "critical", "msg": "current critical"},
    ],
}

DEDUP_WINDOW = 30.0


class AlarmEngine:
    """Evaluate sensor values against thresholds, manage alarm lifecycle."""

    def __init__(self) -> None:
        self._active: dict[str, Alarm] = {}
        self._history: list[Alarm] = []
        self._last_fired: dict[str, float] = {}

    def evaluate(self, robot_id: str, joint_id: int, metric: str, value: float) -> list[Alarm]:
        """Check value against thresholds, return new alarms."""
        thresholds = ALARM_THRESHOLDS.get(metric, [])
        new_alarms: list[Alarm] = []
        now = time.time()

        for thresh in thresholds:
            key = f"{robot_id}:J{joint_id}:{metric}:{thresh['severity']}"

            if abs(value) >= thresh["level"]:
                last = self._last_fired.get(key, 0)
                if now - last < DEDUP_WINDOW and key in self._active:
                    continue

                alarm = Alarm(
                    alarm_id=f"ALM-{len(self._history) + 1:04d}",
                    robot_id=robot_id, joint_id=joint_id, metric=metric,
                    severity=thresh["severity"],
                    message=f"{robot_id} Joint {joint_id}: {thresh['msg']} ({value:.1f})",
                    value=value, threshold=thresh["level"],
                )
                self._active[key] = alarm
                self._history.append(alarm)
                self._last_fired[key] = now
                new_alarms.append(alarm)
                log.warning("alarm.fired", alarm_id=alarm.alarm_id,
                           robot_id=robot_id, joint=joint_id, metric=metric,
                           severity=thresh["severity"], value=value)
            else:
                if key in self._active and not self._active[key].resolved:
                    alarm = self._active[key]
                    alarm.resolved = True
                    alarm.resolved_at = now
                    log.info("alarm.resolved", alarm_id=alarm.alarm_id, robot_id=robot_id)

        return new_alarms

    def get_active(self) -> list[Alarm]:
        """Get all active (unresolved) alarms."""
        return [a for a in self._active.values() if not a.resolved]

    def get_history(self, limit: int = 50) -> list[Alarm]:
        """Get alarm history, newest first."""
        return list(reversed(self._history[-limit:]))

    def to_list(self) -> list[dict[str, Any]]:
        """Serialize active alarms for API."""
        return [
            {
                "alarm_id": a.alarm_id, "robot_id": a.robot_id,
                "joint_id": a.joint_id, "metric": a.metric,
                "severity": a.severity, "message": a.message,
                "value": round(a.value, 2), "threshold": a.threshold,
                "timestamp": a.timestamp, "resolved": a.resolved,
            }
            for a in self.get_active()
        ]

    def history_list(self, limit: int = 50) -> list[dict[str, Any]]:
        """Serialize alarm history for API."""
        return [
            {
                "alarm_id": a.alarm_id, "robot_id": a.robot_id,
                "joint_id": a.joint_id, "metric": a.metric,
                "severity": a.severity, "message": a.message,
                "value": round(a.value, 2), "threshold": a.threshold,
                "timestamp": a.timestamp, "resolved": a.resolved,
                "resolved_at": a.resolved_at,
            }
            for a in self.get_history(limit)
        ]

    def __repr__(self) -> str:
        return f"AlarmEngine(active={len(self.get_active())}, total={len(self._history)})"
