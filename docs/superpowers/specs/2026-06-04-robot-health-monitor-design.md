# Design: RoboLink Robot Health Monitor -- Hackathon MVP

Generated: 2026-06-04
Status: APPROVED
Branch: master

## Problem

Industrial robot arm downtime costs $10-50K/hour. Current process when robot fails: call manufacturer, wait 2 days, pay $500/hr technician. Scheduled maintenance wastes money on healthy robots. Reactive repair wastes more on emergency calls.

Every robot arm already streams diagnostic data via OPC-UA (joint torques, temperatures, vibration, error codes). Nobody uses this data for predictive maintenance at the small/mid manufacturer level. Enterprise solutions (Siemens MindSphere, ABB Ability) cost $100K+ and take months to deploy.

## Product

Real-time robot health monitoring and AI-powered failure prediction from existing OPC-UA diagnostic data. No new sensors, no new hardware.

**One sentence:** "Predict robot failures before they happen using the factory data you already collect."

## Target User

Maintenance/plant manager at manufacturer running robot arms (UR, KUKA, ABB, Fanuc). Company size: 50-500 employees. Running 5-50 robot arms. Currently using scheduled maintenance + reactive repair.

## Architecture

```
Browser (Dashboard)
    |  WebSocket (JSON events)
    |
FastAPI Backend
    |-- WebSocket Manager
    |-- Alarm Engine (thresholds, dedup, auto-resolve)
    |-- Health Scorer (weighted joint metrics -> 0-100)
    |-- Prediction Engine (linear regression on rolling window)
    |
RoboLink Core
    |-- OPCUASource (asyncua subscriptions, 50ms)
    |-- ObservationFormatter (normalize to [-1,1])
    |-- RobotHealthMonitor (aggregate per-robot state)
    |
Simulated OPC-UA Server (asyncua)
    |-- 3 robots x 6 joints x 4 metrics = 72 sensor nodes
    |-- 3 system nodes (gateway, line state, uptime)
    |-- REST endpoint for anomaly injection
```

## Data Flow

```
OPC-UA node change (50ms)
  -> OPCUASource callback
    -> ObservationFormatter (normalize to [-1,1])
      -> RobotHealthMonitor (aggregate, compute health score)
        -> Alarm Engine (evaluate thresholds, fire/resolve)
        -> Prediction Engine (update trend, extrapolate if degrading)
          -> WebSocket broadcast to dashboard clients
```

## Components

### 1. Simulated OPC-UA Server (`sim_server.py`)

Node structure per robot:
```
ns=2;s=Factory.Robot{N}.Joint{M}.Torque        (float, Nm, range 0-200)
ns=2;s=Factory.Robot{N}.Joint{M}.Temperature   (float, C, range 20-120)
ns=2;s=Factory.Robot{N}.Joint{M}.Vibration     (float, mm/s, range 0-10)
ns=2;s=Factory.Robot{N}.Joint{M}.ErrorCode     (int, 0=ok)
```
3 robots x 6 joints x 4 metrics = 72 nodes.

System nodes:
```
ns=2;s=Factory.Robot{N}.Status       (string: running/idle/error)
ns=2;s=Factory.Gateway.Status        (string: online/offline)
ns=2;s=Factory.Line.State            (string: production/maintenance/stopped)
```

Normal behavior: values oscillate within healthy ranges + Gaussian noise.

Error codes: 0 = OK, 1 = minor calibration drift, 2 = communication hiccup, 101 = motor overcurrent, 102 = encoder fault.

Anomaly injection via `POST /inject/{scenario}`:
- `gradual_degradation`: Robot #2 Joint 3 temperature climbs 0.1C/sec over 2 min
- `sudden_vibration`: Robot #3 Joint 5 vibration spikes 3x baseline
- `gateway_offline`: Gateway status flips to "offline"

### 2. RoboLink Core (`robolink/`)

**`sources/base.py`** -- Abstract `DataSource` with async `connect()`, `stream()`, `disconnect()`.

**`sources/opcua_source.py`** -- `OPCUASource` subscribes to OPC-UA nodes via asyncua. Pushes data change callbacks. Exponential backoff reconnection (1s, 2s, 4s, 8s, max 30s).

