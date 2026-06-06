"""Start both OPC-UA sim server and FastAPI backend in one process.

For deployment on Railway/Render/Fly.io where you can't run
multiple processes easily.

Usage: python start.py
"""

from __future__ import annotations

import asyncio
import os
import sys

import uvicorn


async def run_sim_server() -> None:
    """Run OPC-UA simulation server as background task."""
    # Import here to avoid circular imports
    from sim_server import main as sim_main
    try:
        await sim_main()
    except asyncio.CancelledError:
        pass


async def run_api_server() -> None:
    """Run FastAPI server."""
    config = uvicorn.Config(
        "server:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000)),
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    """Start both servers concurrently."""
    print("=" * 50)
    print("RoboLink — Starting all services")
    print("=" * 50)

    sim_task = asyncio.create_task(run_sim_server())

    # Give sim server time to start before API server connects
    await asyncio.sleep(3)

    api_task = asyncio.create_task(run_api_server())

    await asyncio.gather(sim_task, api_task)


if __name__ == "__main__":
    asyncio.run(main())
