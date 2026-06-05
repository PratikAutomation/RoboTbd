# ROBOLINK -- ENGINEERING CONTEXT BRIEF
### For: Claude Code | From: Pratik Patil (Founder)
### Read this before writing any code.

---

## 1. WHO WE ARE

**Company:** RoboLink
**Founder:** Pratik Patil -- IoT Data & Connectivity Engineer at Danfoss. MS Mechatronics, Germany. 24 years old. International robo wars champion.
**Stage:** Pre-product. Building MVP for AI Beavers Founder Hackathon, Hamburg, June 6, 2026.
**Goal:** Build a working demo. Raise pre-seed funding. Become the vendor-neutral robot monitoring standard.

---

## 2. THE PROBLEM

### The multi-vendor monitoring gap:

73% of manufacturing facilities use robots from 2+ vendors (Robotics Industries Association, 2024). Every vendor ships their own monitoring tool:

- **Universal Robots:** UR Insight
- **KUKA:** KUKA Connect
- **ABB:** ABB Ability Connected Services
- **FANUC:** ZDT (Zero Downtime) + iRConnect

These tools work fine for THEIR robots. They will NEVER show competitor data. UR will never display KUKA health. That's their business model.

**The maintenance manager's reality:**
- Open UR Insight -- check 3 UR robots
- Open KUKA Connect -- check 2 KUKA robots
- Open ABB Ability -- check 1 ABB robot
- Cross-reference in Excel -- "which robot needs attention first?"
- 3-4 dashboards, 3-4 alarm systems, zero unified view

**The cost:**
- Unplanned robot downtime: $10,000 - $50,000 per hour
- One failure event: $50,000 - $250,000 total
- Average mid-size factory: 3-6 unplanned downtimes per year
- Annual cost: $150K - $1.5M

### Why incumbents don't solve this:

| Incumbent | Why It Fails |
|-----------|-------------|
| UR Insight / KUKA Connect / ABB Ability | Own-brand only. Will never show competitor data. |
| Siemens Insights Hub | $100K+ setup, 6-12 months deployment. Mid-market can't afford it. |
| Ignition (SCADA) | General-purpose. Reads OPC-UA tags but doesn't know what a robot joint IS. 3-6 month custom build per robot type. |
| AWS IoT SiteWise / Azure IoT | Raw infrastructure toolkit. 2-3 months to wire together. No robot intelligence out of the box. |
| Augury | Requires NEW vibration sensors ($200-500 each). Doesn't use existing OPC-UA data. |

**Nobody has built the vendor-neutral, robot-aware monitoring layer. That's RoboLink.**

---

## 3. THE PRODUCT

**One sentence:** One dashboard for your entire mixed-vendor robot fleet with health scores, alarms, and failure predictions from your existing OPC-UA data.

### What the maintenance manager sees:

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  ROBOT #1    │  ROBOT #2    │  ROBOT #3    │  ROBOT #4    │
│  UR10e       │  UR10e       │  KR16        │  IRB2600     │
│  Health: 94  │  Health: 67  │  Health: 88  │  Health: 91  │
│  ● Running   │  ⚠ Warning   │  ● Running   │  ● Running   │
│  Pred: --    │  Pred: 18d   │  Pred: --    │  Pred: --    │
└──────────────┴──────────────┴──────────────┴──────────────┘

