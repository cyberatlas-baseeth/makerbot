"""
Risk management module.

Enforces position limits and max notional exposure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time

from app.config import settings
from app.logger import get_logger

log = get_logger("risk")


@dataclass
class Position:
    """Current position state."""
    size: float = 0.0          # Net position in base asset (positive = long)
    avg_entry: float = 0.0     # Average entry price
    notional: float = 0.0      # abs(size) * mark_price
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    last_update: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "size": round(self.size, 8),
            "avg_entry": round(self.avg_entry, 4),
            "notional": round(self.notional, 4),
            "unrealized_pnl": round(self.unrealized_pnl, 4),
            "realized_pnl": round(self.realized_pnl, 4),
            "last_update": self.last_update,
        }


class RiskManager:
    """Enforces trading risk limits."""

    def __init__(self) -> None:
        self.position = Position()

    def update_position(
        self,
        size: float,
        avg_entry: float,
        mark_price: float,
        unrealized_pnl: float = 0.0,
        realized_pnl: float = 0.0,
    ) -> None:
        """Update the current position from exchange data."""
        self.position.size = size
        self.position.avg_entry = avg_entry
        self.position.notional = abs(size) * mark_price
        self.position.unrealized_pnl = unrealized_pnl
        self.position.realized_pnl = realized_pnl
        self.position.last_update = time.time()

    def check_can_place_order(
        self,
        side: str,
        size: float,
        price: float,
    ) -> bool:
        """
        Check if a new order can be placed without exceeding risk limits.

        Args:
            side: 'buy' or 'sell'
            size: order size in base asset
            price: order price

        Returns:
            True if the order is within risk limits.
        """
        # Calculate resulting position if filled
        if side == "buy":
            resulting_size = self.position.size + size
        else:
            resulting_size = self.position.size - size

        # Check max position limit
        if abs(resulting_size) > settings.max_position:
            log.warning(
                "risk.position_limit_exceeded",
                current=self.position.size,
                order_side=side,
                order_size=size,
                resulting=resulting_size,
                limit=settings.max_position,
            )
            return False

        # Check max notional limit
        resulting_notional = abs(resulting_size) * price
        if resulting_notional > settings.max_notional:
            log.warning(
                "risk.notional_limit_exceeded",
                current_notional=self.position.notional,
                resulting_notional=resulting_notional,
                limit=settings.max_notional,
            )
            return False

        return True

    def should_reduce_only(self) -> bool:
        """Check if we should only reduce position (near limits)."""
        utilization = self.position.notional / settings.max_notional if settings.max_notional > 0 else 0
        return utilization > 0.9

    def get_status(self) -> dict:
        """Return risk status summary."""
        return {
            "position": self.position.to_dict(),
            "max_position": settings.max_position,
            "max_notional": settings.max_notional,
            "position_utilization": round(
                abs(self.position.size) / settings.max_position * 100
                if settings.max_position > 0
                else 0,
                2,
            ),
            "notional_utilization": round(
                self.position.notional / settings.max_notional * 100
                if settings.max_notional > 0
                else 0,
                2,
            ),
        }


# Singleton
risk_manager = RiskManager()
