"""
Quote generator — symmetric spread quoting for maker uptime.

Generates symmetric bid/ask prices around mid:
- bid_price = mid * (1 - spread_bps / 10000)
- ask_price = mid * (1 + spread_bps / 10000)

Sizing: bid_notional / mid for bid, ask_notional / mid for ask.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.logger import get_logger

log = get_logger("quote")


@dataclass
class Quote:
    """A two-sided quote."""
    bid_price: float
    bid_size: float
    ask_price: float
    ask_size: float
    mid_price: float
    spread_bps: float        # Total spread (bid + ask)
    bid_spread_bps: float    # Bid-side half-spread
    ask_spread_bps: float    # Ask-side half-spread

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
            "bid_deviation_bps": round(self.bid_deviation_bps, 4),
            "ask_deviation_bps": round(self.ask_deviation_bps, 4),
            "within_limits": self.is_within_max_deviation,
        }


class QuoteGenerator:
    """Generates symmetric two-sided quotes for maker uptime."""

    def generate(
        self,
        mid_price: float,
        spread_bps: float | None = None,
        bid_notional: float | None = None,
        ask_notional: float | None = None,
    ) -> Quote:
        """
        Generate a symmetric two-sided quote.

        Sizing:
            bid_size = bid_notional / mid_price
            ask_size = ask_notional / mid_price
        """
        base_spread = spread_bps if spread_bps is not None else settings.spread_bps

        # Symmetric spread
        bid_spread = base_spread
        ask_spread = base_spread

        # Calculate prices
        bid_price = mid_price * (1.0 - bid_spread / 10000.0)
        ask_price = mid_price * (1.0 + ask_spread / 10000.0)

        # Calculate sizes from separate notionals
        b_notional = bid_notional if bid_notional is not None else settings.bid_notional
        a_notional = ask_notional if ask_notional is not None else settings.ask_notional

        if mid_price > 0:
            bid_size = b_notional / mid_price
            ask_size = a_notional / mid_price
        else:
            bid_size = 0.0
            ask_size = 0.0

        total_spread = bid_spread + ask_spread

        quote = Quote(
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
            mid_price=mid_price,
            spread_bps=total_spread,
            bid_spread_bps=bid_spread,
            ask_spread_bps=ask_spread,
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
