"""Unit tests for `domain.financial.money` — ARS amount normalization.

Traces to spec.md "Financial validation" (FR-006): monetary normalization
of already-extracted OCR text into a comparable `Decimal`.
"""

from __future__ import annotations

from decimal import Decimal

from receipt_risk.domain.financial.money import normalize_amount


def test_ars_amount_normalization_handles_thousands_and_decimal_separators() -> None:
    # AR locale: '.' groups thousands, ',' is the decimal separator.
    assert normalize_amount("125.000,00") == Decimal("125000.00")
    # Plain format: '.' is already the decimal separator.
    assert normalize_amount("125000.00") == Decimal("125000.00")
    # US-style thousands with a decimal comma-free value.
    assert normalize_amount("1,250.50") == Decimal("1250.50")


def test_normalize_amount_strips_currency_symbols_and_whitespace() -> None:
    assert normalize_amount("$ 125.000,00") == Decimal("125000.00")
    assert normalize_amount("ARS 125000,00") == Decimal("125000.00")


def test_normalize_amount_returns_none_for_unparseable_text() -> None:
    assert normalize_amount("") is None
    assert normalize_amount("not a number") is None
