"""
Configuration loader.

Merges .env secrets with config.yaml tuning parameters via Pydantic BaseSettings.
Runtime-modifiable fields: spread_bps, order_size, refresh_interval.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_CONFIG_DIR = Path(__file__).resolve().parent.parent
_YAML_PATH = _CONFIG_DIR / "config.yaml"


def _load_yaml() -> dict[str, Any]:
    """Load config.yaml if it exists."""
    if _YAML_PATH.exists():
        with open(_YAML_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


_yaml_data = _load_yaml()


class Settings(BaseSettings):
    """Application settings – env vars take precedence over YAML defaults."""

    model_config = SettingsConfigDict(
        env_file=str(_CONFIG_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Secrets (from .env only) ──────────────────────────────────────
    private_key: str = Field(default="", description="Wallet private key (hex)")

    # ── API Endpoints ────────────────────────────────────────────────
    standx_api_url: str = Field(
        default=_yaml_data.get("standx_api_url", "https://api.standx.io")
    )
    standx_ws_url: str = Field(
        default=_yaml_data.get("standx_ws_url", "wss://ws.standx.io")
    )

    # ── Trading Parameters ───────────────────────────────────────────
    symbol: str = Field(default=_yaml_data.get("symbol", "ETH-PERP"))
    spread_bps: float = Field(default=_yaml_data.get("spread_bps", 5.0))
    order_size: float = Field(default=_yaml_data.get("order_size", 0.1))
    refresh_interval: float = Field(default=_yaml_data.get("refresh_interval", 5.0))

    # ── Risk Limits ──────────────────────────────────────────────────
    max_notional: float = Field(default=_yaml_data.get("max_notional", 10000.0))
    max_position: float = Field(default=_yaml_data.get("max_position", 1.0))

    # ── Uptime ───────────────────────────────────────────────────────
    uptime_target_minutes: int = Field(
        default=_yaml_data.get("uptime_target_minutes", 30)
    )

    # ── Engine Safety ────────────────────────────────────────────────
    max_consecutive_failures: int = Field(
        default=_yaml_data.get("max_consecutive_failures", 5)
    )
    stale_order_seconds: float = Field(
        default=_yaml_data.get("stale_order_seconds", 30.0)
    )
    max_spread_deviation_bps: float = Field(
        default=_yaml_data.get("max_spread_deviation_bps", 10.0)
    )


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
