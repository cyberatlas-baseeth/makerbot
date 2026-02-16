"""
Quote generator.

Generates bid/ask prices based on mid-price and configured spread.
Validates that quotes remain within the 10 bps max deviation from mid.
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
    spread_bps: float

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
            "bid_deviation_bps": round(self.bid_deviation_bps, 4),
            "ask_deviation_bps": round(self.ask_deviation_bps, 4),
            "within_limits": self.is_within_max_deviation,
        }


class QuoteGenerator:
    """Generates two-sided quotes from mid-price + spread."""

    def generate(
        self,
        mid_price: float,
        spread_bps: float | None = None,
        order_size: float | None = None,
    ) -> Quote:
        """
        Generate a two-sided quote.

        bid = mid * (1 - spread_bps / 10000)
        ask = mid * (1 + spread_bps / 10000)
        """
        spread = spread_bps if spread_bps is not None else settings.spread_bps
        size = order_size if order_size is not None else settings.order_size

        half_spread = spread / 10000.0
        bid_price = mid_price * (1.0 - half_spread)
        ask_price = mid_price * (1.0 + half_spread)

        quote = Quote(
            bid_price=bid_price,
            bid_size=size,
            ask_price=ask_price,
            ask_size=size,
            mid_price=mid_price,
            spread_bps=spread * 2.0,  # Total spread
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
