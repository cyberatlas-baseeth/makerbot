"""Tests for the RiskManager module."""

import pytest
from unittest.mock import patch
from app.trading.risk import RiskManager


@pytest.fixture
def risk():
    with patch("app.trading.risk.settings") as mock_settings:
        mock_settings.max_notional = 10000.0
        mock_settings.max_position = 1.0
        rm = RiskManager()
        yield rm


def test_initial_position(risk):
    assert risk.position.size == 0.0
    assert risk.position.notional == 0.0


def test_can_place_order_within_limits(risk):
    assert risk.check_can_place_order("buy", 0.5, 1000.0)


def test_position_limit_exceeded(risk):
    risk.update_position(size=0.9, avg_entry=1000.0, mark_price=1000.0)
    assert not risk.check_can_place_order("buy", 0.2, 1000.0)


def test_notional_limit_exceeded(risk):
    risk.update_position(size=0.1, avg_entry=1000.0, mark_price=1000.0)
    # Trying to buy 20 units at 1000 = 20000 notional > 10000 limit
    assert not risk.check_can_place_order("buy", 20.0, 1000.0)


def test_sell_reduces_position(risk):
    risk.update_position(size=0.8, avg_entry=1000.0, mark_price=1000.0)
    # Selling 0.3 brings position to 0.5, within limits
    assert risk.check_can_place_order("sell", 0.3, 1000.0)


def test_should_reduce_only(risk):
    risk.update_position(size=0.95, avg_entry=1000.0, mark_price=10000.0)
    # notional = 0.95 * 10000 = 9500, utilization = 95%
    assert risk.should_reduce_only()


def test_get_status(risk):
    status = risk.get_status()
    assert "position" in status
    assert "max_position" in status
    assert "max_notional" in status
    assert "position_utilization" in status
    assert "notional_utilization" in status