WORST FIRST: Robot #2 (UR10e) → Robot #3 (KR16) → Robot #4 (ABB)
```

### Core features:
1. **Multi-vendor monitoring:** UR, KUKA, ABB, FANUC in one dashboard
2. **Health scoring:** 0-100 per robot, comparable across vendors
3. **Smart alarms:** Threshold-based, deduplicated, auto-resolving
4. **Failure prediction:** Trend analysis detects degradation early
5. **Audit log:** Every event timestamped for maintenance planning

### What it does NOT do (yet):
- Control robots (read-only monitoring)
- Replace manufacturer tools (complements them)
- Require new hardware (uses existing OPC-UA data)
- Require cloud (runs on localhost for hackathon)

---

## 4. THE TECHNICAL ARCHITECTURE

### The normalization problem (why this is hard):

Every vendor uses different OPC-UA node structures:

```
UR:    ns=2;s=actual_q_0                  # Joint 0 position (radians)
KUKA:  ns=6;s=Axis1.ActualPosition        # Axis 1 position (degrees)
ABB:   ns=3;s=Motion/Ax_1/ActualPos       # Axis 1 position (vendor units)
FANUC: ns=2;s=J1/CURPOS                   # Joint 1 position (vendor units)
```

Same data, four different dialects. RoboLink solves this with device profiles.

### Device profiles:

YAML configs that map vendor-specific OPC-UA nodes to a common schema:

```yaml
# profiles/universal_robots.yaml
vendor: ur
node_mapping:
  joints:
    position: "actual_q_{i}"
    torque: "actual_moment_{i}"
    temperature: "joint_temperatures_{i}"
  status:
    mode:
      node: "robot_mode"
      mapping:
        7: "running"
        3: "idle"
        9: "error"
  unit_conversions:
    position: null           # already radians
    torque: null             # already Nm
```

### Common robot schema (what everything normalizes TO):

```yaml
robot:
  id: string
  vendor: string          # ur | kuka | abb | fanuc
  model: string
  joints:
    - joint_id: int
      position: float     # always radians
      velocity: float     # rad/s
      torque: float       # Nm (converted from vendor units)
      temperature: float  # celsius
      current: float      # amps
      error_code: int     # 0 = OK
  status:
    mode: string          # running | idle | error | estop
  health_score: float     # 0-100
```

### Data flow:

```
OPC-UA node change (50ms)
  → OPCUASource callback
    → Device Profile (vendor node → common schema)
      → ObservationFormatter (normalize to [-1,1])
        → RobotHealthMonitor (aggregate, compute health score)
          → AlarmEngine (evaluate thresholds, fire/resolve)
          → PredictionEngine (update trend, extrapolate if degrading)
            → WebSocket broadcast (batched at 500ms) to dashboard
```

### Health scoring:

```
Per-joint score: weighted metrics
  temperature (0.3) + vibration (0.3) + torque (0.25) + error_codes (0.15)
  Each mapped 0-100 based on distance from critical threshold

Robot score:
  min(per_joint_scores) * 0.4 + avg(per_joint_scores) * 0.6
  Single bad joint drags overall score via the min term

Color coding:
  > 70: green (running)
  40-70: amber (warning)
  < 40: red (critical)
```

### Alarm engine:

| Metric | Warning | Critical |
|--------|---------|----------|
| Joint temperature | > 75°C | > 90°C |
| Joint vibration | > 4.0 mm/s | > 7.0 mm/s |
| Joint torque | > 150 Nm | > 180 Nm |
| Error code | any non-zero | > 100 |
| Gateway status | -- | "offline" |

Deduplication: same alarm suppressed for 30 seconds.
Auto-resolve: value drops below threshold.

### Prediction engine:

Linear regression on rolling 60-point window. If slope exceeds threshold and R² > 0.6, extrapolate to critical value. Report days-to-failure.

Demo uses time compression factor (12960x) to show 18 days of degradation in 2 minutes.

---

## 5. PROJECT STRUCTURE

```
robolink/
  __init__.py              # Package init, version
  sources/
    __init__.py
    base.py                # Abstract DataSource + SensorReading
    opcua_source.py        # OPCUASource (asyncua subscriptions)
  formatter.py             # ObservationFormatter (normalize to [-1,1])
  monitor.py               # RobotHealthMonitor (health scores)
  alarms.py                # AlarmEngine (thresholds, dedup, auto-resolve)
  prediction.py            # PredictionEngine (linear regression)
  utils/
    __init__.py
    logging.py             # Structured logging via structlog

sim_server.py              # OPC-UA simulation server (3 robots, 72 nodes)
server.py                  # FastAPI backend (WebSocket + REST)
dashboard/
  index.html               # Self-contained dashboard
  chart.min.js             # Chart.js bundled locally
