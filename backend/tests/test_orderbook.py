"""Tests for the Orderbook module."""

import asyncio
import pytest
from app.market_data.orderbook import Orderbook


@pytest.fixture
def orderbook():
    return Orderbook(symbol="ETH-PERP")


@pytest.mark.asyncio
async def test_empty_orderbook(orderbook):
    assert orderbook.mid_price is None
    assert orderbook.best_bid is None
    assert orderbook.best_ask is None
    assert orderbook.spread_bps is None


@pytest.mark.asyncio
async def test_snapshot(orderbook):
    bids = [[100.0, 1.0], [99.0, 2.0], [98.0, 3.0]]
    asks = [[101.0, 1.0], [102.0, 2.0], [103.0, 3.0]]
    await orderbook.update_snapshot(bids, asks)

    assert orderbook.best_bid == 100.0
    assert orderbook.best_ask == 101.0
    assert orderbook.mid_price == 100.5
    assert orderbook.spread_bps is not None
    assert orderbook.spread_bps == pytest.approx(
        (101.0 - 100.0) / 100.5 * 10000.0, rel=1e-4
    )


@pytest.mark.asyncio
async def test_delta_add(orderbook):
    await orderbook.update_snapshot([[100.0, 1.0]], [[101.0, 1.0]])
    await orderbook.update_delta("bid", 100.5, 2.0)
    assert orderbook.best_bid == 100.5


@pytest.mark.asyncio
async def test_delta_remove(orderbook):
    await orderbook.update_snapshot(
        [[100.0, 1.0], [99.0, 1.0]],
        [[101.0, 1.0]],
    )
    await orderbook.update_delta("bid", 100.0, 0)
    assert orderbook.best_bid == 99.0


@pytest.mark.asyncio
async def test_top_levels(orderbook):
    bids = [[100.0, 1.0], [99.0, 2.0]]
    asks = [[101.0, 1.0], [102.0, 2.0]]
    await orderbook.update_snapshot(bids, asks)

    levels = orderbook.get_top_levels(depth=1)
    assert len(levels["bids"]) == 1
    assert len(levels["asks"]) == 1
    assert levels["bids"][0]["price"] == 100.0
    assert levels["asks"][0]["price"] == 101.0
    assert levels["mid_price"] == 100.5
