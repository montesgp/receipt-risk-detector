"""Tests for `domain/scoring.py::score`.

Traces to design.md's risk-score/evidence-coverage formulas and the locked
product decision that a failed analyzer never forces `INCONCLUSIVE` alone
(proposal.md).
"""

from __future__ import annotations

from decimal import Decimal

from receipt_risk.domain.analysis import AnalyzerResult, ExtractedField
from receipt_risk.domain.ruleset import Classification
from receipt_risk.domain.rulesets.v2026_09_04 import RULESET_2026_09_04
from receipt_risk.domain.scoring import score
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode, ValidationSignal


def _ocr_result(*, status="completed", extracted_fields=()) -> AnalyzerResult:
    return AnalyzerResult(
        analyzer="paddleocr-onnx", version="1.0.0", status=status, extracted_fields=extracted_fields
    )


def _metadata_result(status="completed") -> AnalyzerResult:
    return AnalyzerResult(analyzer="exiftool", version="1.0.0", status=status)


def _provenance_result(status="completed") -> AnalyzerResult:
    return AnalyzerResult(analyzer="c2pa", version="1.0.0", status=status)


def _all_core_fields() -> tuple[ExtractedField, ...]:
    return tuple(
        ExtractedField(name=name, raw_text="x", normalized="x", confidence=Decimal("0.90"))
        for name in ("amount", "destination_cbu", "cuit", "date_time")
    )


def test_risk_score_contribution_uses_decimal_weight_severity_confidence() -> None:
    signal = ValidationSignal(
        code=SignalCode.INVALID_CBU_CHECK_DIGIT,
        category=SignalCategory.FINANCIAL_CONSISTENCY,
        severity=Severity.HIGH,
        confidence=Decimal("1.00"),
        description="x",
    )
    results = [
        _ocr_result(extracted_fields=_all_core_fields()),
        _metadata_result(),
        _provenance_result(),
    ]
    breakdown = score([signal], results, RULESET_2026_09_04)
    # weight 40 * severity_multiplier(high)=1.5 * confidence 1.00 = 60
    assert breakdown.risk_score == 60


def test_risk_score_capped_at_100_and_raised_to_critical_floor_for_critical_signal() -> None:
    huge = ValidationSignal(
        code=SignalCode.INVALID_CBU_CHECK_DIGIT,
        category=SignalCategory.FINANCIAL_CONSISTENCY,
        severity=Severity.HIGH,
        confidence=Decimal("1.00"),
        description="x",
    )
    critical = ValidationSignal(
        code=SignalCode.VALID_AI_GENERATED_CLAIM,
        category=SignalCategory.PROVENANCE,
        severity=Severity.CRITICAL,
        confidence=Decimal("1.00"),
        description="x",
    )
    results = [
        _ocr_result(extracted_fields=_all_core_fields()),
        _metadata_result(),
        _provenance_result(),
    ]
    breakdown = score([huge, huge, huge, critical], results, RULESET_2026_09_04)
    assert breakdown.risk_score == 100

    breakdown_floor_only = score([critical], results, RULESET_2026_09_04)
    assert breakdown_floor_only.risk_score >= 85


def test_confidence_independent_of_risk_ocr_fails_others_succeed_not_inconclusive() -> None:
    results = [
        _ocr_result(status="failed"),
        _metadata_result(),
        _provenance_result(),
    ]
    breakdown = score([], results, RULESET_2026_09_04)
    # metadata 0.17 + provenance 0.25 = 0.42 (post-rebalance weights; ocr failed contributes 0)
    assert breakdown.evidence_coverage == Decimal("0.42")
    assert breakdown.confidence_score == 42
    assert breakdown.classification is not Classification.INCONCLUSIVE


def test_inconclusive_when_all_analyzers_fail_coverage_zero() -> None:
    results = [
        _ocr_result(status="failed"),
        _metadata_result(status="failed"),
        _provenance_result(status="failed"),
    ]
    breakdown = score([], results, RULESET_2026_09_04)
    assert breakdown.evidence_coverage == Decimal("0.00")
    assert breakdown.classification is Classification.INCONCLUSIVE


def _vision_result(status="completed") -> AnalyzerResult:
    return AnalyzerResult(analyzer="mobilenetv3-embedding", version="1.0.0", status=status)


def test_adapter_role_maps_mobilenetv3_embedding_to_vision() -> None:
    results = [
        _ocr_result(extracted_fields=_all_core_fields()),
        _metadata_result(),
        _provenance_result(),
        _vision_result(),
    ]
    breakdown = score([], results, RULESET_2026_09_04)
    # ocr 0.43 + metadata 0.17 + provenance 0.25 + vision 0.15, all completed = 1.00
    assert breakdown.evidence_coverage == Decimal("1.00")
    assert breakdown.confidence_score == 100

    results_no_vision = [
        _ocr_result(extracted_fields=_all_core_fields()),
        _metadata_result(),
        _provenance_result(),
        _vision_result(status="failed"),
    ]
    breakdown_no_vision = score([], results_no_vision, RULESET_2026_09_04)
    assert breakdown_no_vision.evidence_coverage == Decimal("0.85")


def test_deterministic_score_same_input_and_ruleset_twice_identical_triple() -> None:
    signal = ValidationSignal(
        code=SignalCode.DATE_OUT_OF_BOUNDS,
        category=SignalCategory.FINANCIAL_CONSISTENCY,
        severity=Severity.MEDIUM,
        confidence=Decimal("0.77"),
        description="x",
    )
    results = [
        _ocr_result(extracted_fields=_all_core_fields()),
        _metadata_result(),
        _provenance_result(),
    ]
    first = score([signal], results, RULESET_2026_09_04)
    second = score([signal], results, RULESET_2026_09_04)
    assert first == second
