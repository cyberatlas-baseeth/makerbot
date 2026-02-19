"""
REST API routes for the market maker bot.

Endpoints:
  POST /start       – Start the trading engine
  POST /stop        – Stop the trading engine
  GET  /status      – Bot status, mid-price, spread
  GET  /orders      – Active orders list
  GET  /uptime      – Uptime stats (current hour + history)
  POST /config      – Update symbol, spread_bps, bid/ask notional, refresh_interval
  POST /kill        – Emergency kill-switch
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings, update_runtime_settings, SUPPORTED_SYMBOLS
from app.logger import get_logger
from app.auth.jwt_auth import auth_manager

log = get_logger("api")

router = APIRouter()

# These will be set by main.py after engine initialization
_engine = None
_orderbook = None
_market_data_client = None
_config_lock = asyncio.Lock()


def set_engine(engine: Any) -> None:
    global _engine
    _engine = engine


def set_orderbook(orderbook: Any) -> None:
    global _orderbook
    _orderbook = orderbook


def set_market_data_client(client: Any) -> None:
    global _market_data_client
    _market_data_client = client


# --- Models ---

class ConfigUpdate(BaseModel):
    symbol: Optional[str] = None
    spread_bps: Optional[float] = None
    bid_notional: Optional[float] = None
    ask_notional: Optional[float] = None
    requote_threshold_bps: Optional[float] = None
    refresh_interval: Optional[float] = None


# --- Start / Stop ---

@router.post("/start")
async def start_bot() -> dict[str, Any]:
    """Start the trading engine."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    if not auth_manager.is_authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated — set STANDX_JWT_TOKEN in .env")

    from app.trading.engine import BotStatus
    if _engine.status == BotStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Engine already running")

    await _engine.start()
    log.info("api.engine_started")
    return {
        "message": "Engine started",
        "status": _engine.status.value,
    }


@router.post("/stop")
async def stop_bot() -> dict[str, Any]:
    """Stop the trading engine and cancel all orders."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    from app.trading.engine import BotStatus
    if _engine.status == BotStatus.STOPPED:
        raise HTTPException(status_code=409, detail="Engine already stopped")

    await _engine.stop()
    log.info("api.engine_stopped")
    return {
        "message": "Engine stopped — all orders cancelled",
        "status": _engine.status.value,
    }


# --- Status Endpoints ---

@router.get("/status")
async def get_status() -> dict[str, Any]:
    """Get comprehensive bot status."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    status = _engine.get_full_status()
    status["authenticated"] = auth_manager.is_authenticated
    status["wallet_address"] = auth_manager.wallet_address
    status["supported_symbols"] = SUPPORTED_SYMBOLS
    return status


@router.get("/orders")
async def get_orders() -> dict[str, Any]:
    """Get active orders."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    return {
        "orders": _engine.active_orders,
        "count": len(_engine.active_orders),
    }


@router.get("/uptime")
async def get_uptime() -> dict[str, Any]:
    """Get uptime statistics."""
    from app.uptime.tracker import uptime_tracker
    return uptime_tracker.get_stats()


# --- Config ---

@router.post("/config")
async def update_config(config: ConfigUpdate) -> dict[str, Any]:
    """
    Update runtime configuration.

    If symbol changes: stop engine → cancel orders → reset uptime → switch WS → restart.
    If only spread/size changes: update immediately.
    """
    async with _config_lock:
        symbol_changed = config.symbol is not None and config.symbol != settings.symbol

        if symbol_changed:
            # Validate symbol
            if config.symbol not in SUPPORTED_SYMBOLS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported symbol: {config.symbol}. Must be one of {SUPPORTED_SYMBOLS}",
                )

            from app.trading.engine import BotStatus
            was_running = _engine is not None and _engine.status == BotStatus.RUNNING

            # 1. Stop engine if running
            if was_running and _engine is not None:
                await _engine.stop()

            # 2. Reset uptime
            from app.uptime.tracker import uptime_tracker
            uptime_tracker.reset()

            # 3. Switch WS subscription
            if _market_data_client is not None:
                await _market_data_client.switch_symbol(config.symbol)

            # 4. Update config
            updates = update_runtime_settings(
                symbol=config.symbol,
                spread_bps=config.spread_bps,
                bid_notional=config.bid_notional,
                ask_notional=config.ask_notional,
                requote_threshold_bps=config.requote_threshold_bps,
                refresh_interval=config.refresh_interval,
            )

            # 5. Restart engine if it was running
            if was_running and _engine is not None:
                await asyncio.sleep(1.0)  # Brief pause for new orderbook data
                await _engine.start()

            log.info("api.symbol_switched", updates=updates)

        else:
            # No symbol change — just update params
            updates = update_runtime_settings(
                spread_bps=config.spread_bps,
                bid_notional=config.bid_notional,
                ask_notional=config.ask_notional,
                requote_threshold_bps=config.requote_threshold_bps,
                refresh_interval=config.refresh_interval,
            )
            if not updates:
                raise HTTPException(status_code=400, detail="No valid fields to update")
            log.info("api.config_updated", updates=updates)

    return {
        "message": "Configuration updated" + (" (symbol switched)" if symbol_changed else ""),
        "updated_fields": updates,
        "current_config": {
            "symbol": settings.symbol,
            "spread_bps": settings.spread_bps,
            "bid_notional": settings.bid_notional,
            "ask_notional": settings.ask_notional,
            "requote_threshold_bps": settings.requote_threshold_bps,
            "refresh_interval": settings.refresh_interval,
        },
    }
