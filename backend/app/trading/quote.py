"""
Quote generator with inventory-based spread skew.

Generates asymmetric bid/ask prices:
- Long position → bid goes wider (discourage more buys)
- Short position → ask goes wider (discourage more sells)
- Flat → symmetric spread

Sizing: notional / mid_price, or qty_override if set.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.logger import get_logger

log = get_logger("quote")


@dataclass
class Quote:
    """A two-sided quote with skew info."""
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float
    mid_price: float
    spread_bps: float        # Total spread (bid + ask)
    bid_spread_bps: float    # Bid-side half-spread
    ask_spread_bps: float    # Ask-side half-spread
    skew_bps: float          # Current inventory skew

    @property
    def bid_deviation_bps(self) -> float:
        """Deviation of bid from mid in basis points."""
        if self.mid_price == 0:
            return 0.0
        return (self.mid_price - self.bid_price) / self.mid_price * 10000.0

    @property
    def ask_deviation_bps(self) -> float:
        """Deviation of ask from mid in basis points."""
        if self.mid_price == 0:
            return 0.0
        return (self.ask_price - self.mid_price) / self.mid_price * 10000.0

    @property
    def is_within_max_deviation(self) -> bool:
        """Check if both sides are within the max allowed deviation."""
        max_dev = settings.max_spread_deviation_bps
        return self.bid_deviation_bps <= max_dev and self.ask_deviation_bps <= max_dev

    def to_dict(self) -> dict:
        return {
            "bid_price": round(self.bid_price, 8),
            "bid_size": round(self.bid_size, 8),
            "ask_price": round(self.ask_price, 8),
            "ask_size": round(self.ask_size, 8),
            "mid_price": round(self.mid_price, 8),
            "spread_bps": round(self.spread_bps, 4),
            "bid_spread_bps": round(self.bid_spread_bps, 4),
            "ask_spread_bps": round(self.ask_spread_bps, 4),
            "skew_bps": round(self.skew_bps, 4),
            "bid_deviation_bps": round(self.bid_deviation_bps, 4),
            "ask_deviation_bps": round(self.ask_deviation_bps, 4),
            "within_limits": self.is_within_max_deviation,
        }


class QuoteGenerator:
    """Generates two-sided quotes with inventory skew."""

    def generate(
        self,
        mid_price: float,
        position_size: float = 0.0,
        max_position: float | None = None,
        skew_factor_bps: float | None = None,
        spread_bps: float | None = None,
        order_notional: float | None = None,
        qty_override: float | None = None,
    ) -> Quote:
        """
        Generate a skewed two-sided quote.

        Skew formula:
            skew = (position / max_position) * skew_factor
            bid_spread = base_spread + max(0, skew)    -- long → bid wider
            ask_spread = base_spread + max(0, -skew)   -- short → ask wider
        """
        base_spread = spread_bps if spread_bps is not None else settings.spread_bps
        max_pos = max_position if max_position is not None else settings.max_position
        skew_factor = skew_factor_bps if skew_factor_bps is not None else settings.skew_factor_bps

        # Calculate inventory skew
        if max_pos > 0 and position_size != 0:
            skew = (position_size / max_pos) * skew_factor
        else:
            skew = 0.0

        # Asymmetric spread
        bid_spread = base_spread + max(0.0, skew)     # Long → bid goes wider
        ask_spread = base_spread + max(0.0, -skew)    # Short → ask goes wider

        # Calculate prices
        bid_price = mid_price * (1.0 - bid_spread / 10000.0)
        ask_price = mid_price * (1.0 + ask_spread / 10000.0)

        # Calculate size: qty_override > notional > order_size fallback
        notional = order_notional if order_notional is not None else settings.order_notional
        qty_ovr = qty_override if qty_override is not None else settings.qty_override

        if qty_ovr and qty_ovr > 0:
            size = qty_ovr
        elif notional > 0 and mid_price > 0:
            size = notional / mid_price
        else:
            size = settings.order_size

        total_spread = bid_spread + ask_spread

        quote = Quote(
            bid_price=bid_price,
            bid_size=size,
            ask_price=ask_price,
            ask_size=size,
            mid_price=mid_price,
            spread_bps=total_spread,
            bid_spread_bps=bid_spread,
            ask_spread_bps=ask_spread,
            skew_bps=round(skew, 4),
        )

        if not quote.is_within_max_deviation:
            log.warning(
                "quote.exceeds_max_deviation",
                bid_dev=quote.bid_deviation_bps,
                ask_dev=quote.ask_deviation_bps,
                max_dev=settings.max_spread_deviation_bps,
            )

        return quote


# Singleton
quote_generator = QuoteGenerator()
