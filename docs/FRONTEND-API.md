# Frontend API Guide -- For Javi

## Quick Start

```bash
# 1. Backend will run on:
#    HTTP:      http://localhost:8000
#    WebSocket: ws://localhost:8000/ws

# 2. Your files go in:
#    dashboard/index.html
#    dashboard/chart.min.js  (Chart.js v4 bundled, no CDN)
#    dashboard/style.css     (optional, can be inline)

# 3. To test before backend is ready, use the mock data at bottom of this doc
```

## WebSocket (Real-time Updates)

Connect to `ws://localhost:8000/ws`. You'll receive JSON messages every 500ms:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type = "update"
  // data.robots = { ... }
  // data.alarms = [ ... ]
  // data.predictions = [ ... ]
};
```

### Message Format

```json
{
  "type": "update",
  "robots": {
    "Robot1": {
      "robot_id": "Robot1",
      "vendor": "ur",
      "model": "UR10e",
      "status": "running",
      "safety_state": "normal",
      "health_score": 94.2,
      "joints": {
        "1": {
          "joint_id": 1,
          "position": 1.2345,
          "velocity": 0.5123,
          "torque": 35.20,
          "temperature": 44.1,
          "current": 3.20,
          "vibration": 1.800,
          "error_code": 0,
          "score": 100.0
        },
        "2": { "...same fields..." },
        "3": { "...same fields..." },
        "4": { "...same fields..." },
        "5": { "...same fields..." },
        "6": { "...same fields..." }
      }
    },
    "Robot2": {
      "robot_id": "Robot2",
      "vendor": "kuka",
      "model": "KR-16",
      "status": "running",
      "health_score": 67.3,
      "joints": { "...same structure..." }
    },
    "Robot3": {
      "robot_id": "Robot3",
      "vendor": "abb",
      "model": "IRB-6700",
      "status": "running",
      "health_score": 88.5,
      "joints": { "...same structure..." }
    }
  },
  "alarms": [
    {
      "alarm_id": "ALM-0001",
      "robot_id": "Robot2",
      "joint_id": 3,
      "metric": "temperature",
      "severity": "warning",
      "message": "Robot2 Joint 3: temperature elevated (68.5)",
      "value": 68.50,
      "threshold": 65.0,
      "timestamp": 1749206400.0,
      "resolved": false
    },
    {
      "alarm_id": "ALM-0002",
      "robot_id": "Robot2",
      "joint_id": 3,
      "metric": "vibration",
      "severity": "critical",
      "message": "Robot2 Joint 3: vibration critical (7.2)",
      "value": 7.20,
      "threshold": 7.0,
      "timestamp": 1749206450.0,
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
      "critical_threshold": 85.0,
      "timestamp": 1749206400.0
    }
  ]
}
```

## REST API Endpoints

```
GET /api/robots          → same as robots{} from WebSocket
GET /api/alarms          → same as alarms[] (active only)
GET /api/alarms/history  → all alarms including resolved
GET /api/predictions     → same as predictions[]
```

## 3 Robots in the Demo

| Robot ID | Vendor | Model | Behavior | Color Suggestion |
|----------|--------|-------|----------|-----------------|
| Robot1 | Universal Robots | UR10e | Healthy, stable | Green |
| Robot2 | KUKA | KR-16 | Joint 3 degrades over time | Yellow -> Red |
| Robot3 | ABB | IRB-6700 | Random anomaly spikes | Orange flickers |

## Dashboard Sections to Build

### 1. Robot Cards (top row)
One card per robot showing:
- Robot name + vendor/model
- Health score 0-100 (big number, color-coded)
  - 80-100: green
  - 50-79: yellow/orange
  - 0-49: red
- Status badge ("running" / "stopped" / "error")
- Mini sparkline or bar for each joint score

### 2. Sensor Charts (middle)
Chart.js line charts. User clicks a robot card to see its joint data.
- X axis: time (rolling 60 seconds)
- Y axis: sensor value
- One chart per metric (temperature, torque, vibration, current)
- Draw threshold lines (warning=dashed yellow, critical=dashed red):
  - temperature: warning=65, critical=80
  - torque: warning=100, critical=130
  - vibration: warning=4, critical=7
  - current: warning=7, critical=9

### 3. Alarm Panel (right side or bottom)
- List of active alarms, newest on top
- Color by severity: critical=red, warning=yellow, info=blue
- Show: timestamp, robot, joint, message, value
- Resolved alarms fade out or move to history

### 4. Prediction Panel (bottom)
- Cards showing predicted failures
- "Robot2 Joint 3 Temperature: 18 days to failure (87% confidence)"
- Progress bar showing how close to critical threshold
- Only show predictions with confidence > 50%

### 5. Audit Log (optional, bottom)
- Scrolling log of all events
- Compact format: [time] [robot] [event]

## Design Notes
- Dark theme (background: #0a0a1a or similar)
- Accent color: #00d4ff (cyan)
- Font: system-ui or Segoe UI
- No external CDN dependencies -- bundle Chart.js locally
- Mobile responsive is nice-to-have, desktop-first

## Mock Data for Testing Before Backend

Paste this in browser console to simulate WebSocket data:

```javascript
// Mock WebSocket for frontend testing
function mockData() {
  return {
    type: "update",
    robots: {
      Robot1: {
        robot_id: "Robot1", vendor: "ur", model: "UR10e",
        status: "running", health_score: 95.0 + Math.random() * 5,
        joints: Object.fromEntries([1,2,3,4,5,6].map(j => [j, {
          joint_id: j, position: Math.sin(Date.now()/1000 + j) * 2,
          velocity: Math.cos(Date.now()/1000 + j) * 1,
          torque: 30 + Math.random() * 10, temperature: 42 + Math.random() * 3,
          current: 3 + Math.random(), vibration: 1.5 + Math.random() * 0.5,
          error_code: 0, score: 95 + Math.random() * 5
        }]))
      },
      Robot2: {
        robot_id: "Robot2", vendor: "kuka", model: "KR-16",
        status: "running", health_score: 60 + Math.random() * 20,
        joints: Object.fromEntries([1,2,3,4,5,6].map(j => [j, {
          joint_id: j, position: Math.sin(Date.now()/1000 + j),
          velocity: 0.5, torque: j===3 ? 80+Math.random()*30 : 30+Math.random()*10,
          temperature: j===3 ? 65+Math.random()*15 : 42+Math.random()*3,
          current: j===3 ? 5+Math.random()*2 : 3+Math.random(),
          vibration: j===3 ? 4+Math.random()*3 : 1.5+Math.random()*0.5,
          error_code: 0, score: j===3 ? 40+Math.random()*20 : 95+Math.random()*5
        }]))
      },
      Robot3: {
        robot_id: "Robot3", vendor: "abb", model: "IRB-6700",
        status: "running", health_score: 85 + Math.random() * 10,
        joints: Object.fromEntries([1,2,3,4,5,6].map(j => [j, {
          joint_id: j, position: Math.sin(Date.now()/1000 + j) * 1.5,
          velocity: 0.8, torque: 35+Math.random()*15,
          temperature: 44+Math.random()*5, current: 3.5+Math.random(),
          vibration: 2+Math.random()*1, error_code: 0,
          score: 85+Math.random()*15
        }]))
      }
    },
    alarms: Math.random() > 0.5 ? [{
      alarm_id: "ALM-0001", robot_id: "Robot2", joint_id: 3,
      metric: "temperature", severity: "warning",
      message: "Robot2 Joint 3: temperature elevated (68.5)",
      value: 68.5, threshold: 65.0, timestamp: Date.now()/1000, resolved: false
    }] : [],
    predictions: [{
      robot_id: "Robot2", joint_id: 3, metric: "temperature",
      days_to_failure: 18.3, confidence: 0.87, trend_slope: 0.0012,
      current_value: 68.5, critical_threshold: 85.0, timestamp: Date.now()/1000
    }]
  };
}

// Simulate WebSocket updates every 500ms
setInterval(() => {
  if (window.handleUpdate) window.handleUpdate(mockData());
}, 500);
```

## File Structure

```
dashboard/
  index.html       ← main file (JS inline or in <script>)
  chart.min.js     ← Chart.js v4 (download from chartjs.org, ~200KB)
  style.css        ← optional
```

Download Chart.js: https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js
Save as dashboard/chart.min.js
