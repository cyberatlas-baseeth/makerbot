"""
Maker uptime tracker.

Tracks per-hour maker uptime to ensure the bot maintains
at least 30 minutes of active quoting per hour (StandX eligibility).

- tick(has_both_sides) is called every engine loop iteration.
- Automatically resets every hour.
- Stores history for the last 24 hours.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.logger import get_logger

log = get_logger("uptime")


@dataclass
class HourlyRecord:
    """Record for a single hour."""
    hour_start: float
    total_active_seconds: float = 0.0
    total_elapsed_seconds: float = 0.0
    target_seconds: float = 1800.0  # 30 minutes

    @property
    def uptime_pct(self) -> float:
        """Percentage of the hour with active quoting."""
        if self.total_elapsed_seconds == 0:
            return 0.0
        return min(self.total_active_seconds / 3600.0 * 100.0, 100.0)

    @property
    def target_met(self) -> bool:
        """Whether the uptime target is met."""
        return self.total_active_seconds >= self.target_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "hour_start": self.hour_start,
            "total_active_seconds": round(self.total_active_seconds, 2),
            "total_elapsed_seconds": round(self.total_elapsed_seconds, 2),
            "uptime_pct": round(self.uptime_pct, 2),
            "target_seconds": self.target_seconds,
            "target_met": self.target_met,
        }


class UptimeTracker:
    """
    Tracks maker uptime per hour.

    The bot is considered 'active' when it has BOTH bid and ask
    orders placed within the allowed spread deviation.
    """

    def __init__(self) -> None:
        self._target_seconds = settings.uptime_target_minutes * 60.0
        self._current_hour = self._get_current_hour()
        self._current_record = HourlyRecord(
            hour_start=self._current_hour,
            target_seconds=self._target_seconds,
        )
        self._history: deque[HourlyRecord] = deque(maxlen=24)
        self._last_tick: float = time.time()
        self._is_active = False

    @staticmethod
    def _get_current_hour() -> float:
        """Return the timestamp of the start of the current hour."""
        now = time.time()
        return now - (now % 3600)

    def tick(self, has_both_sides: bool) -> None:
        """
        Called every engine loop iteration.

        Args:
            has_both_sides: True if bot has both bid and ask orders active.
        """
        now = time.time()
        elapsed = now - self._last_tick
        self._last_tick = now

        # Check for hour rollover
        current_hour = self._get_current_hour()
        if current_hour != self._current_hour:
            self._rollover(current_hour)

        # Update current record
        self._current_record.total_elapsed_seconds += elapsed
        if has_both_sides:
            self._current_record.total_active_seconds += elapsed
            if not self._is_active:
                log.info("uptime.became_active")
                self._is_active = True
        else:
            if self._is_active:
                log.info("uptime.became_inactive")
                self._is_active = False

    def _rollover(self, new_hour: float) -> None:
        """Archive current hour and start a new record."""
        log.info(
            "uptime.hour_rollover",
            hour=self._current_hour,
            active_seconds=self._current_record.total_active_seconds,
            uptime_pct=self._current_record.uptime_pct,
            target_met=self._current_record.target_met,
        )
        self._history.append(self._current_record)
        self._current_hour = new_hour
        self._current_record = HourlyRecord(
            hour_start=new_hour,
            target_seconds=self._target_seconds,
        )

    @property
    def current_uptime_pct(self) -> float:
        """Current hour uptime percentage."""
        return self._current_record.uptime_pct

    @property
    def is_target_met(self) -> bool:
        """Whether the current hour target is met."""
        return self._current_record.target_met

    @property
    def seconds_remaining_for_target(self) -> float:
        """Seconds of active quoting still needed to meet target."""
        remaining = self._target_seconds - self._current_record.total_active_seconds
        return max(remaining, 0.0)

    @property
    def seconds_elapsed_in_hour(self) -> float:
        """Seconds elapsed in the current hour."""
        return time.time() - self._current_hour

    def get_stats(self) -> dict[str, Any]:
        """Return comprehensive uptime statistics."""
        return {
            "current_hour": {
                **self._current_record.to_dict(),
                "seconds_remaining_for_target": round(self.seconds_remaining_for_target, 2),
                "seconds_elapsed_in_hour": round(self.seconds_elapsed_in_hour, 2),
                "is_active": self._is_active,
            },
            "history": [r.to_dict() for r in self._history],
            "hours_target_met_last_24h": sum(
                1 for r in self._history if r.target_met
            ),
            "avg_uptime_pct_last_24h": round(
                sum(r.uptime_pct for r in self._history) / len(self._history)
                if self._history
                else 0.0,
                2,
            ),
        }


# Singleton
uptime_tracker = UptimeTracker()
