"""
Configuration loader.

All settings loaded from .env file via Pydantic BaseSettings.
Runtime-modifiable fields: spread_bps, order_size, refresh_interval.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_CONFIG_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded entirely from .env file."""

    model_config = SettingsConfigDict(
        env_file=str(_CONFIG_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API endpoints
    standx_api_base: str = Field(default="https://api.standx.com")
    standx_ws_url: str = Field(default="wss://ws.standx.com")

    # Trading parameters
    symbol: str = Field(default="ETH-PERP")
    spread_bps: float = Field(default=5.0)
    order_size: float = Field(default=0.1)
    refresh_interval: float = Field(default=5.0)

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
    order_size: float | None = None,
    refresh_interval: float | None = None,
) -> dict[str, Any]:
    """Update runtime-modifiable settings. Returns updated values."""
    global settings
    updates: dict[str, Any] = {}
    if spread_bps is not None:
        settings.spread_bps = spread_bps
        updates["spread_bps"] = spread_bps
    if order_size is not None:
        settings.order_size = order_size
        updates["order_size"] = order_size
    if refresh_interval is not None:
        settings.refresh_interval = refresh_interval
        updates["refresh_interval"] = refresh_interval
    return updates
