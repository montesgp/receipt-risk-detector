"""Tests for `domain/assessment.py::assemble` and `FraudAssessment`."""

from __future__ import annotations

from decimal import Decimal

from receipt_risk.domain.analysis import AnalyzerResult, ExtractedField
from receipt_risk.domain.assessment import assemble
from receipt_risk.domain.ruleset import Classification, RecommendedAction
from receipt_risk.domain.rulesets.v2026_09_04 import RULESET_2026_09_04
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode, ValidationSignal


def _core_fields() -> tuple[ExtractedField, ...]:
    # A successful OCR run with all core fields extracted -- the OCR-zero
    # floor (scoring-confidence-calibration change) forces INCONCLUSIVE only
    # when OCR extracts zero core fields, so a "clean successful analysis"
    # fixture must carry at least one to stay distinguishable from that case.
    return tuple(
        ExtractedField(name=name, raw_text="x", normalized="x", confidence=Decimal("0.90"))
        for name in ("amount", "destination_cbu", "cuit", "date_time")
    )


def _results() -> list[AnalyzerResult]:
    return [
        AnalyzerResult(
            analyzer="paddleocr-onnx",
            version="1.0.0",
            status="completed",
            extracted_fields=_core_fields(),
        ),
        AnalyzerResult(analyzer="exiftool", version="1.0.0", status="completed"),
        AnalyzerResult(analyzer="c2pa", version="1.0.0", status="completed"),
    ]


def test_fraud_assessment_includes_ruleset_version_and_engine_version() -> None:
    assessment = assemble(
        analysis_id="sha256:deadbeef",
        results=_results(),
        signals=[],
        ruleset=RULESET_2026_09_04,
        engine_version="0.1.0",
        duration_ms=1234,
    )
    assert assessment.ruleset_version == "2026-09-04"
    assert assessment.engine_version == "0.1.0"
    assert assessment.analysis_id == "sha256:deadbeef"
    assert assessment.duration_ms == 1234
    assert assessment.classification is Classification.LOW_RISK
    assert assessment.recommended_action is RecommendedAction.STANDARD_MANUAL_RECONCILIATION


def test_recommended_action_maps_high_risk_to_do_not_rely() -> None:
    critical = ValidationSignal(
        code=SignalCode.VALID_AI_GENERATED_CLAIM,
        category=SignalCategory.PROVENANCE,
        severity=Severity.CRITICAL,
        confidence=Decimal("1.00"),
        description="x",
    )
    assessment = assemble(
        analysis_id="sha256:x",
        results=_results(),
        signals=[critical],
        ruleset=RULESET_2026_09_04,
        engine_version="0.1.0",
        duration_ms=1,
    )
    assert assessment.classification is Classification.HIGH_RISK
    assert assessment.recommended_action is RecommendedAction.DO_NOT_RELY_ON_RECEIPT


def test_recommended_action_maps_inconclusive_to_priority_reconciliation() -> None:
    failed_results = [
        AnalyzerResult(analyzer="paddleocr-onnx", version="1.0.0", status="failed"),
        AnalyzerResult(analyzer="exiftool", version="1.0.0", status="failed"),
        AnalyzerResult(analyzer="c2pa", version="1.0.0", status="failed"),
    ]
    assessment = assemble(
        analysis_id="sha256:x",
        results=failed_results,
        signals=[],
        ruleset=RULESET_2026_09_04,
        engine_version="0.1.0",
        duration_ms=1,
    )
    assert assessment.classification is Classification.INCONCLUSIVE
    assert assessment.recommended_action is RecommendedAction.PRIORITY_MANUAL_RECONCILIATION


def test_signal_score_contribution_is_filled_by_the_scorer() -> None:
    signal = ValidationSignal(
        code=SignalCode.INVALID_CBU_CHECK_DIGIT,
        category=SignalCategory.FINANCIAL_CONSISTENCY,
        severity=Severity.HIGH,
        confidence=Decimal("1.00"),
        description="x",
    )
    assessment = assemble(
        analysis_id="sha256:x",
        results=_results(),
        signals=[signal],
        ruleset=RULESET_2026_09_04,
        engine_version="0.1.0",
        duration_ms=1,
    )
    assert assessment.signals[0].score_contribution == 60


def test_limitations_always_present() -> None:
    assessment = assemble(
        analysis_id="sha256:x",
        results=_results(),
        signals=[],
        ruleset=RULESET_2026_09_04,
        engine_version="0.1.0",
        duration_ms=1,
    )
    assert len(assessment.limitations) >= 1
