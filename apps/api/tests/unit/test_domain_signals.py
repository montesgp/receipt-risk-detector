"""Unit tests for `domain.signals`'s slice-2 signal vocabulary.

Traces to spec.md scenarios "Missing metadata is neutral" and "Valid
AI-generated provenance claim", and to AGENTS.md's MVP1 invariant that a
valid AI-generation provenance claim alone is a critical risk signal.
"""

from __future__ import annotations

from decimal import Decimal

from receipt_risk.domain.signals import (
    ExtractionFailureReason,
    Severity,
    SignalCategory,
    SignalCode,
    ValidationSignal,
)


def test_metadata_editor_software_signal_shape() -> None:
    signal = ValidationSignal(
        code=SignalCode.METADATA_EDITOR_SOFTWARE,
        category=SignalCategory.METADATA,
        severity=Severity.LOW,
        confidence=Decimal("0.80"),
        description="Embedded metadata names editing software.",
        evidence={"software": "adobe photoshop"},
    )

    assert signal.code == SignalCode.METADATA_EDITOR_SOFTWARE
    assert signal.category == SignalCategory.METADATA
    assert signal.evidence == {"software": "adobe photoshop"}


def test_valid_ai_generated_claim_signal_is_critical_severity() -> None:
    signal = ValidationSignal(
        code=SignalCode.VALID_AI_GENERATED_CLAIM,
        category=SignalCategory.PROVENANCE,
        severity=Severity.CRITICAL,
        confidence=Decimal("1.00"),
        description="A valid C2PA manifest declares algorithmic generation.",
        evidence={"active_manifest": "urn:uuid:abc"},
    )

    assert signal.severity == Severity.CRITICAL
    assert signal.code == SignalCode.VALID_AI_GENERATED_CLAIM
    assert signal.category == SignalCategory.PROVENANCE


def test_slice_3_financial_signal_codes_exist() -> None:
    assert SignalCode.INVALID_CBU_CHECK_DIGIT == "INVALID_CBU_CHECK_DIGIT"
    assert SignalCode.INVALID_CUIT_CHECK_DIGIT == "INVALID_CUIT_CHECK_DIGIT"
    assert SignalCode.AMOUNT_DATE_CONTRADICTION == "AMOUNT_DATE_CONTRADICTION"
    assert SignalCode.DATE_OUT_OF_BOUNDS == "DATE_OUT_OF_BOUNDS"
    assert SignalCode.CORE_FIELD_EXTRACTION_FAILED == "CORE_FIELD_EXTRACTION_FAILED"


def test_extraction_failure_reason_enum_values() -> None:
    assert ExtractionFailureReason.LOW_CONFIDENCE == "low_confidence"
    assert ExtractionFailureReason.NO_TEXT_DETECTED == "no_text_detected"
    assert ExtractionFailureReason.TIMEOUT == "timeout"
