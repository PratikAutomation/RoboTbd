# RoboLink Hackathon Game Plan -- June 6, 2026

**AI Beavers Founder Hackathon | House of AI Hamburg**
**Hongkongstrasse 2, 20457 Hamburg**

---

## Tonight's Checklist (June 5)

- [ ] Push repo to public GitHub
- [ ] `pip install asyncua fastapi uvicorn[standard] structlog numpy`
- [ ] `python -c "import asyncua, fastapi, uvicorn, structlog, numpy; print('ALL GOOD')"`
- [ ] Download Chart.js locally: `curl -o dashboard/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js`
- [ ] Create pitch deck skeleton (7 slides, Google Slides or Canva, dark theme)
- [ ] Read build plan fully: `docs/superpowers/plans/2026-06-04-robot-health-monitor.md`
- [ ] Read spec fully: `docs/superpowers/specs/2026-06-04-robot-health-monitor-design.md`
- [ ] Memorize one-liner (say it out loud 3 times)
- [ ] Text Danfoss colleague for evidence quote
- [ ] Charge laptop
- [ ] Pack: charger, adapters (USB-C/HDMI/power), water bottle, phone
- [ ] Set alarm for 8:00 AM
- [ ] Sleep

---

## The One-Liner (Memorize This)

> "73% of factories run robots from multiple vendors. Each vendor ships their own monitoring tool. Nobody connects them. RoboLink gives you one dashboard for your entire mixed-vendor robot fleet with health scores, alarms, and failure predictions. Plug in any robot, works in minutes."

---

## Files to Have Open Tomorrow

```
Tab 1: docs/superpowers/plans/2026-06-04-robot-health-monitor.md  (build plan)
Tab 2: docs/superpowers/specs/2026-06-04-robot-health-monitor-design.md  (spec)
Tab 3: docs/robolink-blueprint.md  (pitch reference)
```

---

## Build Schedule (June 6)

```
09:00   Arrive. Check in. Light breakfast. Settle in.
09:45   Intro from organizers. Be in the room.
10:00   START BUILDING.

10:00   Task 1-3: scaffolding + base class + formatter           30 min
10:30   Task 4-5: alarm engine + prediction engine                40 min
11:10   Task 6:   robot health monitor                            20 min
11:30   Task 7-8: OPC-UA source + sim server                     40 min
12:10   Task 9:   FastAPI backend                                 30 min
12:40   VERIFY: full backend running, curl endpoints              10 min
        - curl http://localhost:8081/status (sim server)
        - curl http://localhost:8080/api/robots (backend)
        If both respond: backend is done. Move to dashboard.

13:00   LUNCH (eat fast, 15 min max)

13:15   Task 10: DASHBOARD (biggest block, highest risk)          3 hr
        P0: Robot cards with health scores                        30 min
        P0: Chart.js sensor trend charts                          45 min
        P0: Alarm panel with severity colors                      30 min
        P1: Prediction panel                                      20 min
        P1: Audit log                                             15 min
        P2: Animations, branding (CUT if behind)

16:15   Task 11: integration test + demo practice                 30 min
        - Start sim server
        - Start backend
        - Open dashboard
        - curl inject gradual_degradation → watch Robot #2 degrade
        - curl inject sudden_vibration → watch Robot #3 spike
        - Run demo flow 3 times

16:45   BUFFER for bugs and fixes                                 45 min

17:30   PITCH DECK: insert real dashboard screenshots             30 min
        - Screenshot: fleet overview (all green)
        - Screenshot: warning state (Robot #2 amber)
        - Screenshot: critical state (Robot #3 red)

18:00   DINNER (keep polishing pitch, practice out loud)

18:30   Final demo rehearsal x3                                   30 min

19:00   SUBMIT (hard deadline, no exceptions)
        - Push all code to public GitHub
        - Submit form with repo link + pitch deck
        - Even if unfinished, SUBMIT SOMETHING

19:15   Pitch rooms open. Pitch: 3 min, no Q&A in prelims.
```

---

## Checkpoint Gates (Decision Points)

**12:40 -- Backend checkpoint**
Backend responds to curl? YES → dashboard. NO → debug backend, skip dashboard polish.

**14:30 -- Dashboard P0 checkpoint**
Robot cards + charts working? YES → build P1. NO → stop adding features, fix what's broken.

**16:00 -- Ship-or-cut checkpoint**
Dashboard works end-to-end? YES → polish. NO → cut P2, cut animations, ship what works.

**17:00 -- Two-hour warning**
Is demo runnable? YES → screenshots + pitch deck. NO → stop coding, make existing code demo-ready.

**18:30 -- Final gate**
Can you run the 90-second demo without crashing? YES → ready. NO → pre-record a screen capture as backup.

---

## Demo Script (90 Seconds)

