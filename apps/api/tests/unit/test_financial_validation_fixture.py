"""Manifest-driven fixture test for `validate_financials()`.

Traces to spec.md "Invalid CBU check digit" (FR-006) and the
`invalid_cbu_check_digit` fixture's `expected_signals` in
`samples/manifest.json`. Uses `conftest.py::fixture()` per design.md's
fixture-manifest contract — declared_fields feed `validate_financials()`
directly, exactly as the OCR adapter would in the full pipeline (slice 3b).
"""

from __future__ import annotations

from decimal import Decimal

from conftest import fixture
from receipt_risk.application.financial_validation import validate_financials
from receipt_risk.domain.analysis import ExtractedField
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode


def test_invalid_cbu_fixture_produces_expected_signal() -> None:
    manifest_fixture = fixture("invalid_cbu_check_digit")
    declared = manifest_fixture.declared_fields

    fields = tuple(
        ExtractedField(name=name, raw_text=value, normalized=value, confidence=Decimal("0.95"))
        for name, value in declared.items()
    )

    signals = validate_financials(fields)

    assert len(manifest_fixture.expected_signals) == 1
    expected = manifest_fixture.expected_signals[0]
    matching = [s for s in signals if s.code == expected["code"]]

    assert matching, (
        f"expected signal {expected['code']!r} not produced; got {[s.code for s in signals]}"
    )
    assert matching[0].code == SignalCode.INVALID_CBU_CHECK_DIGIT
    assert matching[0].category == SignalCategory(expected["category"])
    assert matching[0].severity == Severity(expected["severity"])
