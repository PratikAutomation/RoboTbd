# Backend Hosting Requirements

For whoever deploys the RoboLink backend (the FastAPI + OPC-UA stack) so the
Vercel-hosted dashboard can show **live** data instead of mock.

The frontend is static and lives on Vercel. The backend cannot — read **Why not Vercel**
below. This doc is the contract the backend host must satisfy.

---

## Why not Vercel (or any serverless platform)

The backend needs three **long-lived** things that serverless functions (Vercel, AWS
Lambda, Cloudflare Workers) do not support:

1. A persistent **WebSocket server** (`/ws`) holding open client connections.
2. A continuous **OPC-UA reader** background task (`opcua_reader` in `server.py`).
3. A 500ms **broadcaster** background task pushing telemetry to all clients.

Use a platform that runs a normal long-running process with WebSocket support:
**Render, Railway, Fly.io**, or a plain VM/container. Not Vercel.

---

## What runs

Two processes (for the demo). In production, #1 is replaced by the customers' real robot
OPC-UA endpoints.

| # | Process | Command | Role |
|---|---------|---------|------|
| 1 | OPC-UA simulator | `python sim_server.py` | Serves simulated robot data on `opc.tcp://0.0.0.0:4840/robolink/server` (3 robots, 72 nodes, real recorded joint data) |
| 2 | API + WebSocket | `uvicorn server:app --host 0.0.0.0 --port 8000` | FastAPI: REST `/api/*`, WebSocket `/ws`, reads OPC-UA, broadcasts every 500ms |

Process #2 connects to #1 as an OPC-UA **client**, so both must run and #2 must be able to
reach #1's endpoint. Simplest: run both in one container/host (then `localhost:4840` works
as-is).

## Runtime & dependencies

- **Python 3.11+** (uses match statements, `X | Y` unions, `asyncio.TaskGroup`). Verified on 3.14.
- `pip install -r requirements.txt` → `asyncua`, `fastapi`, **`uvicorn[standard]`**
  (the `[standard]` extra is required — it provides the WebSocket library; bare `uvicorn`
  404s every `/ws` upgrade), `structlog`, `numpy`, `openai`.

## Ports

| Port | Process | Exposure |
|------|---------|----------|
| 4840 | OPC-UA sim server | **Internal only** — server.py → sim_server. Do not expose publicly. |
| 8000 | uvicorn (HTTP + WS) | **Public** — the dashboard connects here. Platform terminates TLS in front of it. |

## Networking / TLS

- The dashboard is served over **HTTPS**, so it can only open a **`wss://`** (secure)
  WebSocket — an `ws://` connection from an HTTPS page is blocked by the browser.
  → The platform must put **TLS in front of port 8000** (Render/Railway/Fly do this
  automatically and give you an `https://…`/`wss://…` hostname).
- **CORS is already wide open** (`allow_origins=["*"]` in `server.py`), so the Vercel
  origin can connect with no change. (Tighten to the Vercel domain for production.)

## Environment variables

| Var | Required? | Purpose |
|-----|-----------|---------|
| `DASHSCOPE_API_KEY` | For AI diagnosis only | Qwen (Alibaba DashScope, OpenAI-compatible) key used by `robolink/diagnosis.py`. Without a valid, funded key the AI panel shows a graceful "Diagnosis unavailable" — **everything else (telemetry, alarms, predictions) works regardless.** |

> ⚠️ **Security:** `robolink/diagnosis.py` currently hardcodes a fallback key in source
> (committed to git history). It must be **rotated** and the hardcoded fallback removed —
> set the key only via `DASHSCOPE_API_KEY`. See `docs/troubleshooting.md`.

## Config currently hardcoded (recommend making env-configurable)

These are fine as-is for a single-host deploy but should become env vars for flexibility:

- `server.py:45` — `OPCUA_ENDPOINT = "opc.tcp://localhost:4840/robolink/server"`
  (hardcoded `localhost`; needs changing if sim_server runs on a different host).
- uvicorn port (8000) — set via the start command / platform config.

---

## Acceptance check (backend is "done" when…)

From any machine, against the public host:

```bash
# REST is up
curl https://<backend-host>/api/health           # -> {"status":"ok",...}

# WebSocket delivers live frames (needs wss + a WS client)
# Expect type:"update" frames ~every 0.5s with robots/alarms/predictions
```

Then the dashboard goes live by pointing at it — **no rebuild**:
`https://<your-app>.vercel.app/?ws=wss://<backend-host>/ws`
(or set `window.ROBOLINK_WS_URL`, or co-host so `wss://<same-host>/ws` resolves).

The WS payload contract the frontend expects is documented in
`dashboard/DATA_MODEL.md` and `docs/FRONTEND-API.md`.
