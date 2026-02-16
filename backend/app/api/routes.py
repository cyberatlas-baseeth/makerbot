"""
REST API routes for the market maker bot.

Endpoints:
  POST /auth/start  – Receive JWT token from frontend MetaMask login
  GET  /status      – Bot status, mid-price, spread
  GET  /orders      – Active orders list
  GET  /uptime      – Uptime stats (current hour + history)
  GET  /positions   – Current position & PnL
  POST /config      – Update spread_bps, order_size, refresh_interval
  POST /kill        – Emergency kill-switch
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings, update_runtime_settings
from app.logger import get_logger
from app.auth.jwt_auth import auth_manager

log = get_logger("api")

router = APIRouter()

# These will be set by main.py after engine initialization
_engine = None
_orderbook = None


def set_engine(engine: Any) -> None:
    global _engine
    _engine = engine


def set_orderbook(orderbook: Any) -> None:
    global _orderbook
    _orderbook = orderbook


# --- Auth Models ---

class AuthStartRequest(BaseModel):
    token: str
    address: str
    chain: str = "bsc"
    ed25519_private_key_hex: str
    request_id: str


class ConfigUpdate(BaseModel):
    spread_bps: Optional[float] = None
    order_size: Optional[float] = None
    refresh_interval: Optional[float] = None


# --- Auth Endpoint ---

@router.post("/auth/start")
async def auth_start(req: AuthStartRequest) -> dict[str, Any]:
    """
    Receive JWT token and ed25519 keys from frontend after MetaMask login.
    Stores credentials and starts the trading engine if not already running.
    """
    await auth_manager.set_credentials(
        token=req.token,
        address=req.address,
        chain=req.chain,
        ed25519_private_key_hex=req.ed25519_private_key_hex,
        request_id=req.request_id,
    )

    # Start engine if it exists and is not running
    if _engine is not None:
        from app.trading.engine import BotStatus
        if _engine.status in (BotStatus.STARTING, BotStatus.PAUSED, BotStatus.KILLED):
            await _engine.start()
            log.info("api.engine_started_after_auth")

    return {
        "message": "Authenticated successfully",
        "address": req.address,
        "chain": req.chain,
        "engine_started": _engine is not None,
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


@router.get("/positions")
async def get_positions() -> dict[str, Any]:
    """Get current position and risk status."""
    from app.trading.risk import risk_manager
    return risk_manager.get_status()


@router.post("/config")
async def update_config(config: ConfigUpdate) -> dict[str, Any]:
    """Update runtime configuration."""
    updates = update_runtime_settings(
        spread_bps=config.spread_bps,
        order_size=config.order_size,
        refresh_interval=config.refresh_interval,
    )
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    log.info("api.config_updated", updates=updates)
    return {
        "message": "Configuration updated",
        "updated_fields": updates,
        "current_config": {
            "spread_bps": settings.spread_bps,
            "order_size": settings.order_size,
            "refresh_interval": settings.refresh_interval,
        },
    }


@router.post("/kill")
async def kill_bot() -> dict[str, str]:
    """Emergency kill switch — cancel all orders and stop engine."""
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    log.warning("api.kill_switch_activated")
    await _engine.kill()
    return {"message": "Kill switch activated — all orders cancelled, engine stopped"}
