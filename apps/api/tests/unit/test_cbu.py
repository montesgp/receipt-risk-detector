"""Unit tests for `domain.financial.cbu` — CBU/CVU check-digit validation.

Traces to spec.md "Invalid CBU check digit" (FR-006) and the proposal's
locked CBU/CVU algorithm: 22 digits, two mod-10 blocks, weights
`[7,1,3,9,7,1,3]` (block 1) / `[3,9,7,1,3,9,7,1,3,9,7,1,3]` (block 2),
`DV = (10 - sum % 10) % 10`. Known-answer fixture from the proposal:
`2850590940090418135201` (DV1=9, DV2=1).
"""

from __future__ import annotations

from receipt_risk.domain.financial.cbu import (
    CBU_BLOCK1_WEIGHTS,
    CBU_BLOCK2_WEIGHTS,
    ChecksumFailure,
    ChecksumResult,
    mod10_check_digit,
    validate_cbu,
)


def test_cbu_known_answer_block_digits() -> None:
    digits = [int(c) for c in "2850590940090418135201"]
    assert mod10_check_digit(digits[0:7], CBU_BLOCK1_WEIGHTS) == 9  # equals digits[7]
    assert mod10_check_digit(digits[8:21], CBU_BLOCK2_WEIGHTS) == 1  # equals digits[21]


def test_validate_cbu_accepts_known_valid() -> None:
    assert validate_cbu("2850590940090418135201") == ChecksumResult(
        is_valid=True, normalized="2850590940090418135201"
    )


def test_validate_cbu_rejects_mutated_block2_check_digit() -> None:
    result = validate_cbu("2850590940090418135202")

    assert result.is_valid is False
    assert result.failure is ChecksumFailure.BLOCK2_CHECK_DIGIT


def test_validate_cbu_rejects_mutated_block1_check_digit() -> None:
    result = validate_cbu("2850590040090418135201")

    assert result.is_valid is False
    assert result.failure is ChecksumFailure.BLOCK1_CHECK_DIGIT


def test_validate_cbu_rejects_non_numeric() -> None:
    result = validate_cbu("285059094009041813520A")

    assert result.is_valid is False
    assert result.failure is ChecksumFailure.NON_NUMERIC


def test_validate_cbu_rejects_wrong_length() -> None:
    result = validate_cbu("28505909400904181352")

    assert result.is_valid is False
    assert result.failure is ChecksumFailure.BAD_LENGTH
