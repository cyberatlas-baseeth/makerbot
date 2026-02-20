"""Tests for the dual UptimeTracker module."""

import time
import pytest
from unittest.mock import patch
from app.uptime.tracker import UptimeTracker, MAKER_MAX_SPREAD_BPS


@pytest.fixture
def tracker():
    with patch("app.uptime.tracker.settings") as mock_settings:
        mock_settings.uptime_target_minutes = 30
        t = UptimeTracker()
        yield t


def test_initial_state(tracker):
    assert tracker.current_maker_uptime_pct == 0.0
    assert tracker.current_mm_uptime_pct == 0.0
    assert not tracker.is_maker_target_met


def test_tick_maker_spread(tracker):
    """spread ≤ 5 bps → maker counter increments"""
    tracker._last_tick = time.time() - 10.0
    tracker.tick(has_both_sides=True, spread_bps=5.0)
    assert tracker._current_record.maker_active_seconds >= 9.0
    assert tracker._current_record.mm_active_seconds < 1.0


def test_tick_mm_spread(tracker):
    """spread > 5 bps → mm counter increments"""
    tracker._last_tick = time.time() - 10.0
    tracker.tick(has_both_sides=True, spread_bps=50.0)
    assert tracker._current_record.mm_active_seconds >= 9.0
    assert tracker._current_record.maker_active_seconds < 1.0


def test_tick_inactive(tracker):
    """No orders → neither counter increments"""
    tracker._last_tick = time.time() - 10.0
    tracker.tick(has_both_sides=False, spread_bps=5.0)
    assert tracker._current_record.maker_active_seconds < 1.0
    assert tracker._current_record.mm_active_seconds < 1.0


def test_elapsed_capped(tracker):
    """Elapsed should be capped at 10s to prevent jumps after sleep."""
    tracker._last_tick = time.time() - 300.0  # 5 minutes ago
    tracker.tick(has_both_sides=True, spread_bps=5.0)
    assert tracker._current_record.maker_active_seconds <= 10.0


def test_maker_target_met(tracker):
    tracker._current_record.maker_active_seconds = 1800.0
    assert tracker.is_maker_target_met


def test_maker_target_not_met(tracker):
    tracker._current_record.maker_active_seconds = 1799.0
    assert not tracker.is_maker_target_met


def test_seconds_remaining(tracker):
    tracker._current_record.maker_active_seconds = 1000.0
    assert tracker.seconds_remaining_for_target == pytest.approx(800.0, abs=1.0)


def test_get_stats(tracker):
    stats = tracker.get_stats()
    assert "current_hour" in stats
    assert "history" in stats
    assert "hours_target_met_last_24h" in stats
    assert "avg_maker_uptime_pct_last_24h" in stats
    assert "avg_mm_uptime_pct_last_24h" in stats


def test_rollover(tracker):
    tracker._current_hour = time.time() - 7200
    tracker._current_record.maker_active_seconds = 1500.0
    tracker._current_record.mm_active_seconds = 500.0
    tracker.tick(has_both_sides=True, spread_bps=5.0)
    assert len(tracker._history) == 1
    assert tracker._history[0].maker_active_seconds == 1500.0
    assert tracker._history[0].mm_active_seconds == 500.0


def test_reset(tracker):
    tracker._current_record.maker_active_seconds = 1000.0
    tracker._current_record.mm_active_seconds = 200.0
    tracker.reset()
    assert tracker._current_record.maker_active_seconds == 0.0
    assert tracker._current_record.mm_active_seconds == 0.0
    assert len(tracker._history) == 0


def test_boundary_spread(tracker):
    """Exactly 5 bps → should count as maker."""
    tracker._last_tick = time.time() - 5.0
    tracker.tick(has_both_sides=True, spread_bps=MAKER_MAX_SPREAD_BPS)
    assert tracker._current_record.maker_active_seconds >= 4.0
    assert tracker._current_record.mm_active_seconds < 1.0
