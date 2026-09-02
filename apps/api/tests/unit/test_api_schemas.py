"""Contract tests for `adapters/api/schemas.py` and `mappers.py` vs
`docs/API.md` §3/§5."""

from __future__ import annotations

from decimal import Decimal

from receipt_risk.adapters.api.errors import problem_details_for_ingestion_error
from receipt_risk.adapters.api.mappers import assessment_to_response
from receipt_risk.application.errors import IngestionError, IngestionErrorCode
from receipt_risk.domain.analysis import AnalyzerResult, ExtractedField
from receipt_risk.domain.assessment import assemble
from receipt_risk.domain.rulesets.v2026_09_01 import RULESET_2026_09_01
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode, ValidationSignal

_RESPONSE_FIELDS = {
    "analysis_id",
    "engine_version",
    "ruleset_version",
    "classification",
    "risk_score",
    "confidence_score",
    "recommended_action",
    "signals",
    "extracted_data",
    "analyzer_statuses",
    "limitations",
    "duration_ms",
}

_FORBIDDEN_VOCABULARY = ("is_real", "is_fake", "authentic", "verified transfer")


def _assessment():
    results = [
        AnalyzerResult(
            analyzer="paddleocr-onnx",
            version="1.0.0",
            status="completed",
            extracted_fields=(
                ExtractedField(
                    name="destination_cbu",
                    raw_text="2850590940090418135202",
                    normalized="2850590940090418135202",
                    confidence=Decimal("0.95"),
                ),
            ),
        ),
        AnalyzerResult(analyzer="exiftool", version="1.0.0", status="completed"),
        AnalyzerResult(analyzer="c2pa", version="1.0.0", status="completed"),
    ]
    signal = ValidationSignal(
        code=SignalCode.INVALID_CBU_CHECK_DIGIT,
        category=SignalCategory.FINANCIAL_CONSISTENCY,
        severity=Severity.HIGH,
        confidence=Decimal("0.98"),
        description="The extracted CBU does not pass its check-digit validation.",
        evidence={"destination_cbu": "**************5202", "failure": "block2_check_digit"},
    )
    return assemble(
        analysis_id="sha256:abc123",
        results=results,
        signals=[signal],
        ruleset=RULESET_2026_09_01,
        engine_version="0.1.0",
        duration_ms=2310,
    )


def test_analyze_response_schema_matches_docs_api_md_field_for_field() -> None:
    response = assessment_to_response(_assessment())
    payload = response.model_dump()
    assert set(payload.keys()) == _RESPONSE_FIELDS


def test_response_never_contains_forbidden_verdict_vocabulary() -> None:
    response = assessment_to_response(_assessment())
    dumped = response.model_dump_json().lower()
    for forbidden in _FORBIDDEN_VOCABULARY:
        assert forbidden not in dumped


def test_ingestion_error_maps_to_documented_problem_details() -> None:
    error = IngestionError(IngestionErrorCode.FILE_TOO_LARGE, "too big")
    problem = problem_details_for_ingestion_error(error, instance="/v1/receipts/analyze")
    assert problem.status == 413
    assert problem.code == "FILE_TOO_LARGE"
    assert problem.instance == "/v1/receipts/analyze"
