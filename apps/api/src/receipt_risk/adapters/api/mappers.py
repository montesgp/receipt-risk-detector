"""One-directional domain -> transport mapping. Domain objects never carry
Pydantic types; this module is the sole translation point (design.md
"API adapter").
"""

from __future__ import annotations

from receipt_risk.adapters.api.schemas import (
    AnalyzeResponse,
    AnalyzerStatusModel,
    ExtractedFieldModel,
    SignalModel,
)
from receipt_risk.domain.assessment import FraudAssessment

_MASKED_FIELDS = frozenset({"destination_cbu", "cuit"})


def _mask(value: str) -> str:
    """Mask all but the last 4 characters. Mirrors
    `application/financial_validation._mask` — duplicated here deliberately
    since transport masking and domain-evidence masking are independent
    concerns that must not couple the API adapter to application internals."""
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def _extracted_data(assessment: FraudAssessment) -> dict[str, ExtractedFieldModel]:
    ocr_result = next(
        (result for result in assessment.analyzer_statuses if result.analyzer == "paddleocr-onnx"),
        None,
    )
    if ocr_result is None:
        return {}

    data: dict[str, ExtractedFieldModel] = {}
    for field in ocr_result.extracted_fields:
        if field.normalized is None:
            continue
        if field.name in _MASKED_FIELDS:
            data[field.name] = ExtractedFieldModel(
                masked_value=_mask(field.normalized), confidence=float(field.confidence)
            )
        else:
            data[field.name] = ExtractedFieldModel(
                value=field.normalized, confidence=float(field.confidence)
            )
    return data


def assessment_to_response(assessment: FraudAssessment) -> AnalyzeResponse:
    return AnalyzeResponse(
        analysis_id=assessment.analysis_id,
        engine_version=assessment.engine_version,
        ruleset_version=assessment.ruleset_version,
        classification=assessment.classification.value,
        risk_score=assessment.risk_score,
        confidence_score=assessment.confidence_score,
        recommended_action=assessment.recommended_action.value,
        signals=[
            SignalModel(
                code=signal.code.value,
                category=signal.category.value,
                severity=signal.severity.value,
                confidence=float(signal.confidence),
                description=signal.description,
                evidence=dict(signal.evidence),
                score_contribution=signal.score_contribution,
            )
            for signal in assessment.signals
        ],
        extracted_data=_extracted_data(assessment),
        analyzer_statuses=[
            AnalyzerStatusModel(
                analyzer=result.analyzer, status=result.status, duration_ms=result.duration_ms
            )
            for result in assessment.analyzer_statuses
        ],
        limitations=list(assessment.limitations),
        duration_ms=assessment.duration_ms,
    )
