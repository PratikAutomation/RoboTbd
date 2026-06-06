"""Prediction engine -- linear regression trend analysis for failure prediction."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import structlog

log = structlog.get_logger()

TIME_COMPRESSION = 12960.0  # 1 sim-second = 12960 real-seconds
WINDOW_SIZE = 60

CRITICAL_THRESHOLDS = {
    "temperature": 85.0,
    "vibration": 8.0,
    "torque": 140.0,
    "current": 9.5,
}


@dataclass
class Prediction:
    """Failure prediction for a specific metric."""

    robot_id: str
    joint_id: int
    metric: str
    days_to_failure: float | None
    confidence: float
    trend_slope: float
    current_value: float
    critical_threshold: float
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        if self.days_to_failure:
            return f"Prediction({self.robot_id} J{self.joint_id} {self.metric}: {self.days_to_failure:.0f}d, {self.confidence:.0%})"
        return f"Prediction({self.robot_id} J{self.joint_id} {self.metric}: no trend)"


class PredictionEngine:
    """Predict time-to-failure using linear regression on rolling windows."""

    def __init__(self, window_size: int = WINDOW_SIZE) -> None:
        self._window_size = window_size
        self._buffers: dict[str, deque[tuple[float, float]]] = {}
        self._predictions: dict[str, Prediction] = {}

    def add_sample(self, robot_id: str, joint_id: int, metric: str, value: float, timestamp: float | None = None) -> Prediction | None:
        """Add sample and recalculate prediction if enough data."""
        key = f"{robot_id}:J{joint_id}:{metric}"
        ts = timestamp or time.time()

        if key not in self._buffers:
            self._buffers[key] = deque(maxlen=self._window_size)
        self._buffers[key].append((ts, value))

        if len(self._buffers[key]) < 10:
            return None

        prediction = self._compute(robot_id, joint_id, metric)
        if prediction:
            self._predictions[key] = prediction
        return prediction

    def _compute(self, robot_id: str, joint_id: int, metric: str) -> Prediction | None:
        """Run linear regression and predict time to critical threshold."""
        key = f"{robot_id}:J{joint_id}:{metric}"
        buf = self._buffers.get(key)
        if not buf:
            return None

        threshold = CRITICAL_THRESHOLDS.get(metric)
        if not threshold:
            return None

        times = np.array([t for t, _ in buf])
        values = np.array([v for _, v in buf])

        t_offset = times[0]
        t_norm = times - t_offset

        n = len(t_norm)
        sum_t = np.sum(t_norm)
        sum_v = np.sum(values)
        sum_tv = np.sum(t_norm * values)
        sum_t2 = np.sum(t_norm ** 2)

        denom = n * sum_t2 - sum_t ** 2
        if abs(denom) < 1e-10:
            return None

        slope = (n * sum_tv - sum_t * sum_v) / denom
        intercept = (sum_v - slope * sum_t) / n

        y_pred = slope * t_norm + intercept
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        current_value = values[-1]
        days_to_failure = None

        if slope > 0 and current_value < threshold:
            remaining = threshold - current_value
            seconds_to_failure = remaining / slope
            real_seconds = seconds_to_failure * TIME_COMPRESSION
            days_to_failure = real_seconds / 86400.0
            log.info("prediction.computed", robot_id=robot_id, joint=joint_id,
                     metric=metric, days=round(days_to_failure, 1),
                     confidence=round(max(0, r_squared), 2))

        return Prediction(
            robot_id=robot_id, joint_id=joint_id, metric=metric,
            days_to_failure=round(days_to_failure, 1) if days_to_failure else None,
            confidence=round(max(0.0, min(1.0, r_squared)), 2),
            trend_slope=round(slope, 6), current_value=round(current_value, 2),
            critical_threshold=threshold,
        )

    def get_predictions(self) -> list[Prediction]:
        """Get all predictions with positive trends."""
        return [p for p in self._predictions.values() if p.days_to_failure is not None]

    def to_list(self) -> list[dict[str, Any]]:
        """Serialize predictions for API."""
        return [
            {
                "robot_id": p.robot_id, "joint_id": p.joint_id, "metric": p.metric,
                "days_to_failure": p.days_to_failure, "confidence": p.confidence,
                "trend_slope": p.trend_slope, "current_value": p.current_value,
                "critical_threshold": p.critical_threshold, "timestamp": p.timestamp,
            }
            for p in self.get_predictions()
        ]

    def __repr__(self) -> str:
        return f"PredictionEngine(active={len(self.get_predictions())})"
