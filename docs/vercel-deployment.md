# Deploying the Dashboard to Vercel

How to put the RoboLink dashboard (`dashboard/`) online as a static site on Vercel.

**TL;DR:** It's a static frontend — no build step. Import the repo into Vercel with the
**Root Directory set to `dashboard`**. It runs on mock data until the backend is hosted;
pointing it at a live backend later needs no redeploy.

---

## Who has to do the import (and why)

The repo `PratikAutomation/RoboTbd` is under a **personal GitHub account**, so the initial
Vercel import can only be done by the **account owner (Pratik)**. Vercel connects to a repo
by installing the **Vercel GitHub App** on the owning account, and a GitHub App can only be
authorized on a personal account by that account's owner — write collaborators can push
code but cannot authorize the app.

Once imported, the owner can **add collaborators to the Vercel project** so anyone on the
team can manage deployments, previews, and env vars without further owner involvement.

---

## One-time setup (repo owner)

1. Go to **[vercel.com](https://vercel.com)** → sign in with **GitHub** → **Add New… → Project**.
2. **Import** the **RoboTbd** repo (authorize Vercel for GitHub if prompted).
3. On the configure screen, set:
   - **Root Directory → `dashboard`** — click *Edit* and select the `dashboard` folder.
     **This is the critical step.** If skipped, Vercel tries to build the Python backend at
     the repo root and the deploy fails.
   - **Framework Preset → Other**
   - **Build Command → empty**
   - **Output Directory → empty**
   - **Install Command → empty**
4. Click **Deploy**. You'll get a production URL like `https://robotbd.vercel.app`.

### Add the team
Project → **Settings → Members** (create a Team if prompted) → invite teammates by their
Vercel email. They can then manage deploys themselves.

---

## After setup (everyone)

- **Auto-deploy:** every push to **`main`** deploys to the production URL.
- **Preview deploys:** every branch / pull request gets its own preview URL — eyeball
  changes before merging to `main`.
- The `dashboard/vercel.json` (clean URLs + long-cache for `three.min.js`) is picked up
  automatically; no extra config needed.

---

## Mock data now, live data later

The deployed site runs on the **built-in mock simulator** (robots, alarms, predictions all
animate) — fine for a shareable visual demo. It can't show live data yet because the
backend (FastAPI + WebSocket + OPC-UA) **cannot run on Vercel** — see
[`backend-deployment.md`](./backend-deployment.md) for the why and the hosting requirements.

When the backend is hosted (on Render / Railway / Fly.io — something that supports
persistent WebSocket connections), point the dashboard at it **with no redeploy**:

```
https://<your-app>.vercel.app/?ws=wss://<backend-host>/ws
```

(The WebSocket URL also accepts `window.ROBOLINK_WS_URL`, and on HTTPS defaults to
`wss://<same-host>/ws` if the backend is ever co-hosted. See Section 14 of
`dashboard/index.html`.) The backend must serve over **`wss://`** — an HTTPS page cannot
open an insecure `ws://` socket.
