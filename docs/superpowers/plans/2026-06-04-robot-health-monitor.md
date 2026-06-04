# Robot Health Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time robot health monitoring dashboard with alarms and predictive failure detection, powered by simulated OPC-UA data, for a one-day hackathon demo.

**Architecture:** Four-layer stack. Simulated OPC-UA server (asyncua) generates realistic robot sensor data. RoboLink core subscribes, normalizes, and aggregates into health scores. Alarm and prediction engines detect anomalies and trend-based degradation. FastAPI streams events via WebSocket to a single-page vanilla JS dashboard.

**Tech Stack:** Python 3.11+, asyncua, FastAPI, uvicorn, structlog, numpy, Chart.js (bundled), vanilla JS.

**Spec:** `docs/superpowers/specs/2026-06-04-robot-health-monitor-design.md`

**Note:** Tests are deliberately skipped for hackathon timebox. Each task is verified manually. Add tests immediately post-hackathon.

---

## File Structure

```
robolink/
    __init__.py                 # Package init, version, public exports
    sources/
        __init__.py             # Sources subpackage
        base.py                 # Abstract DataSource base class
        opcua_source.py         # OPCUASource with asyncua subscriptions
    formatter.py                # ObservationFormatter (normalize to [-1,1])
    monitor.py                  # RobotHealthMonitor (aggregate, health score)
    alarms.py                   # AlarmEngine (thresholds, dedup, auto-resolve)
    prediction.py               # PredictionEngine (linear regression trends)
    utils/
        __init__.py             # Utils subpackage
        logging.py              # Structured logging via structlog

sim_server.py                   # OPC-UA simulation server + REST anomaly injection
server.py                       # FastAPI backend (WebSocket + REST)
dashboard/
    index.html                  # Self-contained dashboard (JS + Chart.js bundled)
requirements.txt                # Python dependencies
```

---

## Task 1: Project Scaffolding + Dependencies

**Files:**
- Create: `requirements.txt`
- Create: `robolink/__init__.py`
- Create: `robolink/sources/__init__.py`
- Create: `robolink/utils/__init__.py`
- Create: `robolink/utils/logging.py`

- [ ] **Step 1: Create requirements.txt**

```
asyncua>=1.1.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
structlog>=23.2.0
numpy>=1.26.0
```

- [ ] **Step 2: Create package structure**

`robolink/__init__.py`:
```python
"""RoboLink: Robot health monitoring from OPC-UA data."""

__version__ = "0.1.0"
```

`robolink/sources/__init__.py`:
```python
"""Data source connectors."""
```

`robolink/utils/__init__.py`:
```python
"""Utility modules."""
```

- [ ] **Step 3: Create structured logging setup**

`robolink/utils/logging.py`:
```python
"""Structured logging configuration via structlog."""

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog with console output."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.get_level_from_name(level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named logger."""
    return structlog.get_logger(name)
```

- [ ] **Step 4: Install dependencies and verify**

Run: `pip install -r requirements.txt`
Run: `python -c "import robolink; print(robolink.__version__)"`
Expected: `0.1.0`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt robolink/
git commit -m "feat: project scaffolding with package structure and logging"
```

---

## Task 2: Abstract DataSource Base Class

**Files:**
- Create: `robolink/sources/base.py`

- [ ] **Step 1: Write the abstract base class**

`robolink/sources/base.py`:
```python
"""Abstract base class for data sources."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable
from dataclasses import dataclass
from typing import Any


@dataclass
class SensorReading:
    """A single sensor reading from a data source."""

    robot_id: str
    joint: int
    metric: str
    value: float
    timestamp_ms: int
    source_id: str

    def __repr__(self) -> str:
        return (
            f"SensorReading({self.robot_id}.J{self.joint}.{self.metric}"
            f"={self.value:.2f})"
        )


class DataSource(ABC):
    """Abstract base for all data source connectors."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to data source."""

    @abstractmethod
    async def stream(
        self, callback: Callable[[SensorReading], Awaitable[None]]
    ) -> None:
        """Start streaming readings via callback. Blocks until stopped."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close connection."""

    @abstractmethod
    def __repr__(self) -> str: ...
```

- [ ] **Step 2: Verify import**

Run: `python -c "from robolink.sources.base import DataSource, SensorReading; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add robolink/sources/base.py
git commit -m "feat: abstract DataSource base class with SensorReading dataclass"
```

---

## Task 3: ObservationFormatter

**Files:**
- Create: `robolink/formatter.py`

- [ ] **Step 1: Write the formatter**

`robolink/formatter.py`:
```python
"""Normalize raw sensor values to [-1, 1] range."""

from dataclasses import dataclass


@dataclass
class NormalizationConfig:
    """Center and scale for normalizing a metric to [-1, 1]."""

    center: float
    scale: float

    def normalize(self, value: float) -> float:
        """Normalize value to [-1, 1]. Clamps to range."""
        normalized = (value - self.center) / self.scale
        return max(-1.0, min(1.0, normalized))

    def __repr__(self) -> str:
        return f"NormConfig(center={self.center}, scale={self.scale})"


# Default configs per metric type (from spec)
DEFAULT_METRIC_CONFIGS: dict[str, NormalizationConfig] = {
    "torque": NormalizationConfig(center=100.0, scale=100.0),
    "temperature": NormalizationConfig(center=70.0, scale=50.0),
    "vibration": NormalizationConfig(center=5.0, scale=5.0),
}


class ObservationFormatter:
    """Normalizes raw sensor readings to [-1, 1] range."""

    def __init__(
        self,
        configs: dict[str, NormalizationConfig] | None = None,
    ) -> None:
        self._configs = configs or DEFAULT_METRIC_CONFIGS

    def normalize(self, metric: str, value: float) -> float:
        """Normalize a single metric value. Returns raw if no config."""
        config = self._configs.get(metric)
        if config is None:
            return value
        return config.normalize(value)

    def __repr__(self) -> str:
        return f"ObservationFormatter(metrics={list(self._configs.keys())})"
