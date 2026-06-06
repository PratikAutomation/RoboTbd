"""Normalize vendor-specific sensor data to [-1, 1] common range."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class NormalizedReading:
    """Sensor reading normalized to [-1, 1] range."""

    robot_id: str
    joint_id: int
    metric: str
    raw_value: float
    normalized_value: float
    unit: str

    def __repr__(self) -> str:
        return (
            f"NormalizedReading({self.robot_id} J{self.joint_id} "
            f"{self.metric}={self.raw_value:.2f}{self.unit} "
            f"norm={self.normalized_value:.3f})"
        )


DEFAULT_RANGES: dict[str, tuple[float, float]] = {
    "position": (-6.2832, 6.2832),
    "velocity": (-3.14, 3.14),
    "torque": (-150.0, 150.0),
    "temperature": (20.0, 90.0),
    "current": (0.0, 10.0),
    "vibration": (0.0, 10.0),
}


class ObservationFormatter:
    """Normalize raw sensor values to [-1, 1] using known operational ranges."""

    def __init__(self, ranges: dict[str, tuple[float, float]] | None = None) -> None:
        self._ranges = ranges or DEFAULT_RANGES

    def normalize(
        self, robot_id: str, joint_id: int, metric: str, value: float, unit: str = "",
    ) -> NormalizedReading:
        """Normalize a raw value to [-1, 1]."""
        lo, hi = self._ranges.get(metric, (-1.0, 1.0))
        mid = (hi + lo) / 2.0
        half_range = (hi - lo) / 2.0
        norm = 0.0 if half_range == 0 else float(np.clip((value - mid) / half_range, -1.0, 1.0))

        return NormalizedReading(
            robot_id=robot_id, joint_id=joint_id, metric=metric,
            raw_value=value, normalized_value=norm, unit=unit,
        )

    def denormalize(self, metric: str, normalized: float) -> float:
        """Convert [-1, 1] back to raw value."""
        lo, hi = self._ranges.get(metric, (-1.0, 1.0))
        mid = (hi + lo) / 2.0
        half_range = (hi - lo) / 2.0
        return mid + normalized * half_range

    def __repr__(self) -> str:
        return f"ObservationFormatter(metrics={list(self._ranges.keys())})"
