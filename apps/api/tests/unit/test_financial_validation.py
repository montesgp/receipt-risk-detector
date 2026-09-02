"""Unit tests for `application.financial_validation` — orchestrates all
domain financial validators over a set of already-extracted OCR fields.

Traces to spec.md "Invalid CBU check digit" (FR-006) and design.md's
`validate_financials()` contract: pure over `Sequence[ExtractedField]`,
never touches I/O, and masks any evidence carrying financial values (never
raw CBU/CUIT/amount — data-retention log-masking scenario).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from receipt_risk.application.financial_validation import validate_financials
from receipt_risk.domain.analysis import ExtractedField
from receipt_risk.domain.signals import SignalCode


def _field(name: str, raw: str, normalized: str | None, confidence: str = "0.90") -> ExtractedField:
    return ExtractedField(
        name=name, raw_text=raw, normalized=normalized, confidence=Decimal(confidence)
    )


def test_validate_financials_runs_all_validators_over_extracted_fields() -> None:
    reference = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    fields = (
        _field("destination_cbu", "2850590940090418135202", "2850590940090418135202"),
        _field("cuit", "20-17254359-8", "20172543598"),
        _field("date_time", "2020-01-01", "2020-01-01T00:00:00-03:00"),
        _field("amount", "125.000,00", "125000.00"),
        _field("amount", "120.000,00", "120000.00"),
    )

    signals = validate_financials(fields, reference=reference)
    codes = {s.code for s in signals}

    assert SignalCode.INVALID_CBU_CHECK_DIGIT in codes
    assert SignalCode.INVALID_CUIT_CHECK_DIGIT in codes
    assert SignalCode.DATE_OUT_OF_BOUNDS in codes
    assert SignalCode.AMOUNT_DATE_CONTRADICTION in codes


def test_validate_financials_returns_no_signals_for_all_valid_fields() -> None:
    reference = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    fields = (
        _field("destination_cbu", "2850590940090418135201", "2850590940090418135201"),
        _field("cuit", "20-17254359-7", "20172543597"),
        _field("date_time", "2026-08-30", "2026-08-30T14:43:00-03:00"),
        _field("amount", "125.000,00", "125000.00"),
    )

    assert validate_financials(fields, reference=reference) == []


def test_validate_financials_evidence_never_carries_raw_financial_values() -> None:
    reference = datetime(2026, 9, 1, tzinfo=UTC)
    fields = (_field("destination_cbu", "2850590940090418135202", "2850590940090418135202"),)

    signals = validate_financials(fields, reference=reference)
    cbu_signal = next(s for s in signals if s.code == SignalCode.INVALID_CBU_CHECK_DIGIT)

    for value in cbu_signal.evidence.values():
        assert "2850590940090418135202" not in value


def test_validate_financials_ignores_missing_fields() -> None:
    assert validate_financials((), reference=datetime(2026, 9, 1, tzinfo=UTC)) == []
