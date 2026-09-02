"""Date plausibility bounds for extracted receipt dates.

A receipt-declared date far in the past or future relative to submission
time is itself suspicious. Pure, I/O-free per `docs/ARCHITECTURE.md` §5 —
the reference time is always passed in, never read from a clock here.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Final

DEFAULT_MAX_PAST_DAYS: Final[int] = 365
DEFAULT_MAX_FUTURE_DAYS: Final[int] = 1


def is_within_date_bounds(
    extracted: datetime,
    *,
    reference: datetime,
    max_past_days: int = DEFAULT_MAX_PAST_DAYS,
    max_future_days: int = DEFAULT_MAX_FUTURE_DAYS,
) -> bool:
    """Return whether `extracted` falls within `[reference - max_past_days,
    reference + max_future_days]`."""
    lower_bound = reference - timedelta(days=max_past_days)
    upper_bound = reference + timedelta(days=max_future_days)
    return lower_bound <= extracted <= upper_bound
