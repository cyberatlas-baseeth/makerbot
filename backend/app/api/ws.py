"""
WebSocket broadcast endpoint for real-time frontend updates.

Broadcasts engine state snapshot to all connected clients every second.
Includes orderbook data (best bid/ask) in the payload.
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

# References (set from main.py)
_engine = None
_orderbook = None


def set_engine(engine: Any) -> None:
    global _engine
    _engine = engine


def set_orderbook(orderbook: Any) -> None:
    global _orderbook
    _orderbook = orderbook


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

        await asyncio.sleep(2.0)  # Broadcast every 2 seconds
