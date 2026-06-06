# Frontend Design Brief for Javi

## What the Backend Does (Simple)

```
sim_server.py creates 3 fake robots sending real sensor data via OPC-UA
    ↓
server.py connects, processes everything, sends to you via WebSocket
    ↓
YOUR dashboard receives JSON every 500ms and renders it
```

### The 3 Robots

| ID | Vendor | Model | Behavior | What Judges See |
|----|--------|-------|----------|-----------------|
| Robot1 | Universal Robots | UR10e | Healthy | Green, stable, boring (good) |
| Robot2 | KUKA | KR-16 | Joint 3 degrades over time | Yellow→Red, alarms fire, AI diagnoses |
| Robot3 | ABB | IRB-6700 | Random anomaly spikes | Occasional orange flickers |

Robot2 is THE STAR. Its Joint 3 slowly breaks. That's our demo story.

---

## What You Receive (WebSocket)

### Regular update (every 500ms)
```json
{
  "type": "update",
  "robots": {
    "Robot1": {
      "robot_id": "Robot1",
      "vendor": "ur",
      "model": "UR10e",
      "status": "running",
      "health_score": 95.2,
      "joints": {
        "1": {
          "joint_id": 1,
          "position": 1.23,
          "velocity": 0.51,
          "torque": 35.2,
          "temperature": 44.1,
          "current": 3.2,
          "vibration": 1.8,
          "error_code": 0,
          "score": 100.0
        },
        "2": { ... },
        "3": { ... },
        "4": { ... },
        "5": { ... },
        "6": { ... }
      }
    },
    "Robot2": { ... same structure ... },
    "Robot3": { ... same structure ... }
  },
  "alarms": [
    {
      "alarm_id": "ALM-0001",
      "robot_id": "Robot2",
      "joint_id": 3,
      "metric": "temperature",
      "severity": "warning",
      "message": "Robot2 Joint 3: temperature elevated (68.5)",
      "value": 68.5,
      "threshold": 65.0,
      "timestamp": 1749206400.0,
      "resolved": false
    }
  ],
  "predictions": [
    {
      "robot_id": "Robot2",
      "joint_id": 3,
      "metric": "temperature",
      "days_to_failure": 18.3,
      "confidence": 0.87,
      "trend_slope": 0.0012,
      "current_value": 68.5,
      "critical_threshold": 85.0
    }
  ],
  "diagnosis": null  // or latest diagnosis object
}
```

### AI Diagnosis event (fires ONCE, ~15s after alarm)
```json
{
  "type": "diagnosis",
  "robot_id": "Robot2",
  "joint_id": 3,
  "alarm_id": "ALM-0001",
  "diagnosis": "## Diagnosis: BEARING_WEAR\n\n**Confidence:** High (4/4 sensors)...",
  "model": "qwen3.6-plus",
  "tokens": 874,
  "latency_ms": 16500,
  "timestamp": 1749206416.0
}
```

---

## Dashboard Layout

Keep your 3D factory floor — it's impressive. Add clean data panels as overlays on top.

### Full Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                             │
│ Logo/Name    "Robo-Flow"         Fleet: 3 robots    Status: ONLINE   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  LEFT PANEL (fixed, 300px)    │    CENTER (3D factory floor)        │
│                               │                                     │
│  ┌─────────────────────────┐  │    Your existing Three.js scene     │
│  │ FLEET OVERVIEW          │  │    Keep the wireframe factory       │
│  │                         │  │    Keep the robot models             │
│  │ Robot1 UR10e      ██ 95 │  │    Keep drag/rotate                 │
│  │ Robot2 KR-16      ██ 67 │  │                                     │
│  │ Robot3 IRB-6700   ██ 88 │  │    Color the robot models by        │
│  │                         │  │    health score:                     │
│  │ (click to select)       │  │    95-100 = cyan/green glow         │
│  └─────────────────────────┘  │    50-94  = yellow/amber glow       │
│                               │    0-49   = red glow/pulse          │
│  ┌─────────────────────────┐  │                                     │
│  │ ALARMS                  │  │                                     │
│  │                         │  │                                     │
│  │ 🔴 Robot2 J3 temp 72°C │  │                                     │
│  │ 🟡 Robot2 J3 vib 5.2   │  │                                     │
│  │ ✅ Robot3 J6 resolved   │  │                                     │
│  │                         │  │                                     │
│  │ (newest on top, max 5)  │  │                                     │
│  └─────────────────────────┘  │                                     │
│                               │                                     │
│  ┌─────────────────────────┐  │                                     │
│  │ PREDICTIONS             │  │                                     │
│  │                         │  │                                     │
│  │ Robot2 J3 Temp          │  │                                     │
│  │ 18 days (87% conf)      │  │                                     │
│  │ ████████████░░░ → 85°C  │  │                                     │
│  └─────────────────────────┘  │                                     │
│                               │                                     │
├───────────────────────────────┴─────────────────────────────────────┤
│ BOTTOM PANEL (slides up when diagnosis arrives)                     │
│                                                                     │
│  🧠 AI DIAGNOSIS                                  Powered by Qwen  │
│                                                                     │
│  Robot2 Joint 3 — BEARING WEAR                                      │
│  Confidence: HIGH (4/4 sensors)                         ⏱ 16.5s    │
│                                                                     │
│  ✓ Temperature 72°C — exceeds KUKA >70°C threshold                 │
│  ✓ Vibration 5.2 mm/s — bearing signature                          │
│  ✓ Current 5.8A — motor compensating                               │
│  ✓ Torque stable — rules out load change                           │
│                                                                     │
│  ACTION: Replace bearing within 14 days                             │
│  PARTS: Nabtesco RV reducer (€2,000-8,000)                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### When a Robot is Clicked (Right Panel Appears)

