"""Tests for the UptimeTracker module."""

import time
import pytest
from unittest.mock import patch
from app.uptime.tracker import UptimeTracker


@pytest.fixture
def tracker():
    with patch("app.uptime.tracker.settings") as mock_settings:
        mock_settings.uptime_target_minutes = 30
        t = UptimeTracker()
        yield t


def test_initial_state(tracker):
    assert tracker.current_uptime_pct == 0.0
    assert not tracker.is_target_met


def test_tick_active(tracker):
    tracker._last_tick = time.time() - 10.0  # Simulate 10 seconds passed
    tracker.tick(has_both_sides=True)
    assert tracker._current_record.total_active_seconds >= 9.0  # Allow for timing


def test_tick_inactive(tracker):
    tracker._last_tick = time.time() - 10.0
    tracker.tick(has_both_sides=False)
    assert tracker._current_record.total_active_seconds < 1.0


def test_target_met(tracker):
    tracker._current_record.total_active_seconds = 1800.0
    assert tracker.is_target_met


def test_target_not_met(tracker):
    tracker._current_record.total_active_seconds = 1799.0
    assert not tracker.is_target_met


def test_seconds_remaining(tracker):
    tracker._current_record.total_active_seconds = 1000.0
    assert tracker.seconds_remaining_for_target == pytest.approx(800.0, abs=1.0)


def test_get_stats(tracker):
    stats = tracker.get_stats()
    assert "current_hour" in stats
    assert "history" in stats
    assert "hours_target_met_last_24h" in stats
    assert "avg_uptime_pct_last_24h" in stats


def test_rollover(tracker):
    # Force a rollover by setting current hour to a past hour
    tracker._current_hour = time.time() - 7200  # 2 hours ago
    tracker._current_record.total_active_seconds = 1500.0
    tracker.tick(has_both_sides=True)
    # After rollover, history should have the old record
    assert len(tracker._history) == 1
    assert tracker._history[0].total_active_seconds == 1500.0
