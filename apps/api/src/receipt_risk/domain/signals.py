"""Domain signal vocabulary: categories, severities, and validation signals.

Pure, I/O-free per `docs/ARCHITECTURE.md` §5. Signal codes are extended by
later slices (2, 3, 4); slice 1 defines only the shared base enums that
`domain/analysis.py` depends on.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class SignalCategory(StrEnum):
    METADATA = "metadata"
    PROVENANCE = "provenance"
    FINANCIAL_CONSISTENCY = "financial_consistency"
    DATA_QUALITY = "data_quality"


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SignalCode(StrEnum):
    """Signal code vocabulary. Slice 1 defines no codes of its own; codes are
    added here by slices 2 (metadata/provenance), 3 (financial), and 4
    (analyzer availability)."""

    # slice 2
    METADATA_EDITOR_SOFTWARE = "METADATA_EDITOR_SOFTWARE"
    VALID_AI_GENERATED_CLAIM = "VALID_AI_GENERATED_CLAIM"
    PROVENANCE_VALIDATION_FAILED = "PROVENANCE_VALIDATION_FAILED"
    # slice 3
    INVALID_CBU_CHECK_DIGIT = "INVALID_CBU_CHECK_DIGIT"
    INVALID_CUIT_CHECK_DIGIT = "INVALID_CUIT_CHECK_DIGIT"
    AMOUNT_DATE_CONTRADICTION = "AMOUNT_DATE_CONTRADICTION"
    DATE_OUT_OF_BOUNDS = "DATE_OUT_OF_BOUNDS"
    CORE_FIELD_EXTRACTION_FAILED = "CORE_FIELD_EXTRACTION_FAILED"  # category DATA_QUALITY


class ExtractionFailureReason(StrEnum):
    """Why a core field (amount, CBU/CVU, CUIT/CUIL, date) could not be
    extracted. Consumed by `CORE_FIELD_EXTRACTION_FAILED` signals — emitted
    by the OCR adapter in slice 3b, defined here alongside the signal codes
    it accompanies."""

    LOW_CONFIDENCE = "low_confidence"
    NO_TEXT_DETECTED = "no_text_detected"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class ValidationSignal:
    code: SignalCode
    category: SignalCategory
    severity: Severity
    confidence: Decimal
    description: str
    evidence: Mapping[str, str] = field(default_factory=dict)
    score_contribution: int = 0
