"""Tests for the QuoteGenerator module."""

import pytest
from unittest.mock import patch
from app.trading.quote import QuoteGenerator


@pytest.fixture
def gen():
    return QuoteGenerator()


def test_basic_quote(gen):
    quote = gen.generate(mid_price=1000.0, spread_bps=5.0, order_size=0.1)
    assert quote.bid_price == pytest.approx(1000.0 * (1 - 5.0 / 10000.0), rel=1e-8)
    assert quote.ask_price == pytest.approx(1000.0 * (1 + 5.0 / 10000.0), rel=1e-8)
    assert quote.bid_size == 0.1
    assert quote.ask_size == 0.1
    assert quote.mid_price == 1000.0


def test_spread_symmetry(gen):
    quote = gen.generate(mid_price=2000.0, spread_bps=3.0, order_size=1.0)
    bid_dev = abs(quote.mid_price - quote.bid_price)
    ask_dev = abs(quote.ask_price - quote.mid_price)
    assert bid_dev == pytest.approx(ask_dev, rel=1e-8)


def test_within_10bps(gen):
    quote = gen.generate(mid_price=1000.0, spread_bps=5.0)
    assert quote.is_within_max_deviation


def test_exceeds_10bps(gen):
    # With max_spread_deviation_bps=10, a 15 bps spread should exceed
    with patch("app.trading.quote.settings") as mock_settings:
        mock_settings.max_spread_deviation_bps = 10.0
        mock_settings.spread_bps = 15.0
        mock_settings.order_size = 0.1
        quote = gen.generate(mid_price=1000.0, spread_bps=15.0)
        assert not quote.is_within_max_deviation


def test_zero_mid(gen):
    quote = gen.generate(mid_price=0.0, spread_bps=5.0, order_size=0.1)
    assert quote.bid_price == 0.0
    assert quote.ask_price == 0.0
    assert quote.bid_deviation_bps == 0.0


def test_to_dict(gen):
    quote = gen.generate(mid_price=1500.0, spread_bps=5.0, order_size=0.5)
    d = quote.to_dict()
    assert "bid_price" in d
    assert "ask_price" in d
    assert "within_limits" in d
    assert isinstance(d["within_limits"], bool)
