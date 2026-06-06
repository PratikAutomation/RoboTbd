"""OPC-UA simulation server -- 3 robots, 72 nodes, real data replay.

Robot1: UR10e (Universal Robots) -- healthy, normal operation
Robot2: KR-16 (KUKA) -- developing bearing wear on Joint 3
Robot3: IRB-6700 (ABB) -- intermittent anomalies

Usage: python sim_server.py
"""

from __future__ import annotations

import asyncio
import json
import math
import random
import time
from pathlib import Path

from asyncua import Server, ua

# Load real robot data if available
REAL_DATA_DIR = Path("data/processed")
REAL_UR5_DATA: list[dict] = []
REAL_ANOMALY_DATA: list[dict] = []

if (REAL_DATA_DIR / "ur5_joint_data.json").exists():
    with open(REAL_DATA_DIR / "ur5_joint_data.json") as f:
        REAL_UR5_DATA = json.load(f)
    print(f"Loaded {len(REAL_UR5_DATA)} real UR5 frames")

if (REAL_DATA_DIR / "robothon_anomaly_joint_data.json").exists():
    with open(REAL_DATA_DIR / "robothon_anomaly_joint_data.json") as f:
        REAL_ANOMALY_DATA = json.load(f)
    print(f"Loaded {len(REAL_ANOMALY_DATA)} real anomaly frames")

ROBOTS = {
    "Robot1": {"vendor": "ur", "model": "UR10e", "num_joints": 6, "behavior": "healthy"},
    "Robot2": {"vendor": "kuka", "model": "KR-16", "num_joints": 6, "behavior": "degrading"},
    "Robot3": {"vendor": "abb", "model": "IRB-6700", "num_joints": 6, "behavior": "anomaly"},
}

METRICS = ["position", "velocity", "torque", "temperature", "current", "vibration"]


def generate_healthy_value(metric: str, joint: int, t: float, frame_idx: int) -> float:
    """Generate healthy sensor values, using real UR5 data when available."""
    if REAL_UR5_DATA and metric in ("position", "velocity", "torque"):
        frame = REAL_UR5_DATA[frame_idx % len(REAL_UR5_DATA)]
        jdata = frame["joints"].get(f"joint_{joint}")
        if jdata:
            key_map = {"position": "position_rad", "velocity": "velocity_rad_s", "torque": "torque_nm"}
            val = jdata.get(key_map.get(metric, ""), 0.0)
            return val + random.gauss(0, abs(val) * 0.02 + 0.001)

    base_freq = 0.3 + joint * 0.1
    match metric:
        case "position":
            return math.sin(t * base_freq) * 2.5 + random.gauss(0, 0.05)
        case "velocity":
            return math.cos(t * base_freq) * 1.2 + random.gauss(0, 0.03)
        case "torque":
            return 30.0 + math.sin(t * 0.2) * 15.0 + random.gauss(0, 2.0)
        case "temperature":
            return 42.0 + math.sin(t * 0.05) * 3.0 + random.gauss(0, 0.5)
        case "current":
            return 3.0 + math.sin(t * 0.15) * 0.8 + random.gauss(0, 0.1)
        case "vibration":
            return 1.5 + math.sin(t * 0.1) * 0.5 + random.gauss(0, 0.1)
    return 0.0


def generate_degrading_value(metric: str, joint: int, t: float, elapsed: float) -> float:
    """Joint 3 bearing degradation over time."""
    base = generate_healthy_value(metric, joint, t, 0)
    if joint != 3:
        return base
    if elapsed < 30:
        return base

    progress = min(1.0, (elapsed - 30) / 300.0)
    match metric:
        case "temperature":
            return base + progress * 40.0
        case "vibration":
            return base + progress * 6.0
        case "torque":
            return base + progress * 25.0
        case "current":
            return base + progress * 4.0
        case _:
            return base


def generate_anomaly_value(metric: str, joint: int, t: float, frame_idx: int) -> float:
    """Intermittent anomalous behavior with real anomaly data."""
    if REAL_ANOMALY_DATA and metric == "position":
        frame = REAL_ANOMALY_DATA[frame_idx % len(REAL_ANOMALY_DATA)]
        jdata = frame["joints"].get(f"joint_{joint}")
        if jdata:
            raw = jdata.get("position_rad", 0.0)
            return raw * 0.1 + random.gauss(0, 0.02)

    base = generate_healthy_value(metric, joint, t, frame_idx)
    if random.random() < 0.05:
        match metric:
            case "torque":
                return base * random.uniform(1.5, 3.0)
            case "vibration":
                return base + random.uniform(2.0, 5.0)
            case "temperature":
                return base + random.uniform(5.0, 15.0)
            case _:
                return base * (1.0 + random.uniform(-0.5, 0.5))
    return base


async def main() -> None:
    """Run OPC-UA simulation server."""
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/robolink/server")
    server.set_server_name("RoboLink Simulation Server")

    uri = "urn:robolink:sim"
    idx = await server.register_namespace(uri)
    objects = server.nodes.objects

    robot_nodes: dict[str, dict[int, dict[str, any]]] = {}

    for robot_id, config in ROBOTS.items():
        robot_obj = await objects.add_object(idx, robot_id)
        robot_nodes[robot_id] = {}
        await robot_obj.add_variable(idx, f"{robot_id}_status", "running")
        await robot_obj.add_variable(idx, f"{robot_id}_vendor", config["vendor"])
        await robot_obj.add_variable(idx, f"{robot_id}_model", config["model"])

        for j in range(1, config["num_joints"] + 1):
            joint_obj = await robot_obj.add_object(idx, f"Joint{j}")
            robot_nodes[robot_id][j] = {}
            for metric in METRICS:
                var = await joint_obj.add_variable(idx, f"{robot_id}_Joint{j}_{metric}", 0.0)
                await var.set_writable()
                robot_nodes[robot_id][j][metric] = var

    total_nodes = sum(c["num_joints"] for c in ROBOTS.values()) * len(METRICS)
    print(f"OPC-UA server: opc.tcp://0.0.0.0:4840 | {len(ROBOTS)} robots | {total_nodes} nodes")

    async with server:
        start_time = time.time()
        frame_idx = 0
        while True:
            t = time.time()
            elapsed = t - start_time

            for robot_id, config in ROBOTS.items():
                for j in range(1, config["num_joints"] + 1):
                    for metric in METRICS:
                        match config["behavior"]:
                            case "healthy":
                                val = generate_healthy_value(metric, j, t, frame_idx)
                            case "degrading":
                                val = generate_degrading_value(metric, j, t, elapsed)
                            case "anomaly":
                                val = generate_anomaly_value(metric, j, t, frame_idx)
                            case _:
                                val = 0.0
                        await robot_nodes[robot_id][j][metric].write_value(float(val))

            frame_idx += 1
            await asyncio.sleep(0.1)


if __name__ == "__main__":
    print("=" * 50)
    print("RoboLink OPC-UA Simulation Server")
    print("=" * 50)
    asyncio.run(main())
