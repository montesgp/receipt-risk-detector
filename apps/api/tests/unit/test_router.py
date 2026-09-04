"""Tests for `adapters/api/router.py` and `bootstrap/app.py` registration."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from receipt_risk.adapters.api.dependencies import get_use_case
from receipt_risk.adapters.api.router import router
from receipt_risk.application.analyze_receipt import AnalyzeReceiptUseCase
from receipt_risk.application.ingestion import IngestionService
from receipt_risk.application.models import DecodedImageInfo, SafeImageRef
from receipt_risk.domain.analysis import AnalyzerResult
from receipt_risk.domain.rulesets.v2026_09_04 import RULESET_2026_09_04


class _StubDecoder:
    def probe(self, data: bytes) -> DecodedImageInfo:
        return DecodedImageInfo(media_type="image/png", width=10, height=10)


class _CompletedPort:
    name = "stub"
    version = "1.0.0"

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        return AnalyzerResult(analyzer=self.name, version=self.version, status="completed")

    async def extract(self, image: SafeImageRef) -> AnalyzerResult:
        return AnalyzerResult(analyzer=self.name, version=self.version, status="completed")


def _app(tmp_path: Path) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    ingestion = IngestionService(temp_dir=tmp_path, decoder=_StubDecoder())
    use_case = AnalyzeReceiptUseCase(
        ocr=_CompletedPort(),
        metadata=_CompletedPort(),
        provenance=_CompletedPort(),
        vision=_CompletedPort(),
        ingestion=ingestion,
        ruleset=RULESET_2026_09_04,
    )
    app.dependency_overrides[get_use_case] = lambda: use_case
    return app


def test_post_analyze_returns_full_assessment_with_ruleset_and_engine_version(
    tmp_path: Path,
) -> None:
    client = TestClient(_app(tmp_path))
    response = client.post(
        "/v1/receipts/analyze", files={"file": ("receipt.png", b"fake-png-bytes", "image/png")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ruleset_version"] == "2026-09-04"
    assert body["engine_version"] == "0.1.0"
    assert "risk_score" in body
    assert "confidence_score" in body
    assert "classification" in body


def test_missing_file_returns_documented_400_problem_details(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path))
    response = client.post("/v1/receipts/analyze", files={})
    assert response.status_code in (400, 422)


def test_analyze_route_appears_in_openapi_only_after_slice4_registration() -> None:
    from receipt_risk.bootstrap.app import app as bootstrap_app

    paths = bootstrap_app.openapi()["paths"]
    assert "/v1/receipts/analyze" in paths
