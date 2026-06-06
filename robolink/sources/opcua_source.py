"""OPC-UA data source connector using asyncua."""

from __future__ import annotations

import asyncio
from datetime import datetime

import structlog
from asyncua import Client, Node
from asyncua.common.subscription import DataChangeNotif

from .base import DataSource, SensorReading

log = structlog.get_logger()


class OPCUASubscriptionHandler:
    """Handle OPC-UA data change notifications."""

    def __init__(self, source: OPCUASource) -> None:
        self._source = source

    def datachange_notification(self, node: Node, val: float, data: DataChangeNotif) -> None:
        """Called by asyncua on every value change."""
        node_id = node.nodeid.to_string()
        reading = SensorReading(
            robot_id=self._source.robot_id_from_node(node_id),
            node_id=node_id,
            value=float(val),
            timestamp=datetime.utcnow(),
        )
        self._source._emit(reading)


class OPCUASource(DataSource):
    """OPC-UA client that subscribes to robot diagnostic nodes."""

    def __init__(
        self,
        source_id: str,
        endpoint: str,
        robot_node_map: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(source_id)
        self._endpoint = endpoint
        self._client: Client | None = None
        self._subscription = None
        self._robot_node_map = robot_node_map or {}
        self._node_to_robot: dict[str, str] = {}
        self._backoff = 1.0

        for robot_id, nodes in self._robot_node_map.items():
            for node_id in nodes:
                self._node_to_robot[node_id] = robot_id

    def robot_id_from_node(self, node_id: str) -> str:
        """Map OPC-UA node ID back to robot ID."""
        return self._node_to_robot.get(node_id, "unknown")

    async def connect(self) -> None:
        """Connect to OPC-UA server with exponential backoff."""
        while True:
            try:
                self._client = Client(url=self._endpoint)
                await self._client.connect()
                self._running = True
                self._backoff = 1.0
                log.info("opcua.connected", endpoint=self._endpoint)
                return
            except Exception as e:
                log.warning("opcua.connect_failed", error=str(e), retry_in=self._backoff)
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, 30.0)

    async def disconnect(self) -> None:
        """Disconnect from OPC-UA server."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._running = False
            log.info("opcua.disconnected", source=self.source_id)

    async def subscribe(self, node_ids: list[str]) -> None:
        """Subscribe to OPC-UA nodes for data change notifications."""
        if not self._client:
            raise RuntimeError("Not connected")

        handler = OPCUASubscriptionHandler(self)
        self._subscription = await self._client.create_subscription(50, handler)
        nodes = [self._client.get_node(nid) for nid in node_ids]
        await self._subscription.subscribe_data_change(nodes)
        log.info("opcua.subscribed", node_count=len(node_ids))

    def __repr__(self) -> str:
        return f"OPCUASource(id={self.source_id}, endpoint={self._endpoint}, running={self._running})"
