"""
WebSocket broadcast endpoint for real-time frontend updates.

Broadcasts engine state snapshot to all connected clients every second.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.logger import get_logger

log = get_logger("ws_broadcast")

router = APIRouter()

# Connected frontend clients
_clients: set[WebSocket] = set()

# Reference to engine (set from main.py)
_engine = None


def set_engine(engine: Any) -> None:
    global _engine
    _engine = engine


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Accept frontend WebSocket connections."""
    await ws.accept()
    _clients.add(ws)
    log.info("ws.client_connected", total=len(_clients))

    try:
        while True:
            # Keep connection alive; ignore incoming messages
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send ping to keep alive
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.debug("ws.client_error", error=str(e))
    finally:
        _clients.discard(ws)
        log.info("ws.client_disconnected", total=len(_clients))


async def broadcast_loop() -> None:
    """Background task that broadcasts state to all connected clients."""
    while True:
        if _engine and _clients:
            try:
                state = _engine.get_full_status()
                state["type"] = "state_update"
                message = json.dumps(state, default=str)

                disconnected: set[WebSocket] = set()
                for client in _clients.copy():
                    try:
                        await client.send_text(message)
                    except Exception:
                        disconnected.add(client)

                for client in disconnected:
                    _clients.discard(client)

            except Exception as e:
                log.error("ws.broadcast_error", error=str(e))

        await asyncio.sleep(1.0)
