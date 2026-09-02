"""Unit tests for `domain.financial.cuit` — CUIT/CUIL check-digit validation.

Traces to spec.md "Financial validation" (FR-006) and the proposal's locked
CUIT/CUIL algorithm: 11 digits, mod 11, weights `[5,4,3,2,7,6,5,4,3,2]` on
the first 10 digits; result `11 -> 0`, result `10 -> invalid`. Known-answer
fixture from the proposal: `20-17254359-7` (check digit 7).
"""

from __future__ import annotations

from receipt_risk.domain.financial.cbu import ChecksumFailure
from receipt_risk.domain.financial.cuit import validate_cuit


def test_validate_cuit_known_answer() -> None:
    # sum = 136; 136 % 11 == 4; 11 - 4 == 7 == declared check digit
    assert validate_cuit("20-17254359-7").is_valid is True
    assert validate_cuit("20172543597").normalized == "20172543597"


def test_validate_cuit_rejects_wrong_check_digit() -> None:
    result = validate_cuit("20-17254359-8")

    assert result.is_valid is False
    assert result.failure is ChecksumFailure.CHECK_DIGIT


def test_validate_cuit_rejects_non_numeric() -> None:
    result = validate_cuit("20-1725435X-7")

    assert result.is_valid is False
    assert result.failure is ChecksumFailure.NON_NUMERIC


def test_validate_cuit_rejects_wrong_length() -> None:
    result = validate_cuit("20-1725435-7")

    assert result.is_valid is False
    assert result.failure is ChecksumFailure.BAD_LENGTH
