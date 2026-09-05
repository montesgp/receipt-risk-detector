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


def _provenance_result(status="completed", evidence_observed=None) -> AnalyzerResult:
    return AnalyzerResult(
        analyzer="c2pa", version="1.0.0", status=status, evidence_observed=evidence_observed
    )


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


def test_completeness_provenance_evidence_observed_false_returns_zero() -> None:
    """`_completeness` for a non-ocr role must not equate `status ==
    'completed'` with real evidence: a clean C2PA run that observed no
    manifest (`evidence_observed=False`) contributes zero coverage."""
    from receipt_risk.domain.scoring import _completeness

    completed_no_manifest = _provenance_result(evidence_observed=False)
    assert _completeness("provenance", completed_no_manifest) == Decimal("0")


def test_completeness_vision_and_metadata_unchanged_at_one_when_completed() -> None:
    from receipt_risk.domain.scoring import _completeness

    assert _completeness("vision", _vision_result()) == Decimal("1")
    assert _completeness("metadata", _metadata_result()) == Decimal("1")
    # provenance with evidence_observed=True (or unreported/None) stays 1
    assert _completeness("provenance", _provenance_result(evidence_observed=True)) == Decimal("1")
    assert _completeness("provenance", _provenance_result(evidence_observed=None)) == Decimal("1")


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


def test_ocr_zero_core_fields_forces_inconclusive_even_above_coverage_threshold() -> None:
    """Fixture (a): zero-OCR core fields + no C2PA manifest. metadata 0.17 +
    vision 0.15 = 0.32 evidence coverage — this alone is already below the
    0.35 threshold, but the OCR-zero floor must force INCONCLUSIVE
    independently of the coverage gate."""
    results = [
        _ocr_result(extracted_fields=()),
        _metadata_result(),
        _provenance_result(evidence_observed=False),
        _vision_result(),
    ]
    breakdown = score([], results, RULESET_2026_09_04)
    assert breakdown.evidence_coverage == Decimal("0.32")
    assert breakdown.classification is Classification.INCONCLUSIVE


def test_legitimate_low_quality_receipt_partial_ocr_no_c2pa_not_forced_inconclusive() -> None:
    """Fixture (b): real receipt, 1/4 core fields extracted, no C2PA
    manifest -> coverage 0.43. Regression guard for the top design risk:
    this must NOT be forced INCONCLUSIVE by the new OCR-zero floor, since
    OCR completeness is > 0 here."""
    one_core_field = (
        ExtractedField(name="amount", raw_text="x", normalized="x", confidence=Decimal("0.90")),
    )
    results = [
        _ocr_result(extracted_fields=one_core_field),
        _metadata_result(),
        _provenance_result(evidence_observed=False),
        _vision_result(),
    ]
    breakdown = score([], results, RULESET_2026_09_04)
    assert breakdown.evidence_coverage == Decimal("0.43")
    assert breakdown.classification is not Classification.INCONCLUSIVE


def test_ocr_zero_floor_fires_even_when_coverage_is_above_threshold() -> None:
    """The OCR-zero floor is a distinct mechanism from the coverage gate: a
    manifest-carrying image with zero readable core fields pushes coverage
    to 0.57 (above the 0.35 threshold), but must still be forced
    INCONCLUSIVE absent a verdict-grade signal."""
    results = [
        _ocr_result(extracted_fields=()),
        _metadata_result(),
        _provenance_result(evidence_observed=True),
        _vision_result(),
    ]
    breakdown = score([], results, RULESET_2026_09_04)
    assert breakdown.evidence_coverage == Decimal("0.57")
    assert breakdown.classification is Classification.INCONCLUSIVE


def test_combination_floor_fires_only_when_both_signals_co_occur() -> None:
    """Fixture (c): both CORE_FIELD_EXTRACTION_FAILED and DATE_OUT_OF_BOUNDS
    fired -> risk_score floors at 55 under v2026_09_05; each alone leaves
    the score unchanged (no floor triggered); an empty `combination_floors`
    mapping (v2026_09_04) is a no-op even with both signals present."""
    from receipt_risk.domain.rulesets.v2026_09_05 import RULESET_2026_09_05

    extraction_failed = ValidationSignal(
        code=SignalCode.CORE_FIELD_EXTRACTION_FAILED,
        category=SignalCategory.DATA_QUALITY,
        severity=Severity.MEDIUM,
        confidence=Decimal("1.00"),
        description="x",
    )
    date_out_of_bounds = ValidationSignal(
        code=SignalCode.DATE_OUT_OF_BOUNDS,
        category=SignalCategory.FINANCIAL_CONSISTENCY,
        severity=Severity.MEDIUM,
        confidence=Decimal("1.00"),
        description="x",
    )
    results = [
        _ocr_result(extracted_fields=_all_core_fields()),
        _metadata_result(),
        _provenance_result(evidence_observed=True),
        _vision_result(),
    ]

    both = score([extraction_failed, date_out_of_bounds], results, RULESET_2026_09_05)
    assert both.risk_score == 55

    extraction_only = score([extraction_failed], results, RULESET_2026_09_05)
    assert extraction_only.risk_score < 55

    date_only = score([date_out_of_bounds], results, RULESET_2026_09_05)
    assert date_only.risk_score < 55

    # Same both-signals input under the OLD ruleset (empty combination_floors) is a no-op.
    both_old_ruleset = score([extraction_failed, date_out_of_bounds], results, RULESET_2026_09_04)
    assert both_old_ruleset.risk_score == extraction_only.risk_score + date_only.risk_score


def test_v2026_09_01_and_v2026_09_04_reproducible_under_shared_engine_fix() -> None:
    """Fixture (e): historical rulesets stay byte-identical for inputs that
    predate the OCR-zero floor and combination floor (both engine-level
    additions gated to fire only where applicable) — only the shared
    `_completeness` fix applies retroactively, and it does here too since
    both results below carry a manifest (`evidence_observed=True`), so
    `_completeness` returns the same `1` it always did."""
    from receipt_risk.domain.rulesets.v2026_09_01 import RULESET_2026_09_01

    results = [
        _ocr_result(extracted_fields=_all_core_fields()),
        _metadata_result(),
        _provenance_result(evidence_observed=True),
    ]
    signal = ValidationSignal(
        code=SignalCode.DATE_OUT_OF_BOUNDS,
        category=SignalCategory.FINANCIAL_CONSISTENCY,
        severity=Severity.MEDIUM,
        confidence=Decimal("0.77"),
        description="x",
    )
    breakdown_01 = score([signal], results, RULESET_2026_09_01)
    breakdown_04 = score([signal], results, RULESET_2026_09_04)
    assert breakdown_01.evidence_coverage == Decimal("1.00")
    assert breakdown_04.evidence_coverage == Decimal("0.85")


def test_ocr_zero_with_valid_ai_generated_claim_stays_high_risk_not_downgraded() -> None:
    """A verdict-grade CRITICAL signal with a `critical_floor` entry
    overrides the OCR-zero floor: cryptographic provenance evidence must
    never be downgraded to INCONCLUSIVE just because OCR found nothing."""
    critical = ValidationSignal(
        code=SignalCode.VALID_AI_GENERATED_CLAIM,
        category=SignalCategory.PROVENANCE,
        severity=Severity.CRITICAL,
        confidence=Decimal("1.00"),
        description="x",
    )
    results = [
        _ocr_result(extracted_fields=()),
        _metadata_result(),
        _provenance_result(evidence_observed=True),
        _vision_result(),
    ]
    breakdown = score([critical], results, RULESET_2026_09_04)
    assert breakdown.classification is Classification.HIGH_RISK
