# Dashboard — 3D Factory Twin

A self-contained 3D digital-twin frontend for RoboLink. Wireframe factory building you
can orbit; tap a floor to drop into it; tap a machine to inspect live telemetry. Robot
arms render the full RoboLink schema — health score, 6 joints, sensor trends with
threshold lines, alarms, failure prediction, and the AI diagnosis.

## Run

The backend serves this directory automatically (`server.py` mounts `/dashboard`):

```bash
python sim_server.py            # simulated OPC-UA server (real recorded joint data)
uvicorn server:app --port 8000  # REST + WebSocket
# open http://localhost:8000/dashboard/
```

It connects to `ws://<host>:8000/ws` for live updates. **No backend needed to demo:** a
built-in mock simulator keeps the scene alive and automatically yields to the live feed
the moment real data arrives (and falls back if the socket drops).

## Files

- `index.html` — the entire app (vanilla JS + Three.js; section-divided at the bottom)
- `three.min.js` — Three.js r128, bundled locally (no CDN, per repo convention)

## How the data maps

The 3 backend robots map onto 3 arm machines in the scene (`ROBOT_MAP` in Section 14 of
`index.html`): `Robot1→ARM-01`, `Robot2→ARM-02`, `Robot3→ARM-03`. Each robot's
`health_score`, `joints`, `alarms`, `predictions`, and AI `diagnosis` drive that arm's
panel and its color on the floor. The other machines run on mock telemetry (decoration /
future expansion). Edit `ROBOT_MAP` to retarget, and the scene layout lives in `LAYOUT`
(Section 1).

Everything routes through `updateTelemetry(id, patch)` via a small pub/sub, so badges,
panel, floor health-map, and the building hover-dashboard all react automatically.