```
┌──────────────────────────────────────────────┐
│ ROBOT DETAIL — Robot2 (KUKA KR-16)           │
│                                              │
│ Health: 67 ██████░░░░                        │
│ Status: Running                              │
│ Vendor: KUKA                                 │
│                                              │
│ JOINTS                                       │
│ J1  ██████████ 100  42°C  1.5mm/s  35Nm     │
│ J2  ██████████ 100  44°C  1.3mm/s  38Nm     │
│ J3  ██████░░░░  67  72°C  5.2mm/s  35Nm  ⚠ │
│ J4  ██████████ 100  41°C  1.2mm/s  32Nm     │
│ J5  ██████████ 100  40°C  1.1mm/s  30Nm     │
│ J6  ██████████ 100  39°C  1.0mm/s  28Nm     │
│                                              │
│ SENSOR TREND (Joint 3)                       │
│ 90│                                          │
│ 80│- - - - CRITICAL - - - - - -             │
│ 70│          ╱──────                         │
│ 65│- - -╱- - WARNING - - - -                │
│ 50│──╱──                                     │
│    └──────────────────────                    │
│     0    30    60    90  120s                 │
└──────────────────────────────────────────────┘
```

---

## Component Behavior Guide

### 1. Fleet Overview Cards (Left Panel, Always Visible)

**Data source:** `data.robots[robotId].health_score`, `.vendor`, `.model`, `.status`

```javascript
// For each robot
const color = score >= 80 ? '#2ecc71' : score >= 50 ? '#f39c12' : '#e74c3c';
```

- Show robot name, vendor, model
- Big health score number with color
- Small health bar
- Highlight selected robot (border glow)
- Click to select → shows detail panel + highlights in 3D

### 2. Alarm List (Left Panel, Below Fleet)

**Data source:** `data.alarms[]`

```javascript
// severity colors
const colors = {
  critical: '#e74c3c',  // red
  warning: '#f39c12',   // amber
  info: '#3498db'       // blue
};
```

- Show max 5-6 alarms, newest on top
- Format: `[severity icon] [robot] J[joint]: [message]`
- Resolved alarms get ✅ and fade opacity
- New alarm should briefly pulse/flash

### 3. Prediction Cards (Left Panel, Below Alarms)

**Data source:** `data.predictions[]`

- Only show predictions with `confidence > 0.5`
- Show: robot, joint, metric, days to failure, confidence %
- Progress bar: `current_value / critical_threshold`
- Color: green if >30 days, yellow if 7-30, red if <7

### 4. AI Diagnosis Panel (Bottom, Slides Up)

**Data source:** `data.type === "diagnosis"` event

THIS IS THE MOST IMPORTANT VISUAL MOMENT.

**Behavior:**
- Panel is HIDDEN by default (height: 0, or off-screen)
- When `type: "diagnosis"` arrives via WebSocket → slide up with animation
- Stay visible until next diagnosis or user closes it
- Also available in regular `update` messages as `data.diagnosis`

**Parsing the diagnosis text:**
```javascript
function parseDiagnosis(text) {
  // text is markdown. Key sections:
  const title = text.match(/## Diagnosis: (.+)/)?.[1] || 'Analyzing...';
  const confidence = text.match(/\*\*Confidence:\*\* (.+)/)?.[1] || '';

  // Evidence bullets
  const evidenceSection = text.split('**Evidence:**')[1]?.split('**')[0] || '';
  const evidence = evidenceSection.match(/- .+/g) || [];

  // Action
  const action = text.match(/\*\*Action:\*\*\n(.+)/)?.[1] || '';

  // Parts
  const parts = text.match(/\*\*Parts.*:\*\*\n(.+)/)?.[1] || '';

  return { title, confidence, evidence, action, parts };
}
```

**Display:**
```
🧠 AI DIAGNOSIS                              Powered by Qwen

[TITLE: e.g. "BEARING WEAR"]
[CONFIDENCE BADGE: "HIGH (4/4 sensors)" in green/yellow/red]
[LATENCY: "⏱ 16.5s" — shows it's real-time AI]

Evidence:
  ✓ [each evidence line with checkmark]

[ACTION BOX: highlighted, actionable text]
[PARTS: if available]
```

