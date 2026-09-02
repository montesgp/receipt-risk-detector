"""CBU/CVU check-digit validation (Argentine bank account / virtual account
identifiers). 22 digits, two mod-10 blocks. Locked algorithm per the
proposal's "Locked technical decisions" table — do not re-derive.

Pure, I/O-free per `docs/ARCHITECTURE.md` §5.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

CBU_BLOCK1_WEIGHTS: Final[tuple[int, ...]] = (7, 1, 3, 9, 7, 1, 3)
CBU_BLOCK2_WEIGHTS: Final[tuple[int, ...]] = (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3)

_CBU_LENGTH: Final[int] = 22


class ChecksumFailure(StrEnum):
    NON_NUMERIC = "non_numeric"
    BAD_LENGTH = "bad_length"
    BLOCK1_CHECK_DIGIT = "block1_check_digit"
    BLOCK2_CHECK_DIGIT = "block2_check_digit"
    CHECK_DIGIT = "check_digit"


@dataclass(frozen=True, slots=True)
class ChecksumResult:
    is_valid: bool
    normalized: str | None = None
    failure: ChecksumFailure | None = None


def mod10_check_digit(digits: Sequence[int], weights: Sequence[int]) -> int:
    """DV = (10 - sum(d*w) % 10) % 10."""
    return (10 - sum(d * w for d, w in zip(digits, weights, strict=True)) % 10) % 10


def validate_cbu(raw: str) -> ChecksumResult:
    """22 digits: block1 = d[0:7] + DV d[7]; block2 = d[8:21] + DV d[21].

    Accepts both CBU and CVU, which share the identical 22-digit/two-block
    layout.
    """
    cleaned = raw.strip().replace(" ", "")
    if not cleaned.isdigit():
        return ChecksumResult(is_valid=False, failure=ChecksumFailure.NON_NUMERIC)
    if len(cleaned) != _CBU_LENGTH:
        return ChecksumResult(is_valid=False, failure=ChecksumFailure.BAD_LENGTH)

    digits = [int(c) for c in cleaned]

    block1_dv = mod10_check_digit(digits[0:7], CBU_BLOCK1_WEIGHTS)
    if block1_dv != digits[7]:
        return ChecksumResult(is_valid=False, failure=ChecksumFailure.BLOCK1_CHECK_DIGIT)

    block2_dv = mod10_check_digit(digits[8:21], CBU_BLOCK2_WEIGHTS)
    if block2_dv != digits[21]:
        return ChecksumResult(is_valid=False, failure=ChecksumFailure.BLOCK2_CHECK_DIGIT)

    return ChecksumResult(is_valid=True, normalized=cleaned)