requirements.txt           # Python dependencies
```

---

## 6. CODE STANDARDS

- **Python 3.11+** -- match statements, X | Y unions, asyncio.TaskGroup
- **Async everywhere** -- no synchronous blocking, no `time.sleep`, use `asyncio.sleep`
- **Type hints** on every function signature
- **Docstrings** on every class and public method
- **structlog** for logging -- DEBUG=readings, INFO=connections, WARNING=thresholds, ERROR=failures
- **Exponential backoff** reconnection on all network connections (1s, 2s, 4s, 8s, max 30s)
- **Every class needs `__repr__`**
- **No hardcoded values** -- config via dataclass
- **No tests during hackathon** (deliberate deviation -- add immediately after)

---

## 7. DEPENDENCIES

```
asyncua>=1.1.0
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
structlog>=23.2.0
numpy>=1.26.0
```

No GPU. No torch. No Modal. No cloud services. Everything runs on localhost.

---

## 8. HACKATHON DEMO

**The 90-second demo:**

1. Dashboard opens -- 3 robots, all green, metrics streaming
2. Robot #2 Joint 3 temperature starts climbing (gradual degradation)
3. Warning alarm fires, card turns amber, health drops to 67
4. Prediction: "18 days to failure, 83% confidence"
5. Robot #3 vibration spikes, card turns red, critical alarms
6. Audit log shows full timestamped trace
7. Pitch: "I build industrial monitoring at Danfoss. Nobody built this for robots."

**Anomaly injection:**
```bash
curl -X POST http://localhost:8081/inject/gradual_degradation
curl -X POST http://localhost:8081/inject/sudden_vibration
curl -X POST http://localhost:8081/inject/gateway_offline
curl -X POST http://localhost:8081/clear
```

---

## 9. THE BUSINESS CONTEXT

**Market:** Predictive maintenance is $15.9B, growing 25% CAGR. Robot-specific predictive maintenance is a $2-4B subset.

**Target customer:** Maintenance manager at mid-size manufacturer (50-500 employees) running 5-50 robot arms from 2+ vendors. Germany first, then DACH, then Europe.

**Pricing:** $50/robot/month. 12 robots avg = $7,200/year per factory. One prevented failure ($50-250K) pays for 7-35 years.

**Competition:** UR Insight (UR only), KUKA Connect (KUKA only), Siemens ($100K+), Ignition (no robot intelligence), AWS/Azure (raw toolkit). RoboLink is the only vendor-agnostic + robot-aware solution.

**Founder advantage:** Pratik builds industrial monitoring platforms at Danfoss professionally. Same architecture, different vertical. Knows OPC-UA failure modes from production.

**First paid value:** Reduced unplanned downtime via multi-vendor unified monitoring. Not "better monitoring" (manufacturer tools do that per-brand). The value is: "one screen, all robots, which one needs attention FIRST."

---

## 10. VISION (WHERE THIS GOES)

```
TODAY:        Multi-vendor robot monitoring + alarms + predictions
YEAR 1:       Fleet management, compliance reporting, multi-site
YEAR 2+:      Normalized robot data as training pipeline for
              foundation models (pi0, LeRobot, NVIDIA Cosmos).
              The monitoring platform becomes the data layer
              for Physical AI.
```

The monitoring product gets customers and revenue today. The data layer for Physical AI is the long-term moat.

---

## 11. KEY DOCS

| Doc | Path | Purpose |
|-----|------|---------|
| Spec | `docs/superpowers/specs/2026-06-04-robot-health-monitor-design.md` | Technical component spec |
| Plan | `docs/superpowers/plans/2026-06-04-robot-health-monitor.md` | Step-by-step build plan with code |
| Blueprint | `docs/robolink-blueprint.md` | Market, competition, business model |
| Game Plan | `docs/hackathon-gameplan.md` | Hackathon day schedule + pitch |

---

**Build the monitoring product. Ship it. The AI vision follows.**