```

- [ ] **Step 2: Verify normalization math**

Run:
```python
python -c "
from robolink.formatter import ObservationFormatter
f = ObservationFormatter()
# Temperature: center=70, scale=50. So 70->0.0, 120->1.0, 20->-1.0
print(f.normalize('temperature', 70.0))   # 0.0
print(f.normalize('temperature', 120.0))  # 1.0
print(f.normalize('temperature', 20.0))   # -1.0
print(f.normalize('temperature', 90.0))   # 0.4
print(f.normalize('vibration', 5.0))      # 0.0
print(f.normalize('vibration', 10.0))     # 1.0
print('OK')
"
```
Expected: `0.0`, `1.0`, `-1.0`, `0.4`, `0.0`, `1.0`, `OK`

- [ ] **Step 3: Commit**

```bash
git add robolink/formatter.py
git commit -m "feat: ObservationFormatter with configurable normalization"
```

---

## Task 4: AlarmEngine

**Files:**
- Create: `robolink/alarms.py`

- [ ] **Step 1: Write the alarm engine**

`robolink/alarms.py`:
```python
"""Alarm engine with thresholds, deduplication, and auto-resolve."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal
import uuid


@dataclass
class Alarm:
    """A single alarm event."""

    id: str
    robot_id: str
    severity: Literal["critical", "warning", "info"]
    message: str
    metric: str
    value: float
    threshold: float
    timestamp: datetime
    joint: int = -1
    resolved: bool = False
    resolved_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "robot_id": self.robot_id,
            "severity": self.severity,
            "message": self.message,
            "metric": self.metric,
            "value": round(self.value, 2),
            "threshold": self.threshold,
            "joint": self.joint,
            "timestamp": self.timestamp.isoformat(),
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }

    def __repr__(self) -> str:
        state = "RESOLVED" if self.resolved else self.severity.upper()
        return f"Alarm({state}: {self.robot_id} {self.message})"


@dataclass
class ThresholdRule:
    """Threshold rule for a metric."""

    metric: str
    warning: float | None = None
    critical: float | None = None
    compare: Literal["gt", "eq", "neq"] = "gt"


# Default thresholds from spec
DEFAULT_THRESHOLDS: list[ThresholdRule] = [
    ThresholdRule(metric="temperature", warning=75.0, critical=90.0),
    ThresholdRule(metric="vibration", warning=4.0, critical=7.0),
    ThresholdRule(metric="torque", warning=150.0, critical=180.0),
]


class AlarmEngine:
    """Evaluates sensor readings against thresholds. Deduplicates. Auto-resolves."""

    def __init__(
        self,
        thresholds: list[ThresholdRule] | None = None,
        dedup_window_s: float = 30.0,
    ) -> None:
        self._thresholds = {r.metric: r for r in (thresholds or DEFAULT_THRESHOLDS)}
        self._dedup_window = timedelta(seconds=dedup_window_s)
        self._active: dict[str, Alarm] = {}  # keyed by dedup_key
        self._history: list[Alarm] = []
        self._recently_resolved: list[str] = []

    def _dedup_key(self, robot_id: str, joint: int, metric: str, severity: str) -> str:
        return f"{robot_id}:{joint}:{metric}:{severity}"

    def evaluate(
        self,
        robot_id: str,
        joint: int,
        metric: str,
        value: float,
    ) -> Alarm | None:
        """Evaluate a reading. Returns new Alarm if threshold crossed, None otherwise."""
        rule = self._thresholds.get(metric)
        if rule is None:
            return None

        now = datetime.now()
        severity: str | None = None
        threshold: float = 0.0

        # Check critical first, then warning
        if rule.critical is not None and value > rule.critical:
            severity = "critical"
            threshold = rule.critical
        elif rule.warning is not None and value > rule.warning:
            severity = "warning"
            threshold = rule.warning

        if severity is None:
            # Value is normal -- auto-resolve any active alarms for this metric
            self._auto_resolve(robot_id, joint, metric, now)
            return None

        # Dedup check
        key = self._dedup_key(robot_id, joint, metric, severity)
        existing = self._active.get(key)
        if existing and not existing.resolved:
            if (now - existing.timestamp) < self._dedup_window:
                return None  # Suppress duplicate

        alarm = Alarm(
            id=f"a-{uuid.uuid4().hex[:8]}",
            robot_id=robot_id,
            severity=severity,
            message=f"Joint {joint} {metric} {value:.1f} exceeds {severity} threshold {threshold}",
            metric=metric,
            value=value,
            threshold=threshold,
            timestamp=now,
            joint=joint,
        )
        self._active[key] = alarm
        self._history.append(alarm)
        return alarm

    def evaluate_error_code(
        self,
        robot_id: str,
        joint: int,
        code: int,
    ) -> Alarm | None:
        """Evaluate error code. 0=OK, 1-100=warning, >100=critical."""
        if code == 0:
            return None

        now = datetime.now()
        severity = "critical" if code > 100 else "warning"
        key = self._dedup_key(robot_id, joint, "error_code", severity)

        existing = self._active.get(key)
        if existing and not existing.resolved:
            if (now - existing.timestamp) < self._dedup_window:
                return None

        alarm = Alarm(
            id=f"a-{uuid.uuid4().hex[:8]}",
            robot_id=robot_id,
            severity=severity,
            message=f"Joint {joint} error code {code}",
            metric="error_code",
            value=float(code),
            threshold=100.0 if severity == "critical" else 1.0,
            timestamp=now,
            joint=joint,
        )
        self._active[key] = alarm
        self._history.append(alarm)
        return alarm

    def evaluate_system(
        self,
        node: str,
        value: str,
    ) -> Alarm | None:
        """Evaluate system-level nodes (gateway status, etc.)."""
        now = datetime.now()
        if node == "gateway_status" and value == "offline":
            key = "system:gateway:offline"
            existing = self._active.get(key)
            if existing and not existing.resolved:
                return None
            alarm = Alarm(
                id=f"a-{uuid.uuid4().hex[:8]}",
                robot_id="system",
                severity="critical",
                message="Gateway offline",
                metric="gateway_status",
                value=0.0,
                threshold=0.0,
                timestamp=now,
            )
            self._active[key] = alarm
            self._history.append(alarm)
            return alarm
        elif node == "gateway_status" and value == "online":
            key = "system:gateway:offline"
            if key in self._active and not self._active[key].resolved:
                self._active[key].resolved = True
                self._active[key].resolved_at = now
                return None
        return None

    def _auto_resolve(
        self,
        robot_id: str,
        joint: int,
        metric: str,
        now: datetime,
    ) -> list[str]:
        """Auto-resolve active alarms for this robot/joint/metric."""
        for severity in ("warning", "critical"):
            key = self._dedup_key(robot_id, joint, metric, severity)
            alarm = self._active.get(key)
            if alarm and not alarm.resolved:
                alarm.resolved = True
                alarm.resolved_at = now
                self._recently_resolved.append(alarm.id)

    def pop_resolved(self) -> list[str]:
        """Return and clear list of alarm IDs resolved since last call."""
        ids = self._recently_resolved.copy()
        self._recently_resolved.clear()
        return ids

    def get_active(self) -> list[Alarm]:
        return [a for a in self._active.values() if not a.resolved]

    def get_history(self, limit: int = 50) -> list[Alarm]:
        return self._history[-limit:]

    def __repr__(self) -> str:
        active = len(self.get_active())
        total = len(self._history)
        return f"AlarmEngine(active={active}, total={total})"
```

- [ ] **Step 2: Verify alarm engine**

Run:
```python
python -c "
from robolink.alarms import AlarmEngine
e = AlarmEngine()
# Normal value -- no alarm
a = e.evaluate('Robot1', 3, 'temperature', 50.0)
print(f'Normal: {a}')  # None
# Warning
a = e.evaluate('Robot1', 3, 'temperature', 78.0)
print(f'Warning: {a}')  # Alarm
# Dedup
a = e.evaluate('Robot1', 3, 'temperature', 79.0)
print(f'Dedup: {a}')    # None (within 30s)
# Critical
a = e.evaluate('Robot1', 3, 'temperature', 95.0)
print(f'Critical: {a}') # Alarm (different severity)
print(f'Active: {len(e.get_active())}')
print('OK')
"
```
Expected: `Normal: None`, `Warning: Alarm(...)`, `Dedup: None`, `Critical: Alarm(...)`, `Active: 2`, `OK`

- [ ] **Step 3: Commit**

```bash
git add robolink/alarms.py
git commit -m "feat: AlarmEngine with thresholds, dedup, and auto-resolve"
```

---

## Task 5: PredictionEngine

**Files:**
- Create: `robolink/prediction.py`

- [ ] **Step 1: Write the prediction engine**

`robolink/prediction.py`:
```python
"""Prediction engine using linear regression on rolling sensor windows."""

from collections import defaultdict, deque
from dataclasses import dataclass
import numpy as np


@dataclass
class FailurePrediction:
    """A predicted failure for a specific joint metric."""

    robot_id: str
    joint: int
    metric: str
    current_value: float
    trend_slope: float
    predicted_failure_value: float
    days_to_failure: float
    confidence: float

    def to_dict(self) -> dict:
        return {
            "robot_id": self.robot_id,
            "joint": self.joint,
            "metric": self.metric,
            "current_value": round(self.current_value, 2),
            "trend_slope": round(self.trend_slope, 6),
            "predicted_failure_value": self.predicted_failure_value,
            "days_to_failure": round(self.days_to_failure, 1),
            "confidence": round(self.confidence, 2),
        }

    def __repr__(self) -> str:
        return (
            f"Prediction({self.robot_id}.J{self.joint}.{self.metric}: "
            f"{self.days_to_failure:.1f} days, {self.confidence:.0%})"
        )


# Critical thresholds per metric (value at which failure occurs)
CRITICAL_THRESHOLDS: dict[str, float] = {
    "temperature": 90.0,
    "vibration": 7.0,
    "torque": 180.0,
}

# Minimum slope (units/sec) to consider a trend concerning
MIN_SLOPE_THRESHOLDS: dict[str, float] = {
    "temperature": 0.01,
    "vibration": 0.005,
    "torque": 0.05,
}


class PredictionEngine:
    """Detects degradation trends via linear regression on rolling windows."""

    def __init__(
        self,
        window_size: int = 60,
        min_confidence: float = 0.6,
        time_compression_factor: float = 12960.0,
    ) -> None:
        self._window_size = window_size
        self._min_confidence = min_confidence
        self._compression = time_compression_factor
        # key: (robot_id, joint, metric) -> deque of (timestamp_s, value)
        self._windows: dict[tuple[str, int, str], deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._active: dict[tuple[str, int, str], FailurePrediction] = {}

    def update(
        self,
        robot_id: str,
        joint: int,
        metric: str,
        value: float,
        timestamp_s: float,
    ) -> FailurePrediction | None:
        """Add a data point. Returns prediction if degradation trend detected."""
        if metric not in CRITICAL_THRESHOLDS:
            return None

        key = (robot_id, joint, metric)
        self._windows[key].append((timestamp_s, value))

        window = self._windows[key]
        if len(window) < 10:  # Need minimum data for regression
            return None

        # Linear regression
        times = np.array([t for t, _ in window])
        values = np.array([v for _, v in window])

        # Normalize times to start at 0
        times = times - times[0]

        n = len(times)
        sum_x = np.sum(times)
        sum_y = np.sum(values)
        sum_xy = np.sum(times * values)
        sum_x2 = np.sum(times**2)

        denom = n * sum_x2 - sum_x**2
        if abs(denom) < 1e-10:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R-squared for confidence
        y_pred = slope * times + intercept
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0.0

        # Check if trend is concerning
        min_slope = MIN_SLOPE_THRESHOLDS.get(metric, 0.01)
        critical = CRITICAL_THRESHOLDS[metric]

        if slope <= min_slope or value >= critical:
            # Not trending up, or already past critical
            self._active.pop(key, None)
            return None

        if r_squared < self._min_confidence:
            self._active.pop(key, None)
            return None

        # Extrapolate to critical threshold
        remaining = critical - value
        if remaining <= 0:
            self._active.pop(key, None)
            return None

        # slope is in units/sim-second
        # real_seconds = sim_seconds * compression_factor
        sim_seconds_to_failure = remaining / slope
        real_seconds_to_failure = sim_seconds_to_failure * self._compression
        days_to_failure = real_seconds_to_failure / 86400.0

        prediction = FailurePrediction(
            robot_id=robot_id,
            joint=joint,
            metric=metric,
            current_value=value,
            trend_slope=slope,
            predicted_failure_value=critical,
            days_to_failure=days_to_failure,
            confidence=r_squared,
        )
        self._active[key] = prediction
        return prediction

    def get_predictions(self, robot_id: str | None = None) -> list[FailurePrediction]:
        """Get active predictions, optionally filtered by robot."""
        if robot_id is None:
            return list(self._active.values())
        return [p for p in self._active.values() if p.robot_id == robot_id]

    def __repr__(self) -> str:
        return f"PredictionEngine(active={len(self._active)}, windows={len(self._windows)})"
```

- [ ] **Step 2: Verify prediction engine with synthetic data**

Run:
```python
python -c "
from robolink.prediction import PredictionEngine
p = PredictionEngine(window_size=30, min_confidence=0.5, time_compression_factor=12960.0)
# Simulate gradual temperature climb: 60 -> 78 over 20 points
result = None
for i in range(20):
    t = i * 0.5  # 0.5s intervals
    val = 60.0 + i * 0.9  # climbing
    result = p.update('Robot2', 3, 'temperature', val, t)
if result:
    print(f'Prediction: {result.days_to_failure:.1f} days, confidence={result.confidence:.2f}')
    print(f'Slope: {result.trend_slope:.4f}')
else:
    print('No prediction yet')
print(f'Active: {len(p.get_predictions())}')
print('OK')
"
```
Expected: A prediction with days_to_failure > 0, confidence > 0.5, `OK`

- [ ] **Step 3: Commit**

```bash
git add robolink/prediction.py
git commit -m "feat: PredictionEngine with linear regression and time compression"
```

---

## Task 6: RobotHealthMonitor

**Files:**
- Create: `robolink/monitor.py`

- [ ] **Step 1: Write the health monitor**

`robolink/monitor.py`:
```python
"""Robot health monitor: aggregates sensor data into per-robot health scores."""

from collections import defaultdict
from dataclasses import dataclass, field

from robolink.alarms import AlarmEngine, Alarm
from robolink.prediction import PredictionEngine, FailurePrediction
from robolink.formatter import ObservationFormatter


# Metric weights for per-joint health scoring
METRIC_WEIGHTS: dict[str, float] = {
    "temperature": 0.3,
    "vibration": 0.3,
    "torque": 0.25,
    "error_code": 0.15,
}

# Healthy baseline ranges (value at which metric scores 100)
HEALTHY_BASELINES: dict[str, tuple[float, float]] = {
    # (ideal_value, critical_value) -- score maps linearly from 100 to 0
    "temperature": (40.0, 90.0),
    "vibration": (1.5, 7.0),
    "torque": (80.0, 180.0),
}


@dataclass
class JointState:
    """Current state of a single joint."""

    torque: float = 80.0
    temperature: float = 40.0
    vibration: float = 1.5
    error_code: int = 0


@dataclass
class RobotState:
    """Current state of a robot."""

    robot_id: str
    joints: dict[int, JointState] = field(default_factory=dict)
    status: str = "running"
    health_score: float = 100.0

    def to_dict(self) -> dict:
        joints_dict = {}
        for j, state in self.joints.items():
            joints_dict[j] = {
                "torque": round(state.torque, 2),
                "temperature": round(state.temperature, 2),
                "vibration": round(state.vibration, 3),
                "error_code": state.error_code,
            }
        return {
            "robot_id": self.robot_id,
            "joints": joints_dict,
            "status": self.status,
            "health_score": round(self.health_score, 1),
        }


@dataclass
class HealthEvent:
    """Event emitted when health state changes."""

    robot_id: str
    health_score: float
    alarm: Alarm | None = None
    prediction: FailurePrediction | None = None
    resolved_alarm_id: str | None = None


class RobotHealthMonitor:
    """Aggregates sensor readings into per-robot health scores.

    Coordinates with AlarmEngine and PredictionEngine.
    """

    def __init__(
        self,
        alarm_engine: AlarmEngine | None = None,
        prediction_engine: PredictionEngine | None = None,
        formatter: ObservationFormatter | None = None,
    ) -> None:
        self.alarm_engine = alarm_engine or AlarmEngine()
        self.prediction_engine = prediction_engine or PredictionEngine()
        self.formatter = formatter or ObservationFormatter()
        self._robots: dict[str, RobotState] = {}

    def _ensure_robot(self, robot_id: str) -> RobotState:
        if robot_id not in self._robots:
            self._robots[robot_id] = RobotState(
                robot_id=robot_id,
                joints={j: JointState() for j in range(1, 7)},
            )
        return self._robots[robot_id]

    def update(
        self,
        robot_id: str,
        joint: int,
        metric: str,
        value: float,
        timestamp_s: float,
    ) -> HealthEvent:
        """Process a sensor reading. Returns health event with any triggered alarms/predictions."""
        robot = self._ensure_robot(robot_id)

        # Update joint state
        if joint in robot.joints:
            joint_state = robot.joints[joint]
            match metric:
                case "torque":
                    joint_state.torque = value
                case "temperature":
                    joint_state.temperature = value
                case "vibration":
                    joint_state.vibration = value
                case "error_code":
                    joint_state.error_code = int(value)

        # Compute health score
        robot.health_score = self._compute_health_score(robot)

        # Check alarms
        alarm = None
        if metric == "error_code":
            alarm = self.alarm_engine.evaluate_error_code(robot_id, joint, int(value))
        elif metric in ("temperature", "vibration", "torque"):
            alarm = self.alarm_engine.evaluate(robot_id, joint, metric, value)

        # Check predictions
        prediction = self.prediction_engine.update(
            robot_id, joint, metric, value, timestamp_s
        )

        # Update robot status based on health
        if robot.health_score < 40:
            robot.status = "critical"
        elif robot.health_score < 70:
            robot.status = "warning"
        else:
            robot.status = "running"

        return HealthEvent(
            robot_id=robot_id,
            health_score=robot.health_score,
            alarm=alarm,
            prediction=prediction,
        )

    def _compute_health_score(self, robot: RobotState) -> float:
        """Compute health: min(joint_scores) * 0.4 + avg(joint_scores) * 0.6"""
        joint_scores = []
        for joint_state in robot.joints.values():
            score = self._compute_joint_score(joint_state)
            joint_scores.append(score)

        if not joint_scores:
            return 100.0

        min_score = min(joint_scores)
        avg_score = sum(joint_scores) / len(joint_scores)
        return min_score * 0.4 + avg_score * 0.6

    def _compute_joint_score(self, joint: JointState) -> float:
        """Compute 0-100 score for a single joint from weighted metrics."""
        scores: dict[str, float] = {}

        for metric_name, (ideal, critical) in HEALTHY_BASELINES.items():
            value = getattr(joint, metric_name, ideal)
            # Linear map: ideal -> 100, critical -> 0
            if abs(critical - ideal) < 1e-10:
                scores[metric_name] = 100.0
            else:
                ratio = (value - ideal) / (critical - ideal)
                scores[metric_name] = max(0.0, min(100.0, 100.0 * (1.0 - ratio)))

        # Error code: 0 -> 100, non-zero -> 30, >100 -> 0
        if joint.error_code == 0:
            scores["error_code"] = 100.0
        elif joint.error_code > 100:
            scores["error_code"] = 0.0
        else:
            scores["error_code"] = 30.0

        # Weighted combination
        total = 0.0
        for metric_name, weight in METRIC_WEIGHTS.items():
            total += scores.get(metric_name, 100.0) * weight
        return total

    def get_robot_state(self, robot_id: str) -> RobotState | None:
        return self._robots.get(robot_id)

    def get_all_states(self) -> list[RobotState]:
        return list(self._robots.values())

    def __repr__(self) -> str:
        return f"RobotHealthMonitor(robots={len(self._robots)})"
```

- [ ] **Step 2: Verify health scoring**

Run:
```python
python -c "
from robolink.monitor import RobotHealthMonitor
m = RobotHealthMonitor()
import time
t = time.time()
# Normal reading
e = m.update('Robot1', 1, 'temperature', 42.0, t)
print(f'Normal health: {e.health_score:.1f}')  # ~95+
# Hot joint
e = m.update('Robot1', 3, 'temperature', 82.0, t+1)
print(f'Hot joint health: {e.health_score:.1f}')  # drops significantly
print(f'Alarm: {e.alarm}')  # warning alarm
# Critical vibration
e = m.update('Robot1', 5, 'vibration', 8.0, t+2)
print(f'Critical health: {e.health_score:.1f}')  # drops more
print(f'Alarm: {e.alarm}')  # critical alarm
print('OK')
"
```
Expected: decreasing health scores, alarms firing, `OK`

- [ ] **Step 3: Commit**

```bash
git add robolink/monitor.py
git commit -m "feat: RobotHealthMonitor with health scoring, alarm/prediction coordination"
```

---

## Task 7: OPCUASource

**Files:**
- Create: `robolink/sources/opcua_source.py`

- [ ] **Step 1: Write the OPC-UA source**

`robolink/sources/opcua_source.py`:
```python
"""OPC-UA data source using asyncua subscriptions."""

import asyncio
import re
import time

from asyncua import Client, ua
from asyncua.common.subscription import SubHandler

from robolink.sources.base import DataSource, SensorReading
from robolink.utils.logging import get_logger

log = get_logger("opcua_source")

# Pattern to parse node IDs like Factory.Robot1.Joint3.Temperature
NODE_PATTERN = re.compile(
    r"Factory\.(?P<robot>Robot\d+)\.Joint(?P<joint>\d+)\.(?P<metric>\w+)"
)
SYSTEM_PATTERN = re.compile(
    r"Factory\.(?P<node>Gateway\.Status|Line\.State|Robot\d+\.Status)"
)


class _SubscriptionHandler(SubHandler):
    """Handles OPC-UA data change notifications."""

    def __init__(self, callback: asyncio.coroutines) -> None:
        self._callback = callback
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def datachange_notification(self, node, val, data) -> None:
        if self._loop is None:
            return
        node_id = node.nodeid.Identifier
        if isinstance(node_id, str):
            asyncio.run_coroutine_threadsafe(
                self._callback(node_id, val), self._loop
            )


class OPCUASource(DataSource):
    """Connects to OPC-UA server and streams sensor readings via subscription.

    Parses node IDs matching Factory.Robot{N}.Joint{M}.{Metric} pattern
    into structured SensorReading objects.
    """

    def __init__(
        self,
        endpoint: str,
        subscription_interval_ms: int = 50,
    ) -> None:
        self._endpoint = endpoint
        self._interval_ms = subscription_interval_ms
        self._client: Client | None = None
        self._subscription = None
        self._running = False
        self._callback = None
        self._system_callback = None

    async def connect(self) -> None:
        """Connect to OPC-UA server."""
        log.info("connecting", endpoint=self._endpoint)
        self._client = Client(url=self._endpoint)
        await self._client.connect()
        log.info("connected", endpoint=self._endpoint)

    async def stream(self, callback, system_callback=None) -> None:
        """Subscribe to all Factory.* nodes and stream readings."""
        if self._client is None:
            raise RuntimeError("Not connected. Call connect() first.")

        self._callback = callback
        self._system_callback = system_callback
        self._running = True
        loop = asyncio.get_event_loop()

        handler = _SubscriptionHandler(self._on_data_change)
        handler.set_loop(loop)

        self._subscription = await self._client.create_subscription(
            self._interval_ms, handler
        )

        # Browse for all nodes under ns=2
        root = self._client.get_objects_node()
        nodes = await self._browse_recursive(root)
        log.info("subscribing", node_count=len(nodes))

        if nodes:
            await self._subscription.subscribe_data_change(nodes)

        # Keep alive until stopped
        while self._running:
            await asyncio.sleep(0.1)

    async def _browse_recursive(self, node, depth: int = 0):
        """Browse for all variable nodes under the given node."""
        if depth > 5:
            return []
        found = []
        children = await node.get_children()
        for child in children:
            node_class = await child.read_node_class()
            if node_class == ua.NodeClass.Variable:
                found.append(child)
            elif node_class == ua.NodeClass.Object:
                found.extend(await self._browse_recursive(child, depth + 1))
        return found

    async def _on_data_change(self, node_id: str, value) -> None:
        """Parse node ID and dispatch to appropriate callback."""
        # Try sensor reading pattern
        match = NODE_PATTERN.search(node_id)
        if match and self._callback:
            reading = SensorReading(
                robot_id=match.group("robot"),
                joint=int(match.group("joint")),
                metric=match.group("metric").lower(),
                value=float(value) if not isinstance(value, str) else 0.0,
                timestamp_ms=int(time.time() * 1000),
                source_id=self._endpoint,
            )
            await self._callback(reading)
            return

        # Try system node pattern
        sys_match = SYSTEM_PATTERN.search(node_id)
        if sys_match and self._system_callback:
            await self._system_callback(sys_match.group("node"), str(value))

    async def disconnect(self) -> None:
        """Stop streaming and disconnect."""
        self._running = False
        if self._subscription:
            await self._subscription.delete()
        if self._client:
            await self._client.disconnect()
        log.info("disconnected", endpoint=self._endpoint)

    def __repr__(self) -> str:
        state = "connected" if self._client else "disconnected"
        return f"OPCUASource({self._endpoint}, {state})"
```

- [ ] **Step 2: Verify import (can't test without server yet)**

Run: `python -c "from robolink.sources.opcua_source import OPCUASource; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add robolink/sources/opcua_source.py
git commit -m "feat: OPCUASource with asyncua subscriptions and node ID parsing"
```

---

## Task 8: Simulated OPC-UA Server

**Files:**
- Create: `sim_server.py`

- [ ] **Step 1: Write the simulation server**

`sim_server.py`:
```python
"""Simulated OPC-UA server for 3 robot arms with anomaly injection.

