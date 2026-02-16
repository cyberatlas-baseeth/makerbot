"""
WebSocket client for StandX market data.

Connects to StandX WebSocket, subscribes to orderbook updates,
feeds snapshots/deltas to the local Orderbook.
Auto-reconnects with exponential backoff.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Coroutine

import websockets
from websockets.exceptions import (
    ConnectionClosed,
    ConnectionClosedError,
    InvalidStatusCode,
)

from app.config import settings
from app.logger import get_logger
from app.market_data.orderbook import Orderbook

log = get_logger("ws_client")


class MarketDataClient:
    """Async WebSocket client for StandX orderbook feed."""

    def __init__(
        self,
        orderbook: Orderbook,
        auth_headers_fn: Callable[[], Coroutine[Any, Any, dict[str, str]]] | None = None,
    ) -> None:
        self._orderbook = orderbook
        self._auth_headers_fn = auth_headers_fn
        self._ws: Any = None
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0

    async def start(self) -> None:
        """Start the WebSocket connection loop."""
        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
        log.info("ws_client.started", symbol=settings.symbol)

    async def stop(self) -> None:
        """Stop the WebSocket connection."""
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("ws_client.stopped")

    async def _connection_loop(self) -> None:
        """Main connection loop with exponential backoff reconnect."""
        while self._running:
            try:
                headers: dict[str, str] = {}
                if self._auth_headers_fn:
                    headers = await self._auth_headers_fn()

                async with websockets.connect(
                    settings.standx_ws_url,
                    additional_headers=headers,
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1.0  # Reset on successful connect
                    log.info("ws_client.connected", url=settings.standx_ws_url)

                    # Subscribe to orderbook channel
                    subscribe_msg = json.dumps({
                        "type": "subscribe",
                        "channel": "orderbook",
                        "symbol": settings.symbol,
                    })
                    await ws.send(subscribe_msg)
                    log.info("ws_client.subscribed", symbol=settings.symbol)

                    # Process messages
                    async for raw_msg in ws:
                        if not self._running:
                            break
                        await self._handle_message(raw_msg)

            except (ConnectionClosed, ConnectionClosedError) as e:
                log.warning("ws_client.disconnected", reason=str(e))
            except InvalidStatusCode as e:
                log.error("ws_client.invalid_status", status=e.status_code)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("ws_client.error", error=str(e))

            if self._running:
                log.info(
                    "ws_client.reconnecting",
                    delay=self._reconnect_delay,
                )
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(
                    self._reconnect_delay * 2.0,
                    self._max_reconnect_delay,
                )

    async def _handle_message(self, raw: str | bytes) -> None:
        """Parse and route incoming WebSocket messages."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("ws_client.invalid_json", raw=str(raw)[:200])
            return

        msg_type = data.get("type", data.get("event", ""))

        if msg_type in ("snapshot", "orderbook_snapshot"):
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            await self._orderbook.update_snapshot(
                bids=[[float(b[0]), float(b[1])] for b in bids],
                asks=[[float(a[0]), float(a[1])] for a in asks],
            )
            log.debug("ws_client.snapshot_applied")

        elif msg_type in ("delta", "update", "orderbook_update"):
            changes = data.get("changes", data.get("updates", []))
            for change in changes:
                side = change.get("side", "bid")
                price = float(change.get("price", 0))
                size = float(change.get("size", change.get("quantity", 0)))
                await self._orderbook.update_delta(side, price, size)

        elif msg_type in ("subscribed", "pong", "heartbeat"):
            pass  # Expected control messages

        else:
            log.debug("ws_client.unknown_message", msg_type=msg_type)
