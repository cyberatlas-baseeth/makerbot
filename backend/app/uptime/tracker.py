"""
Dual uptime tracker — maker vs market-maker.

Two independent counters per hour:
  • maker_uptime   — counted only when configured spread ≤ 5 bps
                     (StandX maker eligibility)
  • mm_uptime      — counted when spread > 5 bps
                     (wider market-making, not eligible)

tick() is called every engine loop with:
  - has_both_sides: whether bid+ask are both on the book
  - spread_bps: the configured spread at that moment

Automatically resets on the hour boundary.
Stores history for the last 24 hours.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

from app.config import settings
from app.logger import get_logger

log = get_logger("uptime")

# Spread threshold — at or below this, time counts as "maker"
MAKER_MAX_SPREAD_BPS = 5.0


@dataclass
class HourlyRecord:
    """Record for a single hour with dual counters."""
    hour_start: float
    maker_active_seconds: float = 0.0     # spread ≤ 5 bps
    mm_active_seconds: float = 0.0        # spread > 5 bps
    total_elapsed_seconds: float = 0.0
    target_seconds: float = 1800.0        # 30 minutes

    @property
    def maker_uptime_pct(self) -> float:
        """Maker uptime as percentage of the full hour (3600s)."""
        return min(self.maker_active_seconds / 3600.0 * 100.0, 100.0)

    @property
    def mm_uptime_pct(self) -> float:
        """Market-maker uptime as percentage of the full hour."""
        return min(self.mm_active_seconds / 3600.0 * 100.0, 100.0)

    @property
    def maker_target_met(self) -> bool:
        return self.maker_active_seconds >= self.target_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "hour_start": self.hour_start,
            "maker_active_seconds": round(self.maker_active_seconds, 2),
            "mm_active_seconds": round(self.mm_active_seconds, 2),
            "total_elapsed_seconds": round(self.total_elapsed_seconds, 2),
            "maker_uptime_pct": round(self.maker_uptime_pct, 2),
            "mm_uptime_pct": round(self.mm_uptime_pct, 2),
            "target_seconds": self.target_seconds,
            "maker_target_met": self.maker_target_met,
        }


class UptimeTracker:
    """
    Tracks dual uptime per hour.

    maker_uptime — both sides active AND spread ≤ 5 bps
    mm_uptime    — both sides active AND spread > 5 bps
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

    def reset(self) -> None:
        """Reset all uptime data. Used on symbol switch."""
        self._current_hour = self._get_current_hour()
        self._current_record = HourlyRecord(
            hour_start=self._current_hour,
            target_seconds=self._target_seconds,
        )
        self._history.clear()
        self._last_tick = time.time()
        self._is_active = False
        log.info("uptime.reset")

    @staticmethod
    def _get_current_hour() -> float:
        """Return the timestamp of the start of the current hour."""
        now = time.time()
        return now - (now % 3600)

    def tick(self, has_both_sides: bool, spread_bps: float = 0.0) -> None:
        """
        Called every engine loop iteration.

        Args:
            has_both_sides: True if bot has both bid and ask orders active.
            spread_bps: The configured spread at this moment.
        """
        now = time.time()
        elapsed = now - self._last_tick

        # Cap elapsed to prevent huge jumps (e.g. after sleep/suspend)
        elapsed = min(elapsed, 10.0)

        self._last_tick = now

        # Check for hour rollover
        current_hour = self._get_current_hour()
        if current_hour != self._current_hour:
            self._rollover(current_hour)

        # Update current record
        self._current_record.total_elapsed_seconds += elapsed

        if has_both_sides:
            if spread_bps <= MAKER_MAX_SPREAD_BPS:
                self._current_record.maker_active_seconds += elapsed
            else:
                self._current_record.mm_active_seconds += elapsed

            if not self._is_active:
                log.info("uptime.became_active", spread_bps=spread_bps)
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
            maker_seconds=self._current_record.maker_active_seconds,
            mm_seconds=self._current_record.mm_active_seconds,
            maker_pct=self._current_record.maker_uptime_pct,
            mm_pct=self._current_record.mm_uptime_pct,
            maker_target_met=self._current_record.maker_target_met,
        )
        self._history.append(self._current_record)
        self._current_hour = new_hour
        self._current_record = HourlyRecord(
            hour_start=new_hour,
            target_seconds=self._target_seconds,
        )

    @property
    def current_maker_uptime_pct(self) -> float:
        return self._current_record.maker_uptime_pct

    @property
    def current_mm_uptime_pct(self) -> float:
        return self._current_record.mm_uptime_pct

    @property
    def is_maker_target_met(self) -> bool:
        return self._current_record.maker_target_met

    @property
    def seconds_remaining_for_target(self) -> float:
        remaining = self._target_seconds - self._current_record.maker_active_seconds
        return max(remaining, 0.0)

    @property
    def seconds_elapsed_in_hour(self) -> float:
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
                1 for r in self._history if r.maker_target_met
            ),
            "avg_maker_uptime_pct_last_24h": round(
                sum(r.maker_uptime_pct for r in self._history) / len(self._history)
                if self._history
                else 0.0,
                2,
            ),
            "avg_mm_uptime_pct_last_24h": round(
                sum(r.mm_uptime_pct for r in self._history) / len(self._history)
                if self._history
                else 0.0,
                2,
            ),
        }


# Singleton
uptime_tracker = UptimeTracker()
