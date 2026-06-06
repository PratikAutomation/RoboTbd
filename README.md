# RoboTbd

**One dashboard for your entire mixed-vendor robot fleet.**

AI-powered health monitoring, smart alarms, and failure predictions for industrial robots — any vendor, one screen.

![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green)
![OPC-UA](https://img.shields.io/badge/OPC--UA-asyncua-orange)
![AI](https://img.shields.io/badge/AI-Qwen-purple)

## The Problem

73% of factories run robots from 2+ vendors. Each vendor ships their own monitoring tool. Maintenance managers juggle 3-4 dashboards, 3-4 alarm systems, and can't compare robots across brands. Unplanned downtime costs $10-50K/hour.

## What We Built

```
Factory Floor                   RoboTbd                        Dashboard
─────────────                   ───────                        ─────────

 ┌──────┐
 │ UR10 │──┐
 └──────┘  │
 ┌──────┐  │   OPC-UA      ┌──────────────┐   WebSocket    ┌──────────┐
 │ KUKA │──┼────────────>   │  Normalize   │ ──────────────>│ Health:95│
 └──────┘  │                │  Score       │                │ Alarms:2 │
 ┌──────┐  │                │  Diagnose    │                │ AI: Bear-│
 │ ABB  │──┘                │  Predict     │                │ ing wear │
 └──────┘                   └──────────────┘                └──────────┘
```

### Features

- **Multi-vendor normalization** — UR, KUKA, ABB data normalized to one common schema via device profiles
- **Health scoring** — Per-joint and per-robot scores (0-100). Formula: `min(joints) × 0.4 + avg(joints) × 0.6`
- **Smart alarms** — Threshold detection with 30s deduplication and auto-resolve
- **Failure prediction** — Linear regression on rolling 60-point windows with time-to-failure estimates
- **AI diagnostics (Qwen)** — When alarms fire, Qwen analyzes all sensor context against vendor-specific specs and known failure patterns. Returns root cause, evidence, action, and part numbers
- **Real robot data** — Uses actual UR5 and SO-ARM100 recordings from HuggingFace, not synthetic data

### AI Diagnostics

Not just "temperature is high." Our AI reasons about WHY:

```
ALARM: Robot2 Joint 3 temperature 72°C

AI DIAGNOSIS:
  Bearing degradation — 4/4 sensors confirm

  Evidence:
  ✓ Temperature rising (exceeds KUKA >70°C spec)
  ✓ Vibration elevated (high-frequency bearing signature)
  ✓ Current rising (motor compensating for friction)
  ✓ Torque stable (rules out external load change)

  Action: Replace bearing within 14 days
  Parts: Nabtesco RV reducer (€2,000-8,000)
```

Diagnoses are grounded in real vendor documentation — UR Service Manual specs, KUKA RV reducer maintenance intervals, ABB integrated motor-gearbox thresholds. Not hallucinated.

## Architecture

```
robolink/
  sources/
    base.py              # Abstract DataSource + SensorReading
    opcua_source.py      # OPC-UA client (asyncua, subscriptions)
  formatter.py           # Normalize vendor data to [-1,1]
  monitor.py             # Health scoring engine
  alarms.py              # Threshold detection, dedup, auto-resolve
  prediction.py          # Linear regression failure prediction
  diagnosis.py           # Qwen-powered AI diagnostics

sim_server.py            # OPC-UA sim (3 robots, 108 nodes, real data replay)
server.py                # FastAPI + WebSocket backend
start.py                 # Combined launcher for deployment
dashboard/               # Frontend (Chart.js + vanilla JS)
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set Qwen API key (for AI diagnostics)
export DASHSCOPE_API_KEY="your-key-here"

# Option 1: Run both servers at once
python start.py

# Option 2: Run separately
python sim_server.py          # Terminal 1: OPC-UA simulation
uvicorn server:app --port 8000  # Terminal 2: API server

# Open dashboard
open http://localhost:8000/dashboard
```

## API

```
WebSocket:  ws://localhost:8000/ws           (500ms updates)
GET         /api/robots                       (all robot states)
GET         /api/alarms                       (active alarms)
GET         /api/predictions                  (failure predictions)
GET         /api/diagnosis                    (latest AI diagnosis)
GET         /api/health                       (server health check)
```

## Real Robot Data

All training/demo data comes from public HuggingFace datasets:

| Dataset | Source | Frames | What |
|---------|--------|--------|------|
| [UR5 Robotiq](https://huggingface.co/datasets/SleepyShaman123/reach_ur5_robotiq) | LeRobot | 274 | Joint positions, torques, velocities |
| [Robothon Expert](https://huggingface.co/datasets/kantine/industrial_robothon_buttons_expert) | LeRobot | 896 | Normal robot operation |
| [Robothon Anomaly](https://huggingface.co/datasets/kantine/industrial_robothon_buttons_anomaly) | LeRobot | 896 | Anomalous robot behavior |

## Tech Stack

Python 3.12 · asyncua · FastAPI · uvicorn · structlog · numpy · OpenAI SDK (Qwen) · Chart.js

## Team

Built at [AI Beavers Founder Hackathon](https://www.aibeavers.com), Hamburg, June 6 2026.

## License

MIT
