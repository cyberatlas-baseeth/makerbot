"""
Core trading engine.

Main async loop that:
1. Waits for valid mid-price from orderbook
2. Generates two-sided quotes (bid + ask)
3. Cancels stale or out-of-spread orders
4. Places new bid + ask limit orders
5. Updates uptime tracker
6. Sleeps refresh_interval
7. Kill-switch on consecutive API failures
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.logger import get_logger
from app.auth.jwt_auth import auth_manager
from app.market_data.orderbook import Orderbook
from app.trading.quote import Quote, quote_generator
from app.trading.risk import risk_manager
from app.uptime.tracker import uptime_tracker

log = get_logger("engine")


class BotStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    KILLED = "killed"


@dataclass
class ActiveOrder:
    """Tracked order placed by the bot."""
    order_id: str
    side: str              # 'buy' or 'sell'
    price: float
    size: float
    placed_at: float = field(default_factory=time.time)
    status: str = "open"

    def is_stale(self, max_age: float) -> bool:
        return (time.time() - self.placed_at) > max_age

    def deviation_from_mid(self, mid: float) -> float:
        if mid == 0:
            return 0.0
        return abs(self.price - mid) / mid * 10000.0

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "side": self.side,
            "price": round(self.price, 8),
            "size": round(self.size, 8),
            "placed_at": self.placed_at,
            "status": self.status,
            "age_seconds": round(time.time() - self.placed_at, 1),
        }


class TradingEngine:
    """Core market-making engine."""

    def __init__(self, orderbook: Orderbook) -> None:
        self._orderbook = orderbook
        self._status = BotStatus.STARTING
        self._active_orders: dict[str, ActiveOrder] = {}
        self._consecutive_failures = 0
        self._task: asyncio.Task[None] | None = None
        self._last_quote: Quote | None = None
        self._loop_count = 0
        self._client = httpx.AsyncClient(
            base_url=settings.standx_api_url,
            timeout=10.0,
        )

    @property
    def status(self) -> BotStatus:
        return self._status

    @property
    def active_orders(self) -> list[dict]:
        return [o.to_dict() for o in self._active_orders.values() if o.status == "open"]

    @property
    def last_quote(self) -> dict | None:
        return self._last_quote.to_dict() if self._last_quote else None

    async def start(self) -> None:
        """Start the trading engine loop."""
        self._status = BotStatus.RUNNING
        self._task = asyncio.create_task(self._main_loop())
        log.info("engine.started")

    async def stop(self) -> None:
        """Gracefully stop the engine."""
        self._status = BotStatus.PAUSED
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("engine.stopped")

    async def kill(self) -> None:
        """Emergency kill: cancel all orders and stop."""
        log.warning("engine.kill_switch_activated")
        self._status = BotStatus.KILLED
        await self._cancel_all_orders()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("engine.killed")

    def get_full_status(self) -> dict[str, Any]:
        """Return comprehensive engine status."""
        return {
            "status": self._status.value,
            "symbol": settings.symbol,
            "mid_price": self._orderbook.mid_price,
            "market_spread_bps": self._orderbook.spread_bps,
            "configured_spread_bps": settings.spread_bps,
            "order_size": settings.order_size,
            "refresh_interval": settings.refresh_interval,
            "active_orders": self.active_orders,
            "active_order_count": len([o for o in self._active_orders.values() if o.status == "open"]),
            "last_quote": self.last_quote,
            "loop_count": self._loop_count,
            "consecutive_failures": self._consecutive_failures,
            "uptime": uptime_tracker.get_stats(),
            "risk": risk_manager.get_status(),
        }

    async def _main_loop(self) -> None:
        """Primary trading loop."""
        while self._status == BotStatus.RUNNING:
            try:
                await self._tick()
                self._consecutive_failures = 0
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._consecutive_failures += 1
                log.error(
                    "engine.tick_error",
                    error=str(e),
                    consecutive_failures=self._consecutive_failures,
                )

                # Kill-switch: too many consecutive failures
                if self._consecutive_failures >= settings.max_consecutive_failures:
                    log.critical(
                        "engine.kill_switch_triggered",
                        failures=self._consecutive_failures,
                    )
                    self._status = BotStatus.ERROR
                    await self._cancel_all_orders()
                    break

            await asyncio.sleep(settings.refresh_interval)

    async def _tick(self) -> None:
        """Single iteration of the trading loop."""
        self._loop_count += 1

        # 1. Get mid price
        mid = self._orderbook.mid_price
        if mid is None:
            log.debug("engine.no_mid_price")
            uptime_tracker.tick(has_both_sides=False)
            return

        # 2. Generate quotes
        quote = quote_generator.generate(mid)
        self._last_quote = quote

        if not quote.is_within_max_deviation:
            log.warning("engine.quote_exceeds_deviation", quote=quote.to_dict())
            uptime_tracker.tick(has_both_sides=False)
            return

        # 3. Cancel stale or out-of-spread orders
        await self._cancel_stale_orders(mid)

        # 4. Determine what orders we need
        has_bid = any(
            o.side == "buy" and o.status == "open"
            and o.deviation_from_mid(mid) <= settings.max_spread_deviation_bps
            for o in self._active_orders.values()
        )
        has_ask = any(
            o.side == "sell" and o.status == "open"
            and o.deviation_from_mid(mid) <= settings.max_spread_deviation_bps
            for o in self._active_orders.values()
        )

        # 5. Place missing orders
        if not has_bid and risk_manager.check_can_place_order("buy", quote.bid_size, quote.bid_price):
            await self._place_order("buy", quote.bid_price, quote.bid_size)

        if not has_ask and risk_manager.check_can_place_order("sell", quote.ask_size, quote.ask_price):
            await self._place_order("sell", quote.ask_price, quote.ask_size)

        # 6. Update position from exchange
        await self._sync_position(mid)

        # 7. Update uptime - both sides active?
        open_orders = [o for o in self._active_orders.values() if o.status == "open"]
        has_active_bid = any(o.side == "buy" for o in open_orders)
        has_active_ask = any(o.side == "sell" for o in open_orders)
        uptime_tracker.tick(has_both_sides=has_active_bid and has_active_ask)

        log.info(
            "engine.tick",
            loop=self._loop_count,
            mid=round(mid, 4),
            bid=round(quote.bid_price, 4),
            ask=round(quote.ask_price, 4),
            active_orders=len(open_orders),
            uptime_pct=round(uptime_tracker.current_uptime_pct, 2),
        )

    async def _cancel_stale_orders(self, mid: float) -> None:
        """Cancel orders that are stale or drifted too far from mid."""
        to_cancel: list[str] = []
        for oid, order in self._active_orders.items():
            if order.status != "open":
                continue
            if order.is_stale(settings.stale_order_seconds):
                to_cancel.append(oid)
                log.info("engine.cancel_stale", order_id=oid)
            elif order.deviation_from_mid(mid) > settings.max_spread_deviation_bps:
                to_cancel.append(oid)
                log.info("engine.cancel_deviation", order_id=oid, dev=order.deviation_from_mid(mid))

        for oid in to_cancel:
            await self._cancel_order(oid)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=5))
    async def _place_order(self, side: str, price: float, size: float) -> str | None:
        """Place a limit order on StandX."""
        headers = await auth_manager.get_auth_headers()
        payload = {
            "symbol": settings.symbol,
            "side": side,
            "type": "limit",
            "price": str(round(price, 8)),
            "size": str(round(size, 8)),
            "time_in_force": "GTC",
            "post_only": True,
        }

        try:
            resp = await self._client.post(
                "/orders",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            order_id = data.get("order_id", data.get("id", str(uuid.uuid4())))

            self._active_orders[order_id] = ActiveOrder(
                order_id=order_id,
                side=side,
                price=price,
                size=size,
            )
            log.info("engine.order_placed", order_id=order_id, side=side, price=price, size=size)
            return order_id

        except httpx.HTTPStatusError as e:
            log.error("engine.place_order_failed", status=e.response.status_code, body=e.response.text[:200])
            raise
        except Exception as e:
            log.error("engine.place_order_error", error=str(e))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=5))
    async def _cancel_order(self, order_id: str) -> None:
        """Cancel a specific order."""
        try:
            headers = await auth_manager.get_auth_headers()
            resp = await self._client.delete(
                f"/orders/{order_id}",
                headers=headers,
            )
            resp.raise_for_status()
            if order_id in self._active_orders:
                self._active_orders[order_id].status = "cancelled"
            log.info("engine.order_cancelled", order_id=order_id)
        except httpx.HTTPStatusError as e:
            # Order might already be filled/cancelled
            if e.response.status_code == 404:
                if order_id in self._active_orders:
                    self._active_orders[order_id].status = "gone"
                log.info("engine.order_already_gone", order_id=order_id)
            else:
                log.error("engine.cancel_failed", order_id=order_id, status=e.response.status_code)
                raise

    async def _cancel_all_orders(self) -> None:
        """Cancel all open orders (best-effort)."""
        open_orders = [
            oid for oid, o in self._active_orders.items()
            if o.status == "open"
        ]
        for oid in open_orders:
            try:
                await self._cancel_order(oid)
            except Exception as e:
                log.error("engine.cancel_all_error", order_id=oid, error=str(e))

        # Also try bulk cancel via API
        try:
            headers = await auth_manager.get_auth_headers()
            await self._client.delete(
                "/orders",
                params={"symbol": settings.symbol},
                headers=headers,
            )
            log.info("engine.bulk_cancel_sent")
        except Exception as e:
            log.error("engine.bulk_cancel_error", error=str(e))

    async def _sync_position(self, mark_price: float) -> None:
        """Sync position data from exchange."""
        try:
            headers = await auth_manager.get_auth_headers()
            resp = await self._client.get(
                "/positions",
                params={"symbol": settings.symbol},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            # Handle both list and single object responses
            pos_data = data[0] if isinstance(data, list) and data else data if isinstance(data, dict) else {}
            if pos_data:
                risk_manager.update_position(
                    size=float(pos_data.get("size", pos_data.get("quantity", 0))),
                    avg_entry=float(pos_data.get("avg_entry_price", pos_data.get("entry_price", 0))),
                    mark_price=mark_price,
                    unrealized_pnl=float(pos_data.get("unrealized_pnl", 0)),
                    realized_pnl=float(pos_data.get("realized_pnl", 0)),
                )
        except Exception as e:
            log.debug("engine.position_sync_error", error=str(e))

    async def close(self) -> None:
        """Cleanup resources."""
        await self._client.aclose()