Runs an OPC-UA server (asyncua) with 72 sensor nodes (3 robots x 6 joints x 4 metrics)
and a REST API (uvicorn) for triggering anomaly scenarios.

Usage:
    python sim_server.py [--port 4840] [--rest-port 8081]
"""

import argparse
import asyncio
import math
import random
import time
from contextlib import asynccontextmanager
from enum import Enum

from asyncua import Server, ua
import uvicorn
from fastapi import FastAPI

# --- Simulation Config ---

NUM_ROBOTS = 3
NUM_JOINTS = 6

HEALTHY_RANGES: dict[str, tuple[float, float]] = {
    "Torque": (60.0, 100.0),
    "Temperature": (35.0, 55.0),
    "Vibration": (1.0, 2.5),
}

UPDATE_INTERVAL_S = 0.5  # Batch updates at 500ms for WebSocket throttling


class Scenario(str, Enum):
    GRADUAL_DEGRADATION = "gradual_degradation"
    SUDDEN_VIBRATION = "sudden_vibration"
    GATEWAY_OFFLINE = "gateway_offline"


# --- Globals ---

_server: Server | None = None
_nodes: dict[str, any] = {}
_active_scenarios: set[Scenario] = set()
_scenario_start_times: dict[Scenario, float] = {}


# --- OPC-UA Server Setup ---

async def create_opcua_server(port: int) -> Server:
    server = Server()
    await server.init()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{port}/robolink/server")
    server.set_server_name("RoboLink Sim Server")

    uri = "http://robolink.io/sim"
    idx = await server.register_namespace(uri)

    objects = server.nodes.objects
    factory = await objects.add_object(idx, "Factory")

    # Create robot nodes
    for r in range(1, NUM_ROBOTS + 1):
        robot_obj = await factory.add_object(idx, f"Robot{r}")
        for j in range(1, NUM_JOINTS + 1):
            joint_obj = await robot_obj.add_object(idx, f"Joint{j}")
            for metric in ("Torque", "Temperature", "Vibration"):
                low, high = HEALTHY_RANGES[metric]
                initial = (low + high) / 2
                node = await joint_obj.add_variable(
                    idx, metric, initial, ua.VariantType.Float
                )
                await node.set_writable()
                _nodes[f"Factory.Robot{r}.Joint{j}.{metric}"] = node

            # Error code
            err_node = await joint_obj.add_variable(
                idx, "ErrorCode", 0, ua.VariantType.Int32
            )
            await err_node.set_writable()
            _nodes[f"Factory.Robot{r}.Joint{j}.ErrorCode"] = err_node

        # Robot status
        status_node = await robot_obj.add_variable(
            idx, "Status", "running", ua.VariantType.String
        )
        await status_node.set_writable()
        _nodes[f"Factory.Robot{r}.Status"] = status_node

    # System nodes (object + child variable to match spec node IDs)
    gw_obj = await factory.add_object(idx, "Gateway")
    gw_node = await gw_obj.add_variable(
        idx, "Status", "online", ua.VariantType.String
    )
    await gw_node.set_writable()
    _nodes["Factory.Gateway.Status"] = gw_node

    line_obj = await factory.add_object(idx, "Line")
    line_node = await line_obj.add_variable(
        idx, "State", "production", ua.VariantType.String
    )
    await line_node.set_writable()
    _nodes["Factory.Line.State"] = line_node

    return server


async def update_loop():
    """Main simulation loop. Updates all sensor nodes with realistic values."""
    t = 0.0
    while True:
        for r in range(1, NUM_ROBOTS + 1):
            for j in range(1, NUM_JOINTS + 1):
                for metric in ("Torque", "Temperature", "Vibration"):
                    value = _compute_value(r, j, metric, t)
                    node_key = f"Factory.Robot{r}.Joint{j}.{metric}"
                    if node_key in _nodes:
                        await _nodes[node_key].write_value(
                            ua.DataValue(ua.Variant(value, ua.VariantType.Float))
                        )

        # Handle active scenarios
        await _process_scenarios(t)

        t += UPDATE_INTERVAL_S
        await asyncio.sleep(UPDATE_INTERVAL_S)


def _compute_value(robot: int, joint: int, metric: str, t: float) -> float:
    """Compute a realistic sensor value with noise and oscillation."""
    low, high = HEALTHY_RANGES[metric]
    center = (low + high) / 2
    amplitude = (high - low) / 4

    # Each robot/joint has a unique phase offset
    phase = (robot * 7 + joint * 13) * 0.1
    base = center + amplitude * math.sin(t * 0.3 + phase)
    noise = random.gauss(0, amplitude * 0.1)

    value = base + noise

    # Apply scenario effects
    if Scenario.GRADUAL_DEGRADATION in _active_scenarios:
        if robot == 2 and joint == 3 and metric == "Temperature":
            elapsed = t - _scenario_start_times.get(Scenario.GRADUAL_DEGRADATION, t)
            value += elapsed * 0.1  # 0.1 C/sec climb

    if Scenario.SUDDEN_VIBRATION in _active_scenarios:
        if robot == 3 and joint == 5 and metric == "Vibration":
            value = random.uniform(6.0, 9.0)  # 3x baseline

    return round(max(0.0, value), 3)


async def _process_scenarios(t: float):
    """Process system-level scenario effects."""
    if Scenario.GATEWAY_OFFLINE in _active_scenarios:
        gw_node = _nodes.get("Factory.Gateway.Status")
        if gw_node:
            await gw_node.write_value(
                ua.DataValue(ua.Variant("offline", ua.VariantType.String))
            )


# --- REST API for Anomaly Injection ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

rest_app = FastAPI(title="RoboLink Sim Control", lifespan=lifespan)


@rest_app.post("/inject/{scenario}")
async def inject_scenario(scenario: Scenario):
    """Activate an anomaly scenario."""
    _active_scenarios.add(scenario)
    _scenario_start_times[scenario] = time.time()
    return {"status": "activated", "scenario": scenario.value}


@rest_app.post("/clear")
async def clear_scenarios():
    """Clear all active scenarios."""
    _active_scenarios.clear()
    _scenario_start_times.clear()
    # Reset gateway
    gw_node = _nodes.get("Factory.Gateway.Status")
    if gw_node:
        await gw_node.write_value(
            ua.DataValue(ua.Variant("online", ua.VariantType.String))
        )
    return {"status": "cleared"}


@rest_app.get("/status")
async def get_status():
    return {
        "active_scenarios": [s.value for s in _active_scenarios],
        "nodes": len(_nodes),
    }


# --- Main ---

async def run_server(opcua_port: int, rest_port: int):
    global _server
    _server = await create_opcua_server(opcua_port)
    await _server.start()
    print(f"OPC-UA server running on opc.tcp://0.0.0.0:{opcua_port}/robolink/server")
    print(f"REST control API on http://0.0.0.0:{rest_port}")

    # Start update loop
    asyncio.create_task(update_loop())

    # Run REST API
    config = uvicorn.Config(rest_app, host="0.0.0.0", port=rest_port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


def main():
    parser = argparse.ArgumentParser(description="RoboLink OPC-UA Simulation Server")
    parser.add_argument("--port", type=int, default=4840, help="OPC-UA port")
    parser.add_argument("--rest-port", type=int, default=8081, help="REST API port")
    args = parser.parse_args()
    asyncio.run(run_server(args.port, args.rest_port))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Start sim server and verify**

Run in terminal 1: `python sim_server.py --port 4840 --rest-port 8081`
Expected: "OPC-UA server running..." and "REST control API on..."

Run in terminal 2:
```bash
curl http://localhost:8081/status
```
Expected: `{"active_scenarios":[],"nodes":...}`

```bash
curl -X POST http://localhost:8081/inject/gradual_degradation
```
Expected: `{"status":"activated","scenario":"gradual_degradation"}`

Stop server after verification.

- [ ] **Step 3: Commit**

```bash
git add sim_server.py
git commit -m "feat: simulated OPC-UA server with 72 nodes and anomaly injection"
```

---

## Task 9: FastAPI Backend with WebSocket

**Files:**
- Create: `server.py`

- [ ] **Step 1: Write the backend server**

`server.py`:
```python
"""FastAPI backend: WebSocket streaming + REST API for robot health dashboard.

