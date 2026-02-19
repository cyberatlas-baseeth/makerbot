"""
Core trading engine — persistent maker for uptime optimization.

Main loop:
1. Get mid price from orderbook
2. Generate symmetric quote
3. Proximity guard: refresh orders when within 1bps of being hit
4. Drift check: replace only when mid moves beyond threshold
5. Keep orders alive on the book otherwise
"""

from __future__ import annotations

import asyncio
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from app.config import settings, QTY_TICKS
from app.logger import get_logger
from app.auth.jwt_auth import auth_manager
from app.market_data.orderbook import Orderbook
from app.trading.quote import Quote, quote_generator
from app.uptime.tracker import uptime_tracker

log = get_logger("engine")


class BotStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
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

    def drift_from_target(self, target_price: float, mid: float) -> float:
        """How far this order's price is from the new target, in bps."""
        if mid == 0:
            return 0.0
        return abs(self.price - target_price) / mid * 10000.0

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
    """Core market-making engine for uptime optimization."""

    def __init__(self, orderbook: Orderbook) -> None:
        self._orderbook = orderbook
        self._status = BotStatus.STOPPED
        self._active_orders: dict[str, ActiveOrder] = {}
        self._consecutive_failures = 0
        self._task: asyncio.Task[None] | None = None
        self._last_quote: Quote | None = None
        self._loop_count = 0
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            base_url=settings.standx_api_base,
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
        async with self._lock:
            if self._status == BotStatus.RUNNING:
                log.warning("engine.already_running")
                return
            self._status = BotStatus.RUNNING
            self._consecutive_failures = 0
            self._task = asyncio.create_task(self._main_loop())
            log.info("engine.started")

    async def stop(self) -> None:
        """Gracefully stop the engine and cancel all orders."""
        async with self._lock:
            if self._status == BotStatus.STOPPED:
                log.warning("engine.already_stopped")
                return
            self._status = BotStatus.STOPPED
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            await self._cancel_all_orders()
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
        uptime_stats = uptime_tracker.get_stats()
        quote_dict = self.last_quote or {}
        return {
            "status": self._status.value,
            "symbol": settings.symbol,
            "mid_price": self._orderbook.mid_price,
            "best_bid": self._orderbook.best_bid,
            "best_ask": self._orderbook.best_ask,
            "market_spread_bps": self._orderbook.spread_bps,
            "configured_spread_bps": settings.spread_bps,
            "bid_notional": settings.bid_notional,
            "ask_notional": settings.ask_notional,
            "requote_threshold_usd": settings.requote_threshold_usd,
            "bid_spread_bps": quote_dict.get("bid_spread_bps", 0.0),
            "ask_spread_bps": quote_dict.get("ask_spread_bps", 0.0),
            "refresh_interval": settings.refresh_interval,
            "active_orders": self.active_orders,
            "active_order_count": len([o for o in self._active_orders.values() if o.status == "open"]),
            "last_quote": self.last_quote,
            "loop_count": self._loop_count,
            "consecutive_failures": self._consecutive_failures,
            "uptime": uptime_stats,
            "uptime_percentage": uptime_stats.get("current_hour", {}).get("uptime_pct", 0),
        }

    # ─── Main Loop ────────────────────────────────────────────────

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

        best_bid = self._orderbook.best_bid
        best_ask = self._orderbook.best_ask

        # 2. Generate symmetric quote
        quote = quote_generator.generate(mid_price=mid)
        self._last_quote = quote

        if not quote.is_within_max_deviation:
            log.warning("engine.quote_exceeds_deviation", quote=quote.to_dict())
            uptime_tracker.tick(has_both_sides=False)
            return

        # 3. Manage existing orders — proximity guard + drift check
        open_bids = {oid: o for oid, o in self._active_orders.items()
                     if o.side == "buy" and o.status == "open"}
        open_asks = {oid: o for oid, o in self._active_orders.items()
                     if o.side == "sell" and o.status == "open"}

        # Handle bid side
        need_new_bid = True
        for oid, order in open_bids.items():
            proximity_hit = (best_bid is not None and
                             order.price >= best_bid - (mid * settings.proximity_guard_bps / 10000.0))
            drift_usd = abs(order.price - quote.bid_price)

            if proximity_hit:
                log.info("engine.proximity_guard_bid", order_id=oid,
                         order_price=order.price, best_bid=best_bid)
                await self._cancel_order(oid)
            elif drift_usd >= settings.requote_threshold_usd:
                log.info("engine.requote_bid", order_id=oid, drift_usd=round(drift_usd, 2))
                await self._cancel_order(oid)
            elif order.is_stale(settings.stale_order_seconds):
                log.info("engine.cancel_stale_bid", order_id=oid)
                await self._cancel_order(oid)
            else:
                need_new_bid = False  # Existing order is fine, keep it

        # Handle ask side
        need_new_ask = True
        for oid, order in open_asks.items():
            proximity_hit = (best_ask is not None and
                             order.price <= best_ask + (mid * settings.proximity_guard_bps / 10000.0))
            drift_usd = abs(order.price - quote.ask_price)

            if proximity_hit:
                log.info("engine.proximity_guard_ask", order_id=oid,
                         order_price=order.price, best_ask=best_ask)
                await self._cancel_order(oid)
            elif drift_usd >= settings.requote_threshold_usd:
                log.info("engine.requote_ask", order_id=oid, drift_usd=round(drift_usd, 2))
                await self._cancel_order(oid)
            elif order.is_stale(settings.stale_order_seconds):
                log.info("engine.cancel_stale_ask", order_id=oid)
                await self._cancel_order(oid)
            else:
                need_new_ask = False  # Existing order is fine, keep it

        # 4. Place new orders where needed
        if need_new_bid:
            await self._place_order("buy", quote.bid_price, quote.bid_size)

        if need_new_ask:
            await self._place_order("sell", quote.ask_price, quote.ask_size)

        # 5. Update uptime — both sides active?
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
            bid_spread=round(quote.bid_spread_bps, 2),
            ask_spread=round(quote.ask_spread_bps, 2),
            active_orders=len(open_orders),
            uptime_pct=round(uptime_tracker.current_uptime_pct, 2),
        )

    # ─── Order Management ─────────────────────────────────────────

    async def _place_order(self, side: str, price: float, size: float) -> str | None:
        """Place a limit order on StandX.

        Returns order_id on success, None if skipped or soft-failed.
        Only raises on transient errors (network, 5xx) — NOT on 400 qty errors.
        """
        # Round qty to symbol's tick size
        tick = QTY_TICKS.get(settings.symbol, 0.0001)
        floored_qty = math.floor(size / tick) * tick
        # Round to avoid floating point artifacts
        decimals = max(0, -int(math.log10(tick)))
        floored_qty = round(floored_qty, decimals)

        if floored_qty < tick:
            # Notional too small for this symbol — skip gracefully
            log.warning(
                "engine.qty_too_small",
                side=side,
                raw_size=round(size, 8),
                min_tick=tick,
                symbol=settings.symbol,
                hint=f"Increase bid/ask notional. Min order: {tick} * ${price:.0f} = ${tick * price:.2f}",
            )
            return None

        payload = {
            "symbol": settings.symbol,
            "side": side,
            "order_type": "limit",
            "qty": str(floored_qty),
            "price": str(round(price, 2)),
            "time_in_force": "gtc",
            "reduce_only": False,
        }
        payload_str = json.dumps(payload)
        headers = await auth_manager.get_full_headers(payload_str)
        headers["Content-Type"] = "application/json"

        try:
            resp = await self._client.post(
                "/api/new_order",
                content=payload_str,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            order_id = data.get("order_id", data.get("id", str(uuid.uuid4())))

            self._active_orders[order_id] = ActiveOrder(
                order_id=order_id,
                side=side,
                price=price,
                size=floored_qty,
            )
            log.info("engine.order_placed", order_id=order_id, side=side,
                     price=round(price, 2), size=floored_qty)
            return order_id

        except httpx.HTTPStatusError as e:
            body = e.response.text[:200]
            if e.response.status_code == 400 and "qty" in body.lower():
                # Qty tick error from exchange — don't retry, don't crash
                log.warning("engine.qty_rejected_by_exchange",
                            side=side, qty=floored_qty, body=body)
                return None
            log.error("engine.place_order_failed",
                      status=e.response.status_code, body=body)
            raise
        except Exception as e:
            log.error("engine.place_order_error", error=str(e))
            raise

    async def _cancel_order(self, order_id: str) -> None:
        """Cancel a specific order."""
        try:
            payload = json.dumps({"order_id": order_id})
            headers = await auth_manager.get_full_headers(payload)
            headers["Content-Type"] = "application/json"
            resp = await self._client.post(
                "/api/cancel_order",
                content=payload,
                headers=headers,
            )
            resp.raise_for_status()
            if order_id in self._active_orders:
                self._active_orders[order_id].status = "cancelled"
            log.info("engine.order_cancelled", order_id=order_id)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                if order_id in self._active_orders:
                    self._active_orders[order_id].status = "gone"
                log.info("engine.order_already_gone", order_id=order_id)
            else:
                log.error("engine.cancel_failed",
                          order_id=order_id, status=e.response.status_code)
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

        # Bulk cancel via API
        try:
            payload = json.dumps({"symbol": settings.symbol})
            headers = await auth_manager.get_full_headers(payload)
            headers["Content-Type"] = "application/json"
            await self._client.post(
                "/api/cancel_all_orders",
                content=payload,
                headers=headers,
            )
            log.info("engine.bulk_cancel_sent")
        except Exception as e:
            log.error("engine.bulk_cancel_error", error=str(e))

    async def close(self) -> None:
        """Cleanup resources."""
        await self._client.aclose()
