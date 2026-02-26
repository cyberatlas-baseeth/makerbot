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

from app.config import settings, QTY_TICKS, PRICE_TICKS
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
        self._open_position: dict | None = None  # {side, qty, entry_price}
        self._closed_positions: list[dict] = []    # recent auto-closed positions
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
            self._last_quote = None
            self._consecutive_failures = 0
            self._loop_count = 0
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
            "requote_threshold_bps": settings.requote_threshold_bps,
            "bid_spread_bps": quote_dict.get("bid_spread_bps", settings.spread_bps),
            "ask_spread_bps": quote_dict.get("ask_spread_bps", settings.spread_bps),
            "refresh_interval": settings.refresh_interval,
            "tp_bps": settings.tp_bps,
            "sl_bps": settings.sl_bps,
            "auto_close_fills": settings.auto_close_fills,
            "open_position": self._open_position,
            "closed_positions": self._closed_positions[-20:],
            "active_orders": self.active_orders,
            "active_order_count": len([o for o in self._active_orders.values() if o.status == "open"]),
            "last_quote": self.last_quote,
            "loop_count": self._loop_count,
            "consecutive_failures": self._consecutive_failures,
            "uptime": uptime_stats,
            "uptime_percentage": uptime_stats.get("current_hour", {}).get("maker_uptime_pct", 0),
            "mm_uptime_percentage": uptime_stats.get("current_hour", {}).get("mm_uptime_pct", 0),
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

        # 0. Check and close any open positions from partial fills
        if settings.auto_close_fills:
            await self._check_and_close_positions()

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

        # 3. Check if existing orders need refreshing
        open_bids = {oid: o for oid, o in self._active_orders.items()
                     if o.side == "buy" and o.status == "open"}
        open_asks = {oid: o for oid, o in self._active_orders.items()
                     if o.side == "sell" and o.status == "open"}

        need_refresh = False

        # Check bid side
        for oid, order in open_bids.items():
            proximity_hit = (best_bid is not None and
                             order.price >= best_bid - (mid * settings.proximity_guard_bps / 10000.0))
            drift_bps = abs(order.price - quote.bid_price) / mid * 10000.0

            if proximity_hit:
                log.info("engine.proximity_guard_bid", order_id=oid,
                         order_price=order.price, best_bid=best_bid)
                need_refresh = True
            elif drift_bps >= settings.requote_threshold_bps:
                log.info("engine.requote_bid", order_id=oid, drift_bps=round(drift_bps, 2))
                need_refresh = True
            elif order.is_stale(settings.stale_order_seconds):
                log.info("engine.cancel_stale_bid", order_id=oid)
                need_refresh = True

        # Check ask side
        for oid, order in open_asks.items():
            proximity_hit = (best_ask is not None and
                             order.price <= best_ask + (mid * settings.proximity_guard_bps / 10000.0))
            drift_bps = abs(order.price - quote.ask_price) / mid * 10000.0

            if proximity_hit:
                log.info("engine.proximity_guard_ask", order_id=oid,
                         order_price=order.price, best_ask=best_ask)
                need_refresh = True
            elif drift_bps >= settings.requote_threshold_bps:
                log.info("engine.requote_ask", order_id=oid, drift_bps=round(drift_bps, 2))
                need_refresh = True
            elif order.is_stale(settings.stale_order_seconds):
                log.info("engine.cancel_stale_ask", order_id=oid)
                need_refresh = True

        # 4. If refresh needed or no orders exist, cancel all and place new
        has_both_sides = bool(open_bids) and bool(open_asks)

        if need_refresh or not has_both_sides:
            if open_bids or open_asks:
                # Cancel all existing orders on exchange
                await self._cancel_all_orders()

            # Place fresh orders
            await self._place_order("buy", quote.bid_price, quote.bid_size)
            await self._place_order("sell", quote.ask_price, quote.ask_size)

        # 5. Update uptime — both sides active?
        open_orders = [o for o in self._active_orders.values() if o.status == "open"]
        has_active_bid = any(o.side == "buy" for o in open_orders)
        has_active_ask = any(o.side == "sell" for o in open_orders)
        uptime_tracker.tick(
            has_both_sides=has_active_bid and has_active_ask,
            spread_bps=settings.spread_bps,
        )

        log.info(
            "engine.tick",
            loop=self._loop_count,
            mid=round(mid, 4),
            bid=round(quote.bid_price, 4),
            ask=round(quote.ask_price, 4),
            bid_spread=round(quote.bid_spread_bps, 2),
            ask_spread=round(quote.ask_spread_bps, 2),
            active_orders=len(open_orders),
            maker_uptime_pct=round(uptime_tracker.current_maker_uptime_pct, 2),
            mm_uptime_pct=round(uptime_tracker.current_mm_uptime_pct, 2),
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
            # Notional too small — use minimum qty (1 tick) to keep uptime
            floored_qty = tick
            log.info(
                "engine.qty_bumped_to_min",
                side=side,
                raw_size=round(size, 8),
                min_tick=tick,
                symbol=settings.symbol,
            )

        # Round price to symbol's price tick
        price_tick = PRICE_TICKS.get(settings.symbol, 0.01)
        price_decimals = max(0, -int(math.log10(price_tick)))
        if side == "buy":
            # Bid: floor to tick (lower = safer for buyer)
            rounded_price = math.floor(price / price_tick) * price_tick
        else:
            # Ask: ceil to tick (higher = safer for seller)
            rounded_price = math.ceil(price / price_tick) * price_tick
        rounded_price = round(rounded_price, price_decimals)

        payload = {
            "symbol": settings.symbol,
            "side": side,
            "order_type": "limit",
            "qty": str(floored_qty),
            "price": str(rounded_price),
            "time_in_force": "gtc",
            "reduce_only": False,
        }

        # TP/SL — compute absolute prices from bps (0 = disabled)
        if settings.tp_bps > 0:
            if side == "buy":
                tp_price = rounded_price * (1 + settings.tp_bps / 10000.0)
            else:
                tp_price = rounded_price * (1 - settings.tp_bps / 10000.0)
            tp_price = round(tp_price, price_decimals)
            payload["tp_price"] = str(tp_price)

        if settings.sl_bps > 0:
            if side == "buy":
                sl_price = rounded_price * (1 - settings.sl_bps / 10000.0)
            else:
                sl_price = rounded_price * (1 + settings.sl_bps / 10000.0)
            sl_price = round(sl_price, price_decimals)
            payload["sl_price"] = str(sl_price)
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

    async def _cancel_order_by_id(self, exchange_order_id: int) -> bool:
        """Cancel a single order on the exchange using its integer ID."""
        try:
            payload = json.dumps({"order_id": exchange_order_id})
            headers = await auth_manager.get_full_headers(payload)
            headers["Content-Type"] = "application/json"
            resp = await self._client.post(
                "/api/cancel_order",
                content=payload,
                headers=headers,
            )
            resp.raise_for_status()
            log.info("engine.order_cancelled", exchange_id=exchange_order_id)
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (404, 422):
                # 404 = not found, 422 = already filled/cancelled — both mean "gone"
                log.info("engine.order_already_gone",
                         exchange_id=exchange_order_id,
                         status=e.response.status_code)
                return True
            log.error("engine.cancel_failed",
                      exchange_id=exchange_order_id,
                      status=e.response.status_code,
                      body=e.response.text[:200])
            return False
        except Exception as e:
            log.error("engine.cancel_error", exchange_id=exchange_order_id, error=str(e))
            return False

    async def _cancel_all_orders(self) -> None:
        """Cancel all open orders on the exchange, then clear internal state.
        
        Queries the exchange for actual open orders and cancels each
        using the integer order ID from the exchange.
        Never raises — cancel failures are logged but do not propagate.
        """
        cancelled = 0
        failed = 0

        try:
            # 1. Query exchange for real open orders
            try:
                headers = await auth_manager.get_full_headers("")
                resp = await self._client.get(
                    "/api/query_open_orders",
                    params={"symbol": settings.symbol},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                exchange_orders = data.get("result", [])
                log.info("engine.fetched_open_orders", count=len(exchange_orders))
            except Exception as e:
                log.error("engine.fetch_open_orders_failed", error=str(e))
                exchange_orders = []

            # 2. Cancel each order using integer ID
            for order in exchange_orders:
                exchange_id = order.get("id")
                if exchange_id is not None:
                    ok = await self._cancel_order_by_id(exchange_id)
                    if ok:
                        cancelled += 1
                    else:
                        failed += 1

            log.info("engine.cancel_all_done", cancelled=cancelled, failed=failed)
        except Exception as e:
            log.error("engine.cancel_all_error", error=str(e))

        # 3. Always clear internal order tracking, even if cancels failed
        self._active_orders.clear()
        log.info("engine.orders_cleared")

    # ─── Position Management ───────────────────────────────────────

    async def _check_and_close_positions(self) -> None:
        """Query open positions and close them with reduce_only market orders."""
        try:
            headers = await auth_manager.get_full_headers("")
            resp = await self._client.get(
                "/api/query_positions",
                params={"symbol": settings.symbol},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            positions = data.get("result", [])

            # Find non-zero position for our symbol
            active_pos = None
            for pos in positions:
                qty = float(pos.get("qty", 0))
                if pos.get("symbol") == settings.symbol and qty != 0:
                    active_pos = pos
                    break

            if active_pos is None:
                self._open_position = None
                return

            qty = float(active_pos.get("qty", 0))
            entry_price = float(active_pos.get("entry_price", 0))
            pos_side = "long" if qty > 0 else "short"

            self._open_position = {
                "side": pos_side,
                "qty": abs(qty),
                "entry_price": entry_price,
            }

            log.warning(
                "engine.position_detected",
                side=pos_side,
                qty=abs(qty),
                entry_price=entry_price,
            )

            # Close: sell to close long, buy to close short
            close_side = "sell" if qty > 0 else "buy"
            await self._place_market_close(close_side, abs(qty))

        except Exception as e:
            log.error("engine.position_check_error", error=str(e))

    async def _place_market_close(self, side: str, qty: float) -> None:
        """Place a reduce_only market order to close a position."""
        # Round qty to symbol's tick size
        tick = QTY_TICKS.get(settings.symbol, 0.0001)
        decimals = max(0, -int(math.log10(tick)))
        rounded_qty = round(qty, decimals)

        if rounded_qty < tick:
            log.info("engine.position_too_small", qty=qty, tick=tick)
            self._open_position = None
            return

        payload = {
            "symbol": settings.symbol,
            "side": side,
            "order_type": "market",
            "qty": str(rounded_qty),
            "time_in_force": "ioc",
            "reduce_only": True,
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
            order_id = data.get("order_id", data.get("id", "unknown"))
            log.info(
                "engine.position_closed",
                order_id=order_id,
                side=side,
                qty=rounded_qty,
            )
            # Record in closed positions history
            if self._open_position:
                self._closed_positions.append({
                    "side": self._open_position["side"],
                    "qty": self._open_position["qty"],
                    "entry_price": self._open_position["entry_price"],
                    "close_side": side,
                    "close_qty": rounded_qty,
                    "closed_at": time.time(),
                })
                # Keep only last 50
                if len(self._closed_positions) > 50:
                    self._closed_positions = self._closed_positions[-50:]
            self._open_position = None
        except httpx.HTTPStatusError as e:
            log.error(
                "engine.position_close_failed",
                status=e.response.status_code,
                body=e.response.text[:200],
            )
        except Exception as e:
            log.error("engine.position_close_error", error=str(e))

    async def close(self) -> None:
        """Cleanup resources."""
        await self._client.aclose()
