# RoboLink

## What This Is

Real-time robot health monitoring and predictive failure detection platform. Connects to industrial robot arms (UR, KUKA, ABB, FANUC) via OPC-UA, normalizes vendor-specific data into a common schema, and provides unified health dashboards, smart alarms, and failure predictions.

One dashboard for your entire mixed-vendor robot fleet.

**Founder:** Pratik Patil -- IoT Data & Connectivity Engineer at Danfoss. MS Mechatronics, Germany.
**Stage:** Pre-product. Building MVP for AI Beavers Founder Hackathon, Hamburg, June 6, 2026.

## The Problem

73% of factories run robots from 2+ vendors. Each vendor ships their own monitoring tool (UR Insight, KUKA Connect, ABB Ability, FANUC ZDT). Maintenance managers juggle 3-4 dashboards, 3-4 alarm systems, and an Excel sheet to cross-reference. Unplanned downtime costs $10-50K/hour. Nobody has built the vendor-neutral robot monitoring layer.

## Architecture

```
Robot Arms (UR/KUKA/ABB/FANUC)
    |  OPC-UA subscriptions (50ms)
    |
RoboLink Core
    |-- OPCUASource (asyncua, subscribes to robot diagnostic nodes)
    |-- Device Profiles (vendor-specific YAML configs for normalization)
    |-- ObservationFormatter (normalize to [-1,1] common schema)
    |-- RobotHealthMonitor (aggregate per-robot health scores)
    |-- AlarmEngine (thresholds, dedup, auto-resolve)
    |-- PredictionEngine (linear regression trend analysis)
    |
FastAPI Backend
    |-- WebSocket (batched events at 500ms to dashboard)
    |-- REST API (/api/robots, /api/alarms, /api/predictions)
    |
Dashboard (vanilla JS + Chart.js)
    |-- Robot cards with health scores (0-100)
    |-- Sensor trend charts with threshold lines
    |-- Alarm panel (critical/warning/info, deduped)
    |-- Prediction panel (days-to-failure, confidence %)
    |-- Audit log
```

## Project Structure

```
robolink/
  __init__.py
  sources/
    __init__.py
    base.py              # Abstract DataSource + SensorReading dataclass
    opcua_source.py      # OPCUASource with asyncua subscriptions
  formatter.py           # ObservationFormatter (normalize to [-1,1])
  monitor.py             # RobotHealthMonitor (health scores, coordination)
  alarms.py              # AlarmEngine (thresholds, dedup, auto-resolve)
  prediction.py          # PredictionEngine (linear regression trends)
  utils/
    __init__.py
    logging.py           # Structured logging via structlog

sim_server.py            # Simulated OPC-UA server (3 robots, 72 nodes)
server.py                # FastAPI backend (WebSocket + REST)
dashboard/
  index.html             # Self-contained dashboard (JS + Chart.js bundled)
  chart.min.js           # Chart.js bundled locally
```

## Code Standards

- Python 3.11+ (match statements, X | Y unions, asyncio.TaskGroup)
- Async everywhere. No synchronous blocking. No `time.sleep` -- use `asyncio.sleep`
- Type hints on every function signature
- Docstrings on every class and public method
- Structured logging via structlog (DEBUG=readings, INFO=connections, WARNING=thresholds, ERROR=failures)
- Reconnection with exponential backoff on all network connections (1s, 2s, 4s, 8s, max 30s)
- Every class needs `__repr__`
- No hardcoded values -- config via dataclass or Pydantic model

## Key Libraries

- `asyncua` -- OPC-UA client/server (robot data subscriptions + simulation)
- `fastapi` + `uvicorn` -- REST API + WebSocket server
- `structlog` -- structured logging
- `numpy` -- normalization + linear regression
- Chart.js -- dashboard charts (bundled locally, no CDN)

## Key Concepts

- **Device profiles:** YAML configs that map vendor-specific OPC-UA nodes to a common schema. UR uses `actual_q_0`, KUKA uses `Axis1.ActualPosition` -- profiles translate both to `joints[0].position`
- **Common robot schema:** Vendor-neutral data model. Every robot maps to: joints (position, velocity, torque, temperature, current, error_code), status, safety state
- **Health scoring:** `score = min(per_joint_scores) * 0.4 + avg(per_joint_scores) * 0.6`. Single bad joint drags overall score via the min term
- **OPC-UA subscriptions:** Push model, not polling. Server pushes on value change
- **Prediction via trend analysis:** Linear regression on rolling 60-point window. Time compression factor for demo (1 sim-second = 12960 real-seconds)
- **Alarm deduplication:** Same alarm suppressed for 30 seconds. Auto-resolve when value drops below threshold
- **Update throttling:** Server batches OPC-UA updates at 500ms intervals before broadcasting to dashboard

## Build Plan

Full step-by-step plan with code: `docs/superpowers/plans/2026-06-04-robot-health-monitor.md`

## Key Docs

| Doc | Purpose |
|-----|---------|
| `docs/superpowers/specs/2026-06-04-robot-health-monitor-design.md` | Technical spec |
| `docs/superpowers/plans/2026-06-04-robot-health-monitor.md` | Implementation plan with code |
| `docs/robolink-blueprint.md` | Market, competition, business model |
| `docs/hackathon-gameplan.md` | Hackathon day schedule + pitch |

## Future Roadmap (Post-Hackathon)

- MQTT source connector
- Modbus source connector
- Device profiles for KUKA, ABB, FANUC (MVP: UR only)
- Fleet management (multi-site, multi-line)
- Compliance reporting (ISO 10218/15066)
- ML-based prediction models (replace linear regression)
- Bridge to robot foundation models (pi0, LeRobot, NVIDIA Cosmos)
- Normalized robot data as training pipeline for Physical AI

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming --> invoke /office-hours
- Strategy/scope --> invoke /plan-ceo-review
- Architecture --> invoke /plan-eng-review
- Design system/plan review --> invoke /design-consultation or /plan-design-review
- Full review pipeline --> invoke /autoplan
- Bugs/errors --> invoke /investigate
- QA/testing site behavior --> invoke /qa or /qa-only
- Code review/diff check --> invoke /review
- Visual polish --> invoke /design-review
- Ship/deploy/PR --> invoke /ship or /land-and-deploy
- Save progress --> invoke /context-save
- Resume context --> invoke /context-restore
