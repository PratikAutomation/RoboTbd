"""Abstract base for data sources and common data types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable


@dataclass(frozen=True)
class SensorReading:
    """Single sensor reading from a robot."""

    robot_id: str
    node_id: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    unit: str = ""
    quality: str = "good"

    def __repr__(self) -> str:
        return f"SensorReading({self.robot_id}:{self.node_id}={self.value:.4f} {self.unit})"


class DataSource(ABC):
    """Abstract base for all robot data connectors."""

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id
        self._callbacks: list[Callable[[SensorReading], None]] = []
        self._running = False

    def on_reading(self, callback: Callable[[SensorReading], None]) -> None:
        """Register callback for new readings."""
        self._callbacks.append(callback)

    def _emit(self, reading: SensorReading) -> None:
        """Push reading to all registered callbacks."""
        for cb in self._callbacks:
            cb(reading)

    @abstractmethod
    async def connect(self) -> None:
        """Connect to data source."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from data source."""

    @abstractmethod
    async def subscribe(self, node_ids: list[str]) -> None:
        """Subscribe to specific data nodes."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.source_id}, running={self._running})"
