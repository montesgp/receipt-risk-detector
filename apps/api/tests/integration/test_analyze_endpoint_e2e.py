"""End-to-end test: POST a real committed `samples/` fixture through the
actual `POST /v1/receipts/analyze` endpoint via `TestClient`.

Real OCR models and the `exiftool` binary are not available in every
local dev environment (RECEIPT_RISK_OCR_MODEL_DIR unset, no baked
models) -- this mirrors the existing skip pattern in
`tests/integration/test_ocr_integration.py`. This test exercises the
real HTTP route, the real ingestion pipeline (real decode/hash/cleanup),
and the real scoring/assembly path end to end, with the three analyzer
*ports* stubbed to the fixture's `declared_fields`/`expected_signals` so
it runs deterministically everywhere. CI's OCR-integration suite
(`test_ocr_integration.py`) is the real-engine coverage for the OCR
adapter itself; this test is the coverage for the full request pipeline
wiring (router -> use case -> domain -> response).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import Fixture
from conftest import fixture as load_fixture
from receipt_risk.adapters.api.dependencies import get_use_case
from receipt_risk.adapters.api.router import router
from receipt_risk.adapters.image.pillow_decoder import PillowImageDecoder
from receipt_risk.application.analyze_receipt import ENGINE_VERSION, AnalyzeReceiptUseCase
from receipt_risk.application.ingestion import IngestionService
from receipt_risk.domain.analysis import AnalyzerResult, ExtractedField
from receipt_risk.domain.rulesets.v2026_09_05 import RULESET_2026_09_05


class _FixtureOcrPort:
    """Simulates the OCR adapter's output from the fixture's
    `declared_fields` -- a stand-in for the real ONNX engine, not for the
    ingestion/router/scoring pipeline under test here."""

    name = "paddleocr-onnx"
    version = "1.0.0"

    def __init__(self, fixture: Fixture) -> None:
        self._fixture = fixture

    async def extract(self, image) -> AnalyzerResult:
        fields = []
        declared = self._fixture.declared_fields
        for name in ("amount", "destination_cbu", "cuit", "date_time"):
            value = declared.get(name)
            if value is None:
                continue
            fields.append(
                ExtractedField(
                    name=name, raw_text=value, normalized=value, confidence=Decimal("0.95")
                )
            )
        status = self._fixture.expected_analyzer_statuses.get("ocr", "completed")
        return AnalyzerResult(
            analyzer=self.name, version=self.version, status=status, extracted_fields=tuple(fields)
        )


class _FixtureNeutralPort:
    name = "stub"
    version = "1.0.0"

    _NAMES = {"metadata": "exiftool", "provenance": "c2pa", "vision": "mobilenetv3-embedding"}

    def __init__(self, role: str, fixture: Fixture) -> None:
        self.name = self._NAMES.get(role, "stub")
        self._status = fixture.expected_analyzer_statuses.get(role, "completed")

    async def inspect(self, image) -> AnalyzerResult:
        return AnalyzerResult(analyzer=self.name, version=self.version, status=self._status)


def _app_for_fixture(fixture: Fixture, tmp_path: Path) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    ingestion = IngestionService(temp_dir=tmp_path, decoder=PillowImageDecoder())
    use_case = AnalyzeReceiptUseCase(
        ocr=_FixtureOcrPort(fixture),
        metadata=_FixtureNeutralPort("metadata", fixture),
        provenance=_FixtureNeutralPort("provenance", fixture),
        vision=_FixtureNeutralPort("vision", fixture),
        ingestion=ingestion,
        ruleset=RULESET_2026_09_05,
    )
    app.dependency_overrides[get_use_case] = lambda: use_case
    return app


def test_clean_valid_transfer_fixture_returns_low_risk_via_real_endpoint(tmp_path: Path) -> None:
    fixture = load_fixture("clean_valid_transfer")
    client = TestClient(_app_for_fixture(fixture, tmp_path))

    response = client.post(
        "/v1/receipts/analyze", files={"file": (fixture.path.name, fixture.bytes, "image/png")}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ruleset_version"] == RULESET_2026_09_05.version
    assert body["engine_version"] == ENGINE_VERSION
    assert body["classification"] == "LOW_RISK"
    assert body["risk_score"] == 0
    assert body["analysis_id"].startswith("sha256:")


def test_invalid_cbu_fixture_produces_expected_signal_via_real_endpoint(tmp_path: Path) -> None:
    fixture = load_fixture("invalid_cbu_check_digit")
    client = TestClient(_app_for_fixture(fixture, tmp_path))

    response = client.post(
        "/v1/receipts/analyze", files={"file": (fixture.path.name, fixture.bytes, "image/png")}
    )

    assert response.status_code == 200
    body = response.json()
    codes = [signal["code"] for signal in body["signals"]]
    assert "INVALID_CBU_CHECK_DIGIT" in codes


def test_corrupted_truncated_fixture_rejected_via_real_endpoint(tmp_path: Path) -> None:
    fixture = load_fixture("corrupted_truncated")
    app = FastAPI()
    app.include_router(router)
    ingestion = IngestionService(temp_dir=tmp_path, decoder=PillowImageDecoder())
    use_case = AnalyzeReceiptUseCase(
        ocr=_FixtureOcrPort(fixture),
        metadata=_FixtureNeutralPort("metadata", fixture),
        provenance=_FixtureNeutralPort("provenance", fixture),
        vision=_FixtureNeutralPort("vision", fixture),
        ingestion=ingestion,
        ruleset=RULESET_2026_09_05,
    )
    app.dependency_overrides[get_use_case] = lambda: use_case
    client = TestClient(app)

    response = client.post(
        "/v1/receipts/analyze", files={"file": (fixture.path.name, fixture.bytes, "image/jpeg")}
    )

    assert response.status_code == fixture.expected_error["status"]
    assert response.json()["code"] == fixture.expected_error["code"]
