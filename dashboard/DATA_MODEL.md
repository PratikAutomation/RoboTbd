# Data Model

## `LAYOUT` (Section 1) — scene source of truth
What machines exist and where. Both the per-floor scenes and the scaled miniatures in the
building cross-section are built from this.

```js
const LAYOUT = {
  facility: 'PLANT-07',
  floors: [
    {
      id: 'floor4', name: 'Process Floor', accent: 0xff5ec8,
      machines: [
        { id: 'ARM-01', type: 'robot_arm', label: 'Pick Arm 1', position: [-12,0,4], rotation: [0,0,0] },
        // ...
      ],
      flows: [{ type: 'parts_on_conveyor', count: 5 }]   // visual-only particles
    }
  ]
};
```

Common machine fields: `id` (unique), `type` (must match `MACHINE_FACTORIES`), `label`,
`position [x,y,z]`, `rotation [rx,ry,rz]`. Type-specific: conveyors use `from/to/width`;
silos `height/radius`; workstations `size`; bins `color`; welding arms `mount`.

## Runtime telemetry (`state.telemetry[id]`)
Independent of `LAYOUT`. Set by the live WebSocket (Section 14) or the mock fallback. Two
shapes:

**Arm machines** (`robot_arm` / `welding_arm`) — the full RoboLink robot schema:
```js
{
  robot_id, vendor, model, status,        // running|idle|maintenance|error|offline
  safety_state, health_score,             // 0..100
  joints: { 1..6: { joint_id, position, velocity, torque, temperature,
                    current, vibration, error_code, score } },
  alarms: [ { alarm_id, joint_id, metric, severity, message, value, threshold, resolved } ],
  prediction: { joint_id, metric, days_to_failure, confidence, current_value, critical_threshold } | null,
  diagnosis: { joint_id, diagnosis, model, latency_ms, ... } | null   // AI (Qwen) from backend
}
```

**Other machines** — lighter: `{ status, utilization, partsProcessed, temperature, rpm,
health_score, alarms }`.

The panel (Section 11) branches on `telemetry.joints`: present → robot view; absent →
generic view. `state.history[id]` is a ring buffer (last 48) feeding the sparklines;
`state.events` is the global status-change log.

## Status → color (Section 2)
```js
STATUS_COLORS = { running:'#4ee5ff', idle:'#5b8a96', maintenance:'#ffb84e',
                  error:'#ff5e5e', offline:'#3a3a3a' };
```
Drives badge color, panel border, and per-machine wire color (cloned materials).

## Sensor thresholds (Section 2) — match the backend
```js
THRESHOLDS = { temperature:{warning:65,critical:80}, torque:{warning:100,critical:130},
               vibration:{warning:4,critical:7},     current:{warning:7,critical:9} };
SEVERITY_COLORS = { info:'#5ec8ff', warning:'#ffb84e', critical:'#ff5e5e' };
```

## Robot → machine mapping (Section 14)
```js
const ROBOT_MAP = { Robot1:'ARM-01', Robot2:'ARM-02', Robot3:'ARM-03' };
```
Backend `Robot1..3` drive these arms. Status is derived from `health_score`
(≥80 running, ≥50 maintenance, <50 error) so degradation shows spatially. Other machines
run on mock telemetry.

## Camera configs (Section 12)
Each view (`building`, `floor1..4`) has `{ r, lookX, lookY, lookZ, yaw, pitch }` — orbit
radius, look-at point, initial angles. Zoom mutates `radius` within `[0.4, 3]×` of `r`.
