"""
WebSocket client for StandX market data.

Connects to StandX WebSocket (wss://perps.standx.com/ws-stream/v1),
subscribes to depth_book channel, feeds snapshots to local Orderbook.
Auto-reconnects with exponential backoff.

Protocol reference: https://docs.standx.com/standx-api/perps-ws
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
    """Async WebSocket client for StandX depth_book feed."""

    def __init__(
        self,
        orderbook: Orderbook,
    ) -> None:
        self._orderbook = orderbook
        self._ws: Any = None
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0

    async def start(self) -> None:
        """Start the WebSocket connection loop."""
        self._running = True
        self._task = asyncio.create_task(self._connection_loop())
        log.info("ws_client.started", symbol=settings.symbol, url=settings.standx_ws_url)

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

    async def switch_symbol(self, new_symbol: str) -> None:
        """Switch to a new symbol: unsubscribe old, clear orderbook, subscribe new."""
        old_symbol = self._orderbook.symbol

        # Unsubscribe from old symbol
        if self._ws:
            try:
                unsub = json.dumps({
                    "unsubscribe": {
                        "channel": "depth_book",
                        "symbol": old_symbol,
                    }
                })
                await self._ws.send(unsub)
                log.info("ws_client.unsubscribed", symbol=old_symbol)
            except Exception as e:
                log.warning("ws_client.unsubscribe_failed", error=str(e))

        # Clear orderbook and update symbol
        await self._orderbook.reset(new_symbol=new_symbol)

        # Subscribe to new symbol
        if self._ws:
            try:
                sub = json.dumps({
                    "subscribe": {
                        "channel": "depth_book",
                        "symbol": new_symbol,
                    }
                })
                await self._ws.send(sub)
                log.info("ws_client.subscribed", symbol=new_symbol)
            except Exception as e:
                log.warning("ws_client.subscribe_failed", error=str(e))

    async def _connection_loop(self) -> None:
        """Main connection loop with exponential backoff reconnect."""
        while self._running:
            try:
                async with websockets.connect(
                    settings.standx_ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1.0  # Reset on successful connect
                    log.info("ws_client.connected", url=settings.standx_ws_url)

                    # Authenticate on WS if token available
                    if settings.standx_jwt_token:
                        auth_msg = json.dumps({
                            "auth": {
                                "token": settings.standx_jwt_token,
                                "streams": [
                                    {"channel": "order"},
                                    {"channel": "position"},
                                    {"channel": "balance"},
                                ],
                            }
                        })
                        await ws.send(auth_msg)
                        log.info("ws_client.auth_sent")

                    # Subscribe to depth_book channel
                    subscribe_msg = json.dumps({
                        "subscribe": {
                            "channel": "depth_book",
                            "symbol": self._orderbook.symbol,
                        }
                    })
                    await ws.send(subscribe_msg)
                    log.info("ws_client.subscribed", symbol=self._orderbook.symbol)

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

        channel = data.get("channel", "")

        # depth_book channel — full orderbook snapshot on each message
        if channel == "depth_book":
            book_data = data.get("data", {})
            bids_raw = book_data.get("bids", [])
            asks_raw = book_data.get("asks", [])

            # StandX sends string pairs: ["price", "size"]
            bids = [[float(b[0]), float(b[1])] for b in bids_raw]
            asks = [[float(a[0]), float(a[1])] for a in asks_raw]

            await self._orderbook.update_snapshot(bids=bids, asks=asks)
            log.debug(
                "ws_client.depth_book",
                symbol=book_data.get("symbol", ""),
                bids=len(bids),
                asks=len(asks),
            )

        # price channel
        elif channel == "price":
            price_data = data.get("data", {})
            log.debug("ws_client.price_update", symbol=price_data.get("symbol"),
                      mid=price_data.get("mid_price"))

        # auth response
        elif channel == "auth":
            auth_data = data.get("data", {})
            code = auth_data.get("code", -1)
            msg = auth_data.get("msg", "")
            if code in (0, 200):
                log.info("ws_client.auth_success")
            else:
                log.error("ws_client.auth_failed", code=code, msg=msg)

        # order/position/balance (authenticated user channels)
        elif channel in ("order", "position", "balance", "trade"):
            log.debug("ws_client.user_channel", channel=channel,
                      data=str(data.get("data", {}))[:200])

        # Ignore ping/pong/subscribe confirmations
        elif data.get("code") or data.get("type") in ("pong", "heartbeat"):
            pass

        else:
            log.debug("ws_client.unknown_message", data=str(data)[:200])
