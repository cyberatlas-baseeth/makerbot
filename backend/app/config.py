"""
Configuration loader.

All settings loaded from .env file via Pydantic BaseSettings.
Runtime-modifiable fields: spread_bps, bid_notional, ask_notional,
requote_threshold_bps, refresh_interval.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_path() -> Path:
    """Return .env path — next to exe when frozen, else next to backend dir."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / ".env"
    return Path(__file__).resolve().parent.parent / ".env"


_ENV_FILE = _get_env_path()

# Supported trading pairs
SUPPORTED_SYMBOLS = ["BTC-USD", "ETH-USD", "XAU-USD", "XAG-USD"]

# Qty tick sizes per symbol (minimum qty increment accepted by StandX)
QTY_TICKS: dict[str, float] = {
    "BTC-USD": 0.0001,
    "ETH-USD": 0.001,
    "XAU-USD": 0.01,
    "XAG-USD": 0.1,
}

# Price tick sizes per symbol (minimum price increment accepted by StandX)
PRICE_TICKS: dict[str, float] = {
    "BTC-USD": 0.01,
    "ETH-USD": 0.1,
    "XAU-USD": 0.1,
    "XAG-USD": 0.01,
}


class Settings(BaseSettings):
    """Application settings loaded entirely from .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API endpoints
    standx_api_base: str = Field(default="https://perps.standx.com")
    standx_ws_url: str = Field(default="wss://perps.standx.com/ws-stream/v1")

    # StandX credentials (loaded from .env)
    standx_jwt_token: str = Field(default="")
    standx_ed25519_private_key: str = Field(default="")
    standx_wallet_address: str = Field(default="")
    standx_chain: str = Field(default="bsc")

    # Trading parameters
    symbol: str = Field(default="BTC-USD")
    spread_bps: float = Field(default=50.0)         # Half-spread each side (test=50, prod=10)
    bid_notional: float = Field(default=30.0)        # Bid order size in USD
    ask_notional: float = Field(default=30.0)        # Ask order size in USD
    refresh_interval: float = Field(default=1.0)       # Engine tick every 1s

    # Persistent order management
    requote_threshold_bps: float = Field(default=25.0)    # Refresh orders when mid moves ±X bps
    proximity_guard_bps: float = Field(default=1.0)     # Auto-refresh when this close to being hit

    # Risk limits
    max_notional: float = Field(default=10000.0)

    # Uptime
    uptime_target_minutes: int = Field(default=30)

    # Take Profit / Stop Loss (USD offset from entry price, 0 = disabled)
    tp_usd: float = Field(default=0.0)
    sl_usd: float = Field(default=0.0)

    # Auto-close partial-fill positions (reduce_only market order)
    auto_close_fills: bool = Field(default=True)

    # Engine safety
    max_consecutive_failures: int = Field(default=5)
    stale_order_seconds: float = Field(default=30.0)
    max_spread_deviation_bps: float = Field(default=200.0)  # Max allowed deviation per side


# Singleton
settings = Settings()


def update_runtime_settings(
    spread_bps: float | None = None,
    bid_notional: float | None = None,
    ask_notional: float | None = None,
    requote_threshold_bps: float | None = None,
    refresh_interval: float | None = None,
    symbol: str | None = None,
    tp_usd: float | None = None,
    sl_usd: float | None = None,
) -> dict[str, Any]:
    """Update runtime-modifiable settings. Returns updated values."""
    global settings
    updates: dict[str, Any] = {}
    if symbol is not None:
        if symbol not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Unsupported symbol: {symbol}. Must be one of {SUPPORTED_SYMBOLS}")
        settings.symbol = symbol
        updates["symbol"] = symbol
    if spread_bps is not None:
        settings.spread_bps = spread_bps
        updates["spread_bps"] = spread_bps
    if bid_notional is not None:
        settings.bid_notional = bid_notional
        updates["bid_notional"] = bid_notional
    if ask_notional is not None:
        settings.ask_notional = ask_notional
        updates["ask_notional"] = ask_notional
    if requote_threshold_bps is not None:
        settings.requote_threshold_bps = requote_threshold_bps
        updates["requote_threshold_bps"] = requote_threshold_bps
    if refresh_interval is not None:
        settings.refresh_interval = refresh_interval
        updates["refresh_interval"] = refresh_interval
    if tp_usd is not None:
        settings.tp_usd = tp_usd
        updates["tp_usd"] = tp_usd
    if sl_usd is not None:
        settings.sl_usd = sl_usd
        updates["sl_usd"] = sl_usd
    return updates
