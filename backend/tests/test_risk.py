"""Tests for the RiskManager module (minimal, uptime-only)."""

from unittest.mock import patch
from app.trading.risk import RiskManager


def test_get_status():
    with patch("app.trading.risk.settings") as mock_settings:
        mock_settings.max_notional = 10000.0
        rm = RiskManager()
        status = rm.get_status()
        assert "max_notional" in status
        assert status["max_notional"] == 10000.0