**Colors:**
- Panel background: darker than main bg, subtle border glow
- Title: white, bold
- Confidence HIGH: `#2ecc71`, MEDIUM: `#f39c12`, LOW: `#e74c3c`
- Evidence checkmarks: `#2ecc71`
- Action box: border `#00d4ff`, slight background tint

### 5. 3D Robot Colors (In Your Three.js Scene)

When you receive robot health scores, update the robot materials:

```javascript
function updateRobotColor(robotMesh, healthScore) {
  if (healthScore >= 80) {
    // Healthy: cyan/teal glow
    robotMesh.material.color.setHex(0x00d4ff);
    robotMesh.material.emissive.setHex(0x003344);
  } else if (healthScore >= 50) {
    // Warning: amber glow
    robotMesh.material.color.setHex(0xf39c12);
    robotMesh.material.emissive.setHex(0x332200);
  } else {
    // Critical: red pulse
    robotMesh.material.color.setHex(0xe74c3c);
    robotMesh.material.emissive.setHex(0x330000);
    // Add pulse animation
  }
}
```

### 6. Joint Animation (Nice-to-Have)

If you have robot arm models in 3D, animate joints based on `position` data:

```javascript
// data.robots.Robot1.joints[1].position = radians
robotArm.joint1.rotation.z = jointData.position;
```

---

## Design System

```
COLORS
  Background:      #0a0a1a (dark navy)
  Panel bg:        #121a2e (slightly lighter)
  Panel border:    #1e3050
  Accent:          #00d4ff (cyan)
  Healthy:         #2ecc71 (green)
  Warning:         #f39c12 (amber)
  Critical:        #e74c3c (red)
  Text primary:    #e8e8e8
  Text secondary:  #8899aa

FONT
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  Monospace for numbers: 'JetBrains Mono', 'Fira Code', monospace;

SPACING
  Panel padding: 16px
  Between panels: 12px
  Border radius: 8px

ANIMATIONS
  Panel slide: 300ms ease-out
  Color transitions: 500ms
  Alarm flash: 200ms pulse on new alarm
  AI diagnosis slide-up: 400ms ease-out (the "wow" moment)
```

---

## WebSocket Connection Code

```javascript
// Already in your index.html Section 14, but here's the key part:

const params = new URLSearchParams(location.search);
const RL_WS_URL = params.get('ws')
  || window.ROBOLINK_WS_URL
  || (location.protocol === 'https:'
      ? `wss://${location.host}/ws`
      : `ws://${location.hostname || 'localhost'}:8000/ws`);

let ws;
function connectWS() {
  ws = new WebSocket(RL_WS_URL);

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === 'update') {
      updateFleetCards(data.robots);
      updateAlarms(data.alarms);
      updatePredictions(data.predictions);
      update3DRobotColors(data.robots);
      if (data.diagnosis) {
        showDiagnosis(data.diagnosis);
      }
    }

    if (data.type === 'diagnosis') {
      // AI diagnosis just completed — this is the demo moment
      showDiagnosis(data);  // slide panel up with animation
    }
  };

  ws.onclose = () => setTimeout(connectWS, 2000);  // auto-reconnect
}
connectWS();
```

---

## Demo Flow (What Judges Should See)

```
0:00  Dashboard loads. 3D factory floor visible.
      Left panel: 3 robots, all green (95, 100, 88).
      No alarms. No diagnosis. Clean.

0:30  Robot2 health starts dropping (100 → 80 → 67).
      Robot2 card turns yellow.
      Robot2's 3D model changes from cyan to amber.

0:45  First alarm slides into alarm list.
      "⚠ Robot2 J3: temperature elevated (68°C)"

1:00  More alarms stack up.
      Prediction appears: "18 days to failure (87%)"

1:15  🧠 AI DIAGNOSIS panel slides up from bottom.
      "BEARING WEAR — 4/4 sensors confirm"
      THIS IS THE MOMENT. Pause here. Let judges read it.

1:30  Point out: vendor-specific (KUKA specs),
      actionable (part numbers, timeline),
      not hallucinated (grounded in real docs).

2:00  Pitch business case.
3:00  Done.
```

---

## REST Endpoints (for testing/debugging)

```
GET  /api/health              → {"status":"ok","robots":3}
GET  /api/robots              → all robot states
GET  /api/alarms              → active alarms
GET  /api/predictions         → failure predictions
GET  /api/diagnosis           → latest AI diagnosis
GET  /api/diagnosis/history   → all past diagnoses

Backend URL: https://web-production-27a5.up.railway.app
```

---

## Priority Order (What to Build First)

```
1. LEFT PANEL — Fleet cards with health scores     (30 min)
2. LEFT PANEL — Alarm list                         (20 min)
3. BOTTOM — AI Diagnosis panel with slide-up       (30 min)
4. LEFT PANEL — Prediction cards                   (15 min)
5. 3D — Color robots by health score               (15 min)
6. RIGHT PANEL — Robot detail on click             (if time)
7. RIGHT PANEL — Sensor trend chart                (if time)
```

Items 1-5 are MUST HAVE for the demo.
Items 6-7 are nice-to-have.