Usage:
    python server.py [--port 8080] [--opcua-endpoint opc.tcp://localhost:4840/robolink/server]
"""

import argparse
import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from robolink.sources.opcua_source import OPCUASource
from robolink.sources.base import SensorReading
from robolink.monitor import RobotHealthMonitor
from robolink.alarms import AlarmEngine
from robolink.prediction import PredictionEngine
from robolink.formatter import ObservationFormatter
from robolink.utils.logging import setup_logging, get_logger

log = get_logger("server")

# --- Globals ---

monitor: RobotHealthMonitor | None = None
source: OPCUASource | None = None
ws_clients: set[WebSocket] = set()
event_buffer: list[dict] = []  # Batched events for throttling
_batch_lock = asyncio.Lock()
BATCH_INTERVAL_S = 0.5


# --- WebSocket Broadcasting ---

async def broadcast(event: dict) -> None:
    """Buffer an event for batched broadcast."""
    async with _batch_lock:
        event_buffer.append(event)


async def flush_loop() -> None:
    """Periodically flush buffered events to all WebSocket clients."""
    while True:
        await asyncio.sleep(BATCH_INTERVAL_S)
        async with _batch_lock:
            if not event_buffer:
                continue
            events = event_buffer.copy()
            event_buffer.clear()

        dead = set()
        for ws in ws_clients:
            try:
                for event in events:
                    await ws.send_json(event)
            except Exception:
                dead.add(ws)
        ws_clients -= dead


async def send_snapshot(ws: WebSocket) -> None:
    """Send full state snapshot to a newly connected client."""
    if monitor is None:
        return

    snapshot = {
        "type": "state_snapshot",
        "robots": [r.to_dict() for r in monitor.get_all_states()],
        "alarms": [a.to_dict() for a in monitor.alarm_engine.get_active()],
        "predictions": [p.to_dict() for p in monitor.prediction_engine.get_predictions()],
    }
    await ws.send_json(snapshot)


# --- OPC-UA Data Handling ---

async def on_sensor_reading(reading: SensorReading) -> None:
    """Process a sensor reading through the monitor pipeline."""
    if monitor is None:
        return

    event = monitor.update(
        robot_id=reading.robot_id,
        joint=reading.joint,
        metric=reading.metric,
        value=reading.value,
        timestamp_s=reading.timestamp_ms / 1000.0,
    )

    # Broadcast sensor update
    normalized = monitor.formatter.normalize(reading.metric, reading.value)
    await broadcast({
        "type": "sensor_update",
        "robot_id": reading.robot_id,
        "joint": reading.joint,
        "metric": reading.metric,
        "value": round(reading.value, 3),
        "normalized": round(normalized, 4),
    })

    # Broadcast health update
    await broadcast({
        "type": "health_update",
        "robot_id": reading.robot_id,
        "score": round(event.health_score, 1),
    })

    # Broadcast alarm if fired
    if event.alarm:
        await broadcast({
            "type": "alarm",
            **event.alarm.to_dict(),
        })

    # Broadcast prediction if generated
    if event.prediction:
        await broadcast({
            "type": "prediction",
            **event.prediction.to_dict(),
        })

    # Broadcast any resolved alarms
    for resolved_id in monitor.alarm_engine.pop_resolved():
        await broadcast({
            "type": "alarm_resolved",
            "id": resolved_id,
        })


async def on_system_event(node: str, value: str) -> None:
    """Handle system-level OPC-UA events (gateway, line state)."""
    if monitor is None:
        return

    alarm = monitor.alarm_engine.evaluate_system(node.lower().replace(".", "_"), value)
    await broadcast({
        "type": "system",
        "node": node,
        "value": value,
    })
    if alarm:
        await broadcast({
            "type": "alarm",
            **alarm.to_dict(),
        })


# --- App Lifecycle ---

async def start_opcua(endpoint: str) -> None:
    """Connect to OPC-UA server and start streaming."""
    global source
    source = OPCUASource(endpoint=endpoint)

    max_retries = 10
    for attempt in range(max_retries):
        try:
            await source.connect()
            log.info("opcua_connected", endpoint=endpoint)
            break
        except Exception as e:
            wait = min(2 ** attempt, 30)
            log.warning("opcua_connect_failed", attempt=attempt + 1, error=str(e), retry_in=wait)
            await asyncio.sleep(wait)
    else:
        log.error("opcua_connect_exhausted", endpoint=endpoint)
        return

    await source.stream(on_sensor_reading, on_system_event)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global monitor
    setup_logging("INFO")

    monitor = RobotHealthMonitor(
        alarm_engine=AlarmEngine(),
        prediction_engine=PredictionEngine(),
        formatter=ObservationFormatter(),
    )

    # Start flush loop
    asyncio.create_task(flush_loop())

    # Start OPC-UA connection in background
    opcua_endpoint = app.state.opcua_endpoint
    asyncio.create_task(start_opcua(opcua_endpoint))

    log.info("server_started")
    yield
    log.info("server_stopping")

    if source:
        await source.disconnect()


app = FastAPI(title="RoboLink Dashboard API", lifespan=lifespan)


# --- Routes ---

@app.get("/")
async def serve_dashboard():
    """Serve the dashboard HTML."""
    dashboard_path = Path(__file__).parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path, media_type="text/html")
    return HTMLResponse("<h1>Dashboard not built yet</h1>")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    log.info("ws_connected", clients=len(ws_clients))

    # Send state snapshot
    await send_snapshot(ws)

    try:
        while True:
            # Keep connection alive, ignore client messages
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(ws)
        log.info("ws_disconnected", clients=len(ws_clients))


@app.get("/api/robots")
async def get_robots():
    if monitor is None:
        return []
    return [r.to_dict() for r in monitor.get_all_states()]


@app.get("/api/alarms")
async def get_alarms():
    if monitor is None:
        return {"active": [], "history": []}
    return {
        "active": [a.to_dict() for a in monitor.alarm_engine.get_active()],
        "history": [a.to_dict() for a in monitor.alarm_engine.get_history()],
    }


@app.get("/api/predictions")
async def get_predictions():
    if monitor is None:
        return []
    return [p.to_dict() for p in monitor.prediction_engine.get_predictions()]


# --- Main ---

def main():
    parser = argparse.ArgumentParser(description="RoboLink Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port")
    parser.add_argument(
        "--opcua-endpoint",
        default="opc.tcp://localhost:4840/robolink/server",
        help="OPC-UA server endpoint",
    )
    args = parser.parse_args()

    app.state.opcua_endpoint = args.opcua_endpoint
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify server starts (without OPC-UA connection)**

Run: `python server.py --port 8080 &`
Run: `curl http://localhost:8080/api/robots`
Expected: `[]`
Stop: kill the background process

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat: FastAPI backend with WebSocket streaming and REST API"
```

---

## Task 10: Dashboard

**Files:**
- Create: `dashboard/index.html`

- [ ] **Step 1: Download Chart.js locally**

```bash
mkdir -p dashboard
curl -o dashboard/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js
```

- [ ] **Step 2: Write the dashboard HTML**

`dashboard/index.html` -- this is a large self-contained file. Write the complete file with:

**HTML structure:**
- Top bar with "RoboLink" title and line status indicator
- 3 robot cards in a row, each with: health score bar (colored), status badge, alarm count, key joint metrics for hottest/most vibrating joint
- Sensor trend chart (Chart.js) showing selected robot's joint temperatures over time
- Alarm panel (left) with severity-colored entries, newest first
- Prediction panel (right) with days-to-failure and confidence
- Audit log at bottom with timestamped entries

**CSS:**
- Dark theme (`#1a1a2e` background, `#16213e` cards)
- Green/amber/red color system based on health score
- Alarm severity colors: critical=`#e74c3c`, warning=`#f39c12`, info=`#3498db`
- CSS Grid layout for responsive panels
- Pulsing animation on active critical alarms

**JavaScript:**
- WebSocket connection to `ws://localhost:8080/ws` with auto-reconnect (1s interval)
- "Reconnecting..." banner on disconnect
- State management: robot states, alarm list, prediction list, chart data
- `state_snapshot` handler: populate all panels from initial state
- `sensor_update` handler: update robot card metrics, push to chart data
- `health_update` handler: update health score bar + color
- `alarm` handler: prepend to alarm panel with flash
- `alarm_resolved` handler: mark as resolved in panel
- `prediction` handler: update prediction panel
- `system` handler: update line status
- Chart.js line chart: 6 lines (one per joint temperature), red threshold line at 90C, rolling 60-point window
- Click robot card to select it and update chart

The full HTML file should be approximately 400-600 lines including inline CSS and JS. Write the complete file -- do not use placeholders.

- [ ] **Step 3: Verify dashboard loads**

Run sim server: `python sim_server.py --port 4840 --rest-port 8081 &`
Run backend: `python server.py --port 8080 &`
Open browser: `http://localhost:8080`
Expected: Dashboard loads, robot cards appear, metrics start streaming within a few seconds

- [ ] **Step 4: Commit**

```bash
git add dashboard/
git commit -m "feat: real-time dashboard with health scores, alarms, and predictions"
```

---

## Task 11: End-to-End Integration Test

**Files:** No new files. This verifies the full stack works together.

- [ ] **Step 1: Start the full stack**

Terminal 1: `python sim_server.py --port 4840 --rest-port 8081`
Terminal 2: `python server.py --port 8080`
Browser: Open `http://localhost:8080`

- [ ] **Step 2: Verify normal operation**

Verify in browser:
- 3 robot cards visible with health scores near 90-100
- All cards green
- Sensor chart updating with oscillating values
- No alarms in alarm panel
- No predictions

- [ ] **Step 3: Trigger gradual degradation**

Run: `curl -X POST http://localhost:8081/inject/gradual_degradation`

Verify in browser (wait 30-60 seconds):
- Robot #2 card turns amber
- Health score drops (92 -> ~67)
- Warning alarm appears in alarm panel
- Prediction appears: "Joint 3 temperature: ~18 days to failure"

- [ ] **Step 4: Trigger sudden vibration**

Run: `curl -X POST http://localhost:8081/inject/sudden_vibration`

Verify in browser:
- Robot #3 card turns red
- Health score drops to ~41
- Critical alarm appears in alarm panel

- [ ] **Step 5: Trigger gateway offline**

Run: `curl -X POST http://localhost:8081/inject/gateway_offline`

Verify in browser:
- Critical alarm: "Gateway offline"
- Line status indicator changes

- [ ] **Step 6: Clear and verify recovery**

Run: `curl -X POST http://localhost:8081/clear`

Verify: alarms auto-resolve, health scores recover

- [ ] **Step 7: Practice the 90-second demo**

Run through the demo script from the spec 3 times. Time it.

- [ ] **Step 8: Commit any final fixes**

```bash
git add -A
git commit -m "feat: end-to-end integration verified, demo ready"
```

---

## Summary

| Task | Component | Est. Time |
|------|-----------|-----------|
| 1 | Scaffolding + deps | 10 min |
| 2 | DataSource base | 5 min |
| 3 | ObservationFormatter | 10 min |
| 4 | AlarmEngine | 20 min |
| 5 | PredictionEngine | 20 min |
| 6 | RobotHealthMonitor | 20 min |
| 7 | OPCUASource | 15 min |
| 8 | Sim server | 25 min |
| 9 | FastAPI backend | 25 min |
| 10 | Dashboard | 120 min |
| 11 | Integration test | 30 min |
| **Total** | | **~300 min (5 hr)** |

3 hours of buffer for debugging, polish, and demo practice.
