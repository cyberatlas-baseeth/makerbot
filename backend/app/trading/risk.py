"""
Risk management module — minimal version for uptime-only bot.

Only tracks max notional exposure for safety.
"""

from __future__ import annotations

from app.config import settings
from app.logger import get_logger

log = get_logger("risk")


class RiskManager:
    """Minimal risk manager for uptime-only bot."""

    def get_status(self) -> dict:
        """Return risk status summary."""
        return {
            "max_notional": settings.max_notional,
        }


# Singleton
risk_manager = RiskManager()
