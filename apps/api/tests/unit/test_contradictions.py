"""Unit tests for `domain.financial.contradictions` — internal
contradiction detection between extracted fields.

Traces to spec.md "Financial validation" (FR-006): when OCR extracts two
occurrences of the same logical field (e.g. an amount printed twice on the
receipt) that disagree after normalization, that disagreement is itself a
suspicious signal, not something to silently average or discard.
"""

from __future__ import annotations

from decimal import Decimal

from receipt_risk.domain.analysis import ExtractedField
from receipt_risk.domain.financial.contradictions import detect_contradictions


def test_amount_date_contradiction_detected() -> None:
    fields = (
        ExtractedField(
            name="amount", raw_text="125.000,00", normalized="125000.00", confidence=Decimal("0.90")
        ),
        ExtractedField(
            name="amount", raw_text="120.000,00", normalized="120000.00", confidence=Decimal("0.85")
        ),
        ExtractedField(
            name="date_time",
            raw_text="2026-09-01",
            normalized="2026-09-01T14:43:00-03:00",
            confidence=Decimal("0.95"),
        ),
    )

    contradictions = detect_contradictions(fields)

    assert "amount" in contradictions
    assert "date_time" not in contradictions


def test_no_contradiction_when_all_occurrences_agree() -> None:
    fields = (
        ExtractedField(
            name="amount", raw_text="125.000,00", normalized="125000.00", confidence=Decimal("0.90")
        ),
        ExtractedField(
            name="amount", raw_text="125000.00", normalized="125000.00", confidence=Decimal("0.85")
        ),
    )

    assert detect_contradictions(fields) == []


def test_unnormalized_fields_are_ignored() -> None:
    fields = (
        ExtractedField(
            name="amount", raw_text="illegible", normalized=None, confidence=Decimal("0.10")
        ),
        ExtractedField(
            name="amount", raw_text="illegible", normalized=None, confidence=Decimal("0.10")
        ),
    )

    assert detect_contradictions(fields) == []
