# Dashboard (3D Factory Twin) — orientation

This folder is the **frontend** for RoboLink: a single self-contained HTML file
(`index.html`) using vanilla **Three.js r128** (bundled in `three.min.js`, no build step,
no CDN). The aesthetic is wireframe-edges-on-dark with HUD overlays; the scene is
data-driven so machines can be moved/added by editing one object.

> The repo root `CLAUDE.md` covers the Python backend. **This file covers the frontend.**
> When working on the dashboard, read this one.

## Run
The backend serves this dir (`server.py` mounts `/dashboard`):
```bash
python sim_server.py && uvicorn server:app --port 8000
# open http://localhost:8000/dashboard/
```
A built-in mock keeps the scene alive with **no backend**; it yields to the live
WebSocket the moment real data arrives (and falls back if it drops).

## How `index.html` is organized
The `<script>` is divided into 15 numbered banner-commented sections. Read in order:

| Section | What it does |
|---|---|
| 1. LAYOUT DATA | The `LAYOUT` object — facility, floors, machines. **Source of truth.** |
| 2. CONSTANTS | `STATUS_COLORS`, `TYPE_LABELS`, `THRESHOLDS`, `SEVERITY_COLORS`, `ROBOT_PROFILES`, `ARM_TYPES` |
| 3. STATE | Pub/sub. `state.telemetry`, `state.history`, `state.events`, `updateTelemetry()` |
| 4. THREE.JS SETUP | scene, camera, renderer |
| 5. HELPERS / PRIMITIVES | `mkBox`, `mkCyl`, `lm`, materials, `applyWireframeOverlay` |
| 6. MACHINE FACTORIES | one fn per machine type, registered in `MACHINE_FACTORIES` |
| 7. SCENE BUILDERS | `buildFloorScene` reads layout; `animateFloor`; status→wire color; click hitboxes |
| 8. BUILDING (section view) | cross-section shell + scaled neutral miniatures of each floor; hover glow |
| 9. HUD | corner overlays per view |
| 10. FLOATING BADGES | 3D→2D projection; status dots, full label on click, distance scaling |
| 11. SIDE PANEL | per-machine inspector. Arms = robot view (health/joints/trends/alarms/prediction/AI diagnosis); others = generic |
| 12. VIEW MGMT | building ↔ floors; camera configs; zoom |
| 13. INPUT | drag/tap/raycast, wheel+pinch zoom, floor hover + hover dashboard |
| 14. DATA | **live RoboLink WebSocket client + mock fallback** |
| 15. BOOT | subscribe UI to state, start data, render loop |

## Live data wiring (Section 14)
- Connects to `ws://<host>:8000/ws`. Handles `type:"update"` (robots/alarms/predictions/diagnosis)
  and `type:"diagnosis"` messages.
- `ROBOT_MAP` maps the backend's `Robot1..3` → arm machines `ARM-01..03`. Edit to retarget.
- Everything routes through `updateTelemetry(id, patch)`; badges, panel, floor health-map,
  and the building hover-dashboard all react via pub/sub. Don't bypass it.

## Common tasks
- **Add/move/remove a machine** → edit `LAYOUT` (Section 1). Both the floor scenes and the
  building miniatures rebuild from it.
- **Add a machine type** → write `makeX(m)` in Section 6, register in `MACHINE_FACTORIES`,
  add a `TYPE_LABELS` entry, then use `type:'x'` in `LAYOUT`. Call `tagMachine(g, m)`.
- **Map more robots / change targeting** → edit `ROBOT_MAP` (Section 14).
- **Retheme** → `STATUS_COLORS` / `SEVERITY_COLORS` / `THRESHOLDS` (Section 2).
- **Realistic GLB models** → `makeGLBModel` stub (Section 6) + `applyWireframeOverlay` (Section 5).

## Conventions
- Wireframe `LineSegments` only — no filled meshes except invisible click hitboxes.
- Status drives appearance via `state.telemetry[id].status`; per-machine materials are cloned
  at boot so they recolor independently.
- Keep the section banners — they're how you (and Claude) navigate the file.
- No npm / no CDN — CDN-free is intentional (`three.min.js` is vendored).
