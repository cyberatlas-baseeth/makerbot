"""
Local orderbook state manager.

Maintains sorted bid/ask levels, computes mid-price and spread.
Thread-safe via asyncio.Lock.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from app.logger import get_logger

log = get_logger("orderbook")


@dataclass
class PriceLevel:
    """Single price level in the orderbook."""
    price: float
    size: float
    timestamp: float = field(default_factory=time.time)


class Orderbook:
    """
    In-memory orderbook maintaining sorted bids and asks.

    Bids are sorted descending (best bid first).
    Asks are sorted ascending (best ask first).
    """

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._bids: dict[float, PriceLevel] = {}
        self._asks: dict[float, PriceLevel] = {}
        self._lock = asyncio.Lock()
        self._last_update: float = 0.0

    async def update_snapshot(self, bids: list[list[float]], asks: list[list[float]]) -> None:
        """Replace the entire orderbook with a snapshot."""
        async with self._lock:
            self._bids.clear()
            self._asks.clear()
            now = time.time()
            for price, size in bids:
                self._bids[price] = PriceLevel(price=price, size=size, timestamp=now)
            for price, size in asks:
                self._asks[price] = PriceLevel(price=price, size=size, timestamp=now)
            self._last_update = now
        log.debug("orderbook.snapshot", symbol=self.symbol, bids=len(bids), asks=len(asks))

    async def update_delta(self, side: str, price: float, size: float) -> None:
        """Apply an incremental update to the orderbook."""
        async with self._lock:
            book = self._bids if side == "bid" else self._asks
            if size <= 0:
                book.pop(price, None)
            else:
                book[price] = PriceLevel(price=price, size=size, timestamp=time.time())
            self._last_update = time.time()

    @property
    def best_bid(self) -> float | None:
        """Highest bid price."""
        if not self._bids:
            return None
        return max(self._bids.keys())

    @property
    def best_ask(self) -> float | None:
        """Lowest ask price."""
        if not self._asks:
            return None
        return min(self._asks.keys())

    @property
    def mid_price(self) -> float | None:
        """Mid price = (best_bid + best_ask) / 2."""
        bb = self.best_bid
        ba = self.best_ask
        if bb is None or ba is None:
            return None
        return (bb + ba) / 2.0

    @property
    def spread_bps(self) -> float | None:
        """Spread in basis points = (ask - bid) / mid * 10000."""
        bb = self.best_bid
        ba = self.best_ask
        mid = self.mid_price
        if bb is None or ba is None or mid is None or mid == 0:
            return None
        return (ba - bb) / mid * 10000.0

    @property
    def last_update(self) -> float:
        return self._last_update

    def get_top_levels(self, depth: int = 5) -> dict[str, Any]:
        """Return top N bid/ask levels."""
        sorted_bids = sorted(self._bids.values(), key=lambda x: x.price, reverse=True)[:depth]
        sorted_asks = sorted(self._asks.values(), key=lambda x: x.price)[:depth]
        return {
            "bids": [{"price": l.price, "size": l.size} for l in sorted_bids],
            "asks": [{"price": l.price, "size": l.size} for l in sorted_asks],
            "mid_price": self.mid_price,
            "spread_bps": self.spread_bps,
            "last_update": self._last_update,
        }