**`formatter.py`** -- `ObservationFormatter` normalizes raw values to [-1, 1]:
- Torque: center=100, scale=100
- Temperature: center=70, scale=50
- Vibration: center=5, scale=5

**`monitor.py`** -- `RobotHealthMonitor`:
```python
class RobotHealthMonitor:
    def update(self, robot_id: str, joint: int, metric: str, value: float) -> HealthEvent
    def get_health_score(self, robot_id: str) -> float  # 0-100
    def get_predictions(self, robot_id: str) -> list[FailurePrediction]
```

Health score: hybrid of worst-joint and average-joint to make single-joint degradation visible.
Formula: `score = min(per_joint_scores) * 0.4 + avg(per_joint_scores) * 0.6`
Per-joint score: weighted combination -- temperature (0.3), vibration (0.3), torque (0.25), error codes (0.15). Each metric mapped 0-100 based on distance from critical threshold.
Below 70 = warning. Below 40 = critical.
Single bad joint drags overall score down hard (via the min term).

### 3. Alarm Engine (`robolink/alarms.py`)

```python
@dataclass
class Alarm:
    id: str
    robot_id: str
    severity: Literal["critical", "warning", "info"]
    message: str
    metric: str
    value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False
```

Threshold rules:

| Metric | Warning | Critical |
|--------|---------|----------|
| Joint temperature | > 75C | > 90C |
| Joint vibration | > 4.0 mm/s | > 7.0 mm/s |
| Joint torque | > 150 Nm | > 180 Nm |
| Error code | any non-zero | code > 100 |
| Gateway status | -- | "offline" |

Deduplication: same alarm (robot + metric + severity) suppressed for 30 seconds.
Auto-resolve: value drops below threshold -> alarm resolved with timestamp.

### 4. Prediction Engine (`robolink/prediction.py`)

```python
@dataclass
class FailurePrediction:
    robot_id: str
    joint: int
    metric: str
    current_value: float
    trend_slope: float
    predicted_failure_value: float
    days_to_failure: float
    confidence: float  # 0-1
```

Method: rolling window of 60 data points. Linear regression. If slope positive and exceeds threshold, extrapolate to critical threshold. Report days-to-failure.

Confidence: R-squared of linear fit. Only report predictions with confidence > 0.6.

Demo compression: simulation compresses 18 days into 2 minutes. Prediction engine uses a configurable `time_compression_factor` (default: 12960, meaning 1 sim-second = 12960 real-seconds). Math: `days_to_failure = (critical_threshold - current_value) / (slope_per_second * time_compression_factor * 86400)`. In production, factor = 1.

### 5. FastAPI Backend (`server.py`)

Endpoints:
```
GET  /                     -> serves dashboard HTML
WS   /ws                   -> streams events to dashboard
POST /inject/{scenario}    -> triggers anomaly scenario
GET  /api/robots           -> current state of all robots
GET  /api/alarms           -> active + recent alarms
GET  /api/predictions      -> current predictions
```

On WebSocket connect, server sends full state snapshot (all robot health scores + active alarms + active predictions) before streaming deltas. Client auto-reconnects on close with 1s interval (no backoff needed for hackathon). Dashboard shows "Reconnecting..." banner during disconnect.

Update throttling: server batches sensor updates at 500ms intervals (not raw 50ms). Collects latest value per node, broadcasts one batch. Reduces 1440 updates/sec to ~2 batched events/sec. Dashboard still feels real-time.

WebSocket event types:
- `state_snapshot`: full current state (sent once on connect)
- `sensor_update`: robot_id, joint, metric, value, normalized
- `health_update`: robot_id, score
- `alarm`: id, severity, robot_id, message, value
- `alarm_resolved`: id
- `prediction`: robot_id, joint, metric, days_to_failure, confidence
- `system`: gateway status, line state

### 6. Dashboard (`dashboard/index.html`)

Single self-contained HTML file. Vanilla JS + Chart.js (bundled locally).

Layout:
- Top bar: "RoboLink" + line status
- 3 robot cards: health score bar (0-100), status, active alarm count, key joint metrics
- Sensor trend chart: Chart.js line chart for selected robot, threshold lines in red
- Alarm panel: severity-colored entries, newest first
- Prediction panel: days-to-failure, confidence %, trend direction
- Audit log: timestamped entries for every event

