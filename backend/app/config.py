"""
Configuration loader.

All settings loaded from .env file via Pydantic BaseSettings.
Runtime-modifiable fields: spread_bps, bid_notional, ask_notional,
skew_factor_bps, refresh_interval, auto_close_fills.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_CONFIG_DIR = Path(__file__).resolve().parent.parent

# Supported trading pairs
SUPPORTED_SYMBOLS = ["BTC-USD", "ETH-USD", "XAU-USD", "XAG-USD"]


class Settings(BaseSettings):
    """Application settings loaded entirely from .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_CONFIG_DIR / ".env"),
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
    bid_notional: float = Field(default=500.0)       # Bid order size in USD
    ask_notional: float = Field(default=500.0)       # Ask order size in USD
    order_size: float = Field(default=0.1)           # Legacy fallback
    refresh_interval: float = Field(default=5.0)

    # Inventory skew
    skew_factor_bps: float = Field(default=3.0)      # Skew per unit position

    # Persistent order management
    requote_threshold_bps: float = Field(default=2.0)   # Min drift before replacing
    proximity_guard_bps: float = Field(default=1.0)     # Auto-refresh when this close to being hit

    # Auto-close fills
    auto_close_fills: bool = Field(default=True)     # Market close if order fills

    # Risk limits
    max_notional: float = Field(default=10000.0)
    max_position: float = Field(default=1.0)

    # Uptime
    uptime_target_minutes: int = Field(default=30)

    # Engine safety
    max_consecutive_failures: int = Field(default=5)
    stale_order_seconds: float = Field(default=30.0)
    max_spread_deviation_bps: float = Field(default=10.0)


# Singleton
settings = Settings()


def update_runtime_settings(
    spread_bps: float | None = None,
    bid_notional: float | None = None,
    ask_notional: float | None = None,
    skew_factor_bps: float | None = None,
    order_size: float | None = None,
    refresh_interval: float | None = None,
    auto_close_fills: bool | None = None,
    symbol: str | None = None,
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
    if skew_factor_bps is not None:
        settings.skew_factor_bps = skew_factor_bps
        updates["skew_factor_bps"] = skew_factor_bps
    if order_size is not None:
        settings.order_size = order_size
        updates["order_size"] = order_size
    if refresh_interval is not None:
        settings.refresh_interval = refresh_interval
        updates["refresh_interval"] = refresh_interval
    if auto_close_fills is not None:
        settings.auto_close_fills = auto_close_fills
        updates["auto_close_fills"] = auto_close_fills
    return updates
