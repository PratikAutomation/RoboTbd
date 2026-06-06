"""FastAPI backend -- REST API + WebSocket for dashboard.

Connects to OPC-UA sim server, processes data through RoboLink core
(formatter, monitor, alarms, prediction), broadcasts to dashboard.

Usage: uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from robolink.alarms import AlarmEngine
from robolink.formatter import ObservationFormatter
from robolink.monitor import RobotHealthMonitor
from robolink.prediction import PredictionEngine
from robolink.utils.logging import setup_logging

setup_logging("INFO")
log = structlog.get_logger()

# Core components
monitor = RobotHealthMonitor()
alarms = AlarmEngine()
predictions = PredictionEngine()
formatter = ObservationFormatter()

# WebSocket clients
ws_clients: set[WebSocket] = set()

# OPC-UA config
OPCUA_ENDPOINT = "opc.tcp://localhost:4840/robolink/server"
ROBOTS = {
    "Robot1": {"vendor": "ur", "model": "UR10e", "joints": 6},
    "Robot2": {"vendor": "kuka", "model": "KR-16", "joints": 6},
    "Robot3": {"vendor": "abb", "model": "IRB-6700", "joints": 6},
}
METRICS = ["position", "velocity", "torque", "temperature", "current", "vibration"]
# Reverse lookup: numeric node id -> (robot_id, joint_id, metric)
node_id_map: dict[str, tuple[str, int, str]] = {}


async def opcua_reader() -> None:
    """Connect to OPC-UA sim server, browse tree, subscribe to all nodes."""
    from asyncua import Client

    backoff = 1.0
    while True:
        try:
            client = Client(url=OPCUA_ENDPOINT)
            await client.connect()
            log.info("opcua.connected", endpoint=OPCUA_ENDPOINT)
            break
        except Exception as e:
            log.warning("opcua.connect_failed", error=str(e), retry_in=backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30.0)

    # Browse the tree to find all robot/joint/metric nodes
    objects = client.nodes.objects
    all_nodes = []

    for child in await objects.get_children():
        name = (await child.read_browse_name()).Name
        if name not in ROBOTS:
            continue
        robot_id = name

        for joint_obj in await child.get_children():
            jname = (await joint_obj.read_browse_name()).Name
            if not jname.startswith("Joint"):
                continue
            joint_id = int(jname.replace("Joint", ""))

            for var_node in await joint_obj.get_children():
                vname = (await var_node.read_browse_name()).Name
                # vname = "Robot1_Joint1_temperature"
                parts = vname.split("_")
                if len(parts) == 3:
                    metric = parts[2]
                    if metric in METRICS:
                        nid = var_node.nodeid.to_string()
                        node_id_map[nid] = (robot_id, joint_id, metric)
                        all_nodes.append(var_node)

    log.info("opcua.browsed", nodes=len(all_nodes))

    # Subscribe to all discovered nodes
    handler = _OPCUAHandler()
    subscription = await client.create_subscription(50, handler)
    await subscription.subscribe_data_change(all_nodes)
    log.info("opcua.subscribed", nodes=len(all_nodes))

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await client.disconnect()


class _OPCUAHandler:
    """Handle OPC-UA data change notifications."""

    def datachange_notification(self, node, val, data) -> None:
        nid = node.nodeid.to_string()
        parsed = node_id_map.get(nid)
        if not parsed:
            return
        robot_id, joint_id, metric = parsed

        monitor.update_joint(robot_id, joint_id, metric, float(val))
        monitor.update_status(robot_id, "running")

        if metric in ("temperature", "torque", "vibration", "current"):
            alarms.evaluate(robot_id, joint_id, metric, float(val))
            predictions.add_sample(robot_id, joint_id, metric, float(val))


async def ws_broadcaster() -> None:
    """Broadcast state to all WebSocket clients every 500ms."""
    while True:
        if ws_clients:
            payload = json.dumps({
                "type": "update",
                "robots": monitor.to_dict(),
                "alarms": alarms.to_list(),
                "predictions": predictions.to_list(),
                "timestamp": time.time(),
            })
            dead: set[WebSocket] = set()
            for ws in ws_clients:
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.add(ws)
            ws_clients -= dead
        await asyncio.sleep(0.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start OPC-UA reader and WS broadcaster on startup."""
    # Register robots
    for robot_id, config in ROBOTS.items():
        monitor.register_robot(robot_id, config["vendor"], config["model"], config["joints"])

    reader_task = asyncio.create_task(opcua_reader())
    broadcast_task = asyncio.create_task(ws_broadcaster())

    log.info("server.started", robots=list(ROBOTS.keys()))
    yield

    reader_task.cancel()
    broadcast_task.cancel()


app = FastAPI(title="RoboLink API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve dashboard
try:
    app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
except Exception:
    pass  # dashboard dir may not exist yet


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """WebSocket endpoint for real-time dashboard updates."""
    await ws.accept()
    ws_clients.add(ws)
    log.info("ws.connected", total=len(ws_clients))
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        ws_clients.discard(ws)
        log.info("ws.disconnected", total=len(ws_clients))


@app.get("/api/robots")
async def get_robots() -> dict:
    """Get all robot states."""
    return monitor.to_dict()


@app.get("/api/alarms")
async def get_alarms() -> list:
    """Get active alarms."""
    return alarms.to_list()


@app.get("/api/alarms/history")
async def get_alarm_history() -> list:
    """Get alarm history."""
    return alarms.history_list()


@app.get("/api/predictions")
async def get_predictions() -> list:
    """Get failure predictions."""
    return predictions.to_list()


@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "robots": len(ROBOTS), "ws_clients": len(ws_clients)}
