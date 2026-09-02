"""CUIT/CUIL check-digit validation (Argentine tax ID). 11 digits, mod 11.
Locked algorithm per the proposal's "Locked technical decisions" table — do
not re-derive.

Pure, I/O-free per `docs/ARCHITECTURE.md` §5.
"""

from __future__ import annotations

from typing import Final

from receipt_risk.domain.financial.cbu import ChecksumFailure, ChecksumResult

CUIT_WEIGHTS: Final[tuple[int, ...]] = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)

_CUIT_LENGTH: Final[int] = 11
_INVALID_REMAINDER_CHECK_DIGIT: Final[int] = 10
_MODULUS: Final[int] = 11


def validate_cuit(raw: str) -> ChecksumResult:
    """11 digits (hyphens/spaces stripped). dv = 11 - sum(d*w) % 11; 11 -> 0;
    10 -> invalid."""
    cleaned = raw.strip().replace("-", "").replace(" ", "")
    if not cleaned.isdigit():
        return ChecksumResult(is_valid=False, failure=ChecksumFailure.NON_NUMERIC)
    if len(cleaned) != _CUIT_LENGTH:
        return ChecksumResult(is_valid=False, failure=ChecksumFailure.BAD_LENGTH)

    digits = [int(c) for c in cleaned]
    total = sum(d * w for d, w in zip(digits[:10], CUIT_WEIGHTS, strict=True))
    check_digit = _MODULUS - (total % _MODULUS)
    if check_digit == _MODULUS:
        check_digit = 0
    if check_digit == _INVALID_REMAINDER_CHECK_DIGIT or check_digit != digits[10]:
        return ChecksumResult(is_valid=False, failure=ChecksumFailure.CHECK_DIGIT)

    return ChecksumResult(is_valid=True, normalized=cleaned)
