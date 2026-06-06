# Troubleshooting & Fixed Errors

A log of wiring/runtime errors found in RoboLink, their root causes, and fixes.
Newest first.

---

## 2026-06-06 — Dashboard never received live data (3 bugs)

**Symptom:** `dashboard/index.html` only ever showed mock data. The live WebSocket
never delivered a single frame, even with `sim_server.py` and `server.py` both running.

### 1. No Python environment / dependencies installed
- **Cause:** Fresh checkout had no virtualenv and no installed packages, so
  `server.py` / `sim_server.py` couldn't even import (`ModuleNotFoundError: structlog`).
- **Fix:** Create an isolated env and install requirements:
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  ```
  (`.venv` is already in `.gitignore`.)

### 2. `uvicorn` had no WebSocket support → every `/ws` upgrade returned 404
- **Cause:** `requirements.txt` pinned bare `uvicorn>=0.20`, which does **not** bundle a
  WebSocket implementation. On startup uvicorn logged
  `No supported WebSocket library detected` and rejected every `/ws` handshake with
  `HTTP 404 Not Found` / `Unsupported upgrade request`. The dashboard silently fell back
  to mock data forever.
- **Fix:** Pin the standard extra (pulls in `websockets`, `httptools`, `uvloop`, …):
  ```
  uvicorn[standard]>=0.20
  ```
  in `requirements.txt`, then reinstall.

### 3. `UnboundLocalError: local variable 'ws_clients'` crashed the broadcaster
- **Cause:** Both `ws_broadcaster()` and `_run_diagnosis()` in `server.py` did
  `ws_clients -= dead`. Augmented assignment binds the name as a **local** for the whole
  function, so the earlier `if ws_clients:` read raised
  `UnboundLocalError: cannot access local variable 'ws_clients'`. The broadcaster task
  died on its **first tick**, so no `update` frame was ever sent. (Visible in logs as
  repeated `Task exception was never retrieved`.)
- **Fix:** Mutate the module-level set in place instead of rebinding:
  ```python
  ws_clients.difference_update(dead)   # was: ws_clients -= dead
  ```
  Applied at both sites (`server.py` ~lines 194 and 217).

**Verification (all green after fixes):**
- `GET /dashboard/` → 200, `three.min.js` → 200
- WebSocket `/ws` delivers `update` frames every 500ms: 3 robots, 6 joints each, live
  health scores, alarms, and predictions — matching the shape `applyRoboLinkUpdate()`
  expects in `index.html` (Section 14).
- 0 task exceptions in the backend log.

---

## Outstanding (not a code bug)

### AI diagnosis (Qwen) returns HTTP 403 — free tier exhausted
- **Symptom:** The dashboard's AI diagnosis panel shows
  `Diagnosis unavailable: Error code: 403 ... The free tier of the model has been exhausted.`
- **Cause:** Account-side quota on the Qwen `qwen-plus` key used by `_run_diagnosis`.
  The broadcast mechanism works — only the model call fails, and it degrades gracefully.
- **Fix:** Add credit / disable "free tier only" mode on the Qwen account, or swap the
  diagnostics provider. Live telemetry / alarms / predictions are unaffected.