Color system: green (health > 70), amber (40-70), red (< 40).

Click robot card -> sensor chart updates to show that robot's joints.

Dashboard sub-component priority (build top-down, cut bottom-up):
1. P0: Robot cards with health scores
2. P0: Live sensor trend charts
3. P0: Alarm panel with severity colors
4. P1: Prediction panel
5. P1: Audit log
6. P2: Anomaly flash animations (CUT FIRST)
7. P2: Branding polish (CUT SECOND)

## File Structure

```
robolink/
    __init__.py
    sources/
        __init__.py
        base.py
        opcua_source.py
    formatter.py
    monitor.py
    alarms.py
    prediction.py
    utils/
        logging.py

sim_server.py
server.py
dashboard/
    index.html
```

9 Python files + 1 HTML file. No framework, no build step, no npm.

## Build Schedule (8 hours)

```
Hour 1-2:  sim_server.py
           72 sensor nodes + 3 system nodes
           3 anomaly scenarios + REST trigger

Hour 2-3:  robolink/ core
           OPCUASource, ObservationFormatter, RobotHealthMonitor

Hour 3-4:  Alarm + Prediction engines
           AlarmEngine, PredictionEngine

Hour 4-5:  FastAPI backend
           WebSocket streaming, REST endpoints

Hour 5-8:  Dashboard (3 hours)
           P0: Robot cards + health scores (30 min)
           P0: Chart.js sensor trends (45 min)
           P0: Alarm panel (30 min)
           P1: Prediction panel (20 min)
           P1: Audit log (15 min)
           P2: Animations, branding (cut if behind)
```

## Risk Mitigations

- Dashboard takes too long: cut P2 items, ship P0+P1
- OPC-UA server flaky: pre-record sensor data, replay from JSON
- Prediction math wrong: hardcode "18 days" for demo
- WebSocket drops: auto-reconnect in JS client (3 lines)

## What to Skip

- Real ML model (linear regression only)
- Database (in-memory)
- Authentication / multi-tenant
- MQTT and Modbus sources
- Mobile responsive
- Email/SMS notifications
- Historical data persistence
- Tests (deliberate deviation for hackathon -- add immediately after)
- pip packaging
- Docker / deployment

## Demo Script (90 seconds)

```
0:00  Dashboard opens. 3 robots green. Metrics streaming.
0:15  "Live OPC-UA diagnostic data. Health score per robot."
0:25  Robot #2 Joint 3 temp climbing (gradual degradation).
0:35  Warning alarm. Card amber. Health 92->67.
0:40  Prediction: "Joint 3: 18 days to failure. 83% confidence."
0:50  Robot #3 vibration spike. Critical alarm. Card red. Health: 41.
0:55  "Slow degradation and sudden spike. Both caught."
1:05  Point to audit log. "Full trace for maintenance planning."
1:15  Pitch. Done.
```

## Pitch

> "I build industrial monitoring dashboards at Danfoss. For refrigeration, we catch compressor failures before they waste food. I rebuilt the same system for robots.
>
> 4.6 million robot arms in factories. Downtime: 10 to 50 thousand dollars per hour. Current solution: call manufacturer, wait 2 days, pay 500/hr technician.
>
> RoboLink connects to OPC-UA diagnostic data every robot already streams. Scores health real-time. Fires smart alarms. Predicts failures before they happen. That Joint 3 warning? 18 days advance notice. Schedule maintenance on the weekend instead of losing a production shift.
>
> No new hardware. No new sensors. Data your factory already collects, made useful.
>
> Biggest risk: no paying customer yet. Next step: 3 free pilots with factories running UR arms. I have the Danfoss relationships to make it happen."

## Success Criteria

1. Demo runs without crash
2. 3 robot cards with live health scores
3. Warning alarm fires on gradual degradation
4. Critical alarm fires on sudden spike
5. Prediction shows days-to-failure with confidence %
6. Demo under 90 seconds
7. Pitch references Danfoss experience
8. Pitch names biggest risk honestly

## Dependencies

- `asyncua` (OPC-UA server + client)
- `fastapi` + `uvicorn` (WebSocket server)
- `structlog` (structured logging)
- `numpy` (normalization + linear regression)
- Chart.js (bundled locally, no CDN at venue)
- Python 3.11+
