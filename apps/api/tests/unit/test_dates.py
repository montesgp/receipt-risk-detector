"""Unit tests for `domain.financial.dates` — date plausibility bounds.

Traces to spec.md "Financial validation" (FR-006): a receipt-declared date
far outside a configured plausibility window relative to a reference time
is itself suspicious.
"""

from __future__ import annotations

from datetime import UTC, datetime

from receipt_risk.domain.financial.dates import is_within_date_bounds


def test_date_out_of_bounds_flagged_outside_configured_window() -> None:
    reference = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    too_old = datetime(2020, 1, 1, tzinfo=UTC)
    too_future = datetime(2027, 1, 1, tzinfo=UTC)

    assert is_within_date_bounds(too_old, reference=reference) is False
    assert is_within_date_bounds(too_future, reference=reference) is False


def test_date_within_default_window_is_accepted() -> None:
    reference = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    plausible = datetime(2026, 8, 30, 9, 0, tzinfo=UTC)

    assert is_within_date_bounds(plausible, reference=reference) is True


def test_date_bounds_respect_custom_window() -> None:
    reference = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    ten_days_ago = datetime(2026, 8, 22, 12, 0, tzinfo=UTC)

    assert is_within_date_bounds(ten_days_ago, reference=reference, max_past_days=5) is False
    assert is_within_date_bounds(ten_days_ago, reference=reference, max_past_days=15) is True