```
0:00   Dashboard opens. 3 robots. All green. Numbers streaming.
       "RoboLink. Three robot arms, three different vendors,
        one dashboard. Live OPC-UA health data."

0:15   Robot #2 Joint 3 temperature starts climbing.
       Trend line visibly bending upward.
       "Watch Robot 2. Joint 3 temperature drifting."

0:30   Health drops 94 → 67. Card turns amber. Warning alarm fires.
       Prediction appears: 18 days to failure, 83% confidence.
       "Warning. Predicted failure in 18 days. Schedule maintenance
        on a weekend, not an emergency call on Tuesday."

0:45   Robot #3 vibration spikes. Card turns red. Critical alarms.
       "Robot 3. Sudden spike. Immediate inspection."

0:55   Point to alarm panel and audit log.
       "Every event logged. Full audit trail. One screen."

1:05   Pitch.
       "I build industrial monitoring platforms professionally.
        Every robot vendor ships their own dashboard.
        Nobody connects them. RoboLink does.
        One dashboard. Any vendor. Works in minutes."

1:15   Done.
```

---

## Pitch Deck (7 Slides)

### Slide 1: Hook
"Your robot will fail in 18 days. We know because the data told us."
[Dashboard screenshot with prediction highlighted]

### Slide 2: Problem
- 73% of factories run 2+ robot vendors
- Each vendor ships their own monitoring tool
- Maintenance manager: 3 dashboards, 3 alarm systems, Excel to cross-reference
- Unplanned downtime: $10-50K per hour
- One failure event: $50-250K total cost

### Slide 3: Solution + Demo
- One dashboard for your entire mixed-vendor robot fleet
- Live health scores, smart alarms, failure predictions
- QR code to live demo
- [Dashboard screenshot]

### Slide 4: Why Now
- OPC-UA is now standard on every new robot (UR, KUKA, ABB, FANUC)
- AI can interpret multivariate sensor degradation patterns
- Cost of building software collapsed 10-100x
- Maintenance workforce aging (avg technician age: 52 in Germany)

### Slide 5: Market + Competition
- Predictive maintenance market: $15.9B, growing 25% CAGR
- UR Insight: UR only. KUKA Connect: KUKA only. ABB Ability: ABB only.
- Ignition: general SCADA, no robot intelligence
- AWS/Azure IoT: raw infrastructure, build-it-yourself
- RoboLink: only vendor-agnostic + robot-aware solution

### Slide 6: Business Model
- $50/robot/month. 12 robots avg = $7,200/year per factory
- ROI: one prevented failure ($50-250K) pays for 7-35 years
- Expansion: fleet management, compliance reporting, AI data pipeline
- [Evidence quote from Danfoss colleague if available]

### Slide 7: Team + Ask
- Pratik Patil
- IoT Data & Connectivity Engineer at Danfoss
- Builds industrial monitoring platforms professionally
- MS Mechatronics, Germany
- International robo wars champion
- Looking for: co-founder + pre-seed funding
- github.com/[repo] | [contact email]

---

## What NOT to Do Tomorrow

- Don't spend morning debating ideas (you have a plan)
- Don't add MQTT (OPC-UA only)
- Don't build auth/login
- Don't write tests
- Don't try real ML (linear regression only)
- Don't make it mobile responsive
- Don't polish CSS before core functionality works
- Don't refactor working code
- Don't add features not in the plan
- Don't miss the 19:00 deadline for ANY reason

---

## Emergency Fallbacks

| Problem | Fallback |
|---------|----------|
| Dashboard not done by 16:00 | Ship robot cards + alarms only, skip predictions panel |
| OPC-UA server won't start | Replay pre-recorded JSON data through WebSocket |
| Chart.js broken | Show raw numbers in HTML table, no charts |
| WebSocket won't connect | Poll REST endpoints every 2 seconds |
| Predictions math wrong | Hardcode "18 days, 83% confidence" for demo |
| WiFi at venue unreliable | Everything runs on localhost, no cloud needed |
| Demo crashes during pitch | Have 3 screenshots ready as static backup |
| Can't find teammate | Go solo, narrow scope to P0 features only |

---

## Required at 19:00 Submission

- [x] Public GitHub repo with README and commit history from June 6
- [x] Pitch deck (max 7 slides)
- [ ] Live demo or hosted preview URL (preferred, not required)

Even if broken, submit what you have. Unfinished beats unsubmitted.

---

## Key Reference Docs

| Doc | Path | Purpose |
|-----|------|---------|
| Build Plan | `docs/superpowers/plans/2026-06-04-robot-health-monitor.md` | Step-by-step tasks with code |
| Spec | `docs/superpowers/specs/2026-06-04-robot-health-monitor-design.md` | Architecture + component details |
| Blueprint | `docs/robolink-blueprint.md` | Market, competition, business model |
| Hackathon Guide | `docs/founder hackathon - ideas & strategy guide.md` | Judging criteria + expectations |

---

*Ship something. Pitch clearly. Show why only you could build this. Go.*
