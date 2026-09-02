"""Contract tests for every reachable documented `ProblemDetails` error
code (`docs/API.md` §5) against the real router.

`ANALYZER_UNAVAILABLE` (503) is documented but intentionally unreachable
through this endpoint: design.md's locked decision is that a failed
analyzer always becomes a `ValidationSignal`, never a request abort (see
`domain/scoring.py`'s `INCONCLUSIVE` coverage path instead).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from receipt_risk.adapters.api.dependencies import get_use_case
from receipt_risk.adapters.api.router import router
from receipt_risk.application.analyze_receipt import AnalysisTimeoutError, AnalyzeReceiptUseCase
from receipt_risk.application.ingestion import IngestionService
from receipt_risk.application.models import DecodedImageInfo
from receipt_risk.domain.rulesets.v2026_09_01 import RULESET_2026_09_01


class _StubDecoder:
    def __init__(self, *, width: int = 10, height: int = 10) -> None:
        self._width = width
        self._height = height

    def probe(self, data: bytes) -> DecodedImageInfo:
        return DecodedImageInfo(media_type="image/png", width=self._width, height=self._height)


class _AlwaysTimesOutUseCase:
    async def execute(self, data: bytes, *, declared_filename: str | None = None):
        raise AnalysisTimeoutError("budget exhausted")


def _app(tmp_path: Path, *, decoder=None, use_case=None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    if use_case is not None:
        app.dependency_overrides[get_use_case] = lambda: use_case
    else:
        ingestion = IngestionService(temp_dir=tmp_path, decoder=decoder or _StubDecoder())
        real_use_case = AnalyzeReceiptUseCase(
            ocr=_NoopPort(),
            metadata=_NoopPort(),
            provenance=_NoopPort(),
            ingestion=ingestion,
            ruleset=RULESET_2026_09_01,
        )
        app.dependency_overrides[get_use_case] = lambda: real_use_case
    return app


class _NoopPort:
    name = "stub"
    version = "1.0.0"

    async def inspect(self, image):
        from receipt_risk.domain.analysis import AnalyzerResult

        return AnalyzerResult(analyzer=self.name, version=self.version, status="completed")

    async def extract(self, image):
        from receipt_risk.domain.analysis import AnalyzerResult

        return AnalyzerResult(analyzer=self.name, version=self.version, status="completed")


def test_missing_file_returns_400(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path))
    response = client.post("/v1/receipts/analyze", data={})
    assert response.status_code == 400
    assert response.json()["code"] == "MISSING_FILE"


def test_file_too_large_returns_413(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path))
    huge = b"0" * (10 * 1024 * 1024 + 1)
    response = client.post("/v1/receipts/analyze", files={"file": ("big.png", huge, "image/png")})
    assert response.status_code == 413
    assert response.json()["code"] == "FILE_TOO_LARGE"


def test_unsupported_image_returns_415(tmp_path: Path) -> None:
    class _RejectingDecoder:
        def probe(self, data: bytes):
            from receipt_risk.application.errors import IngestionError, IngestionErrorCode

            raise IngestionError(
                IngestionErrorCode.UNSUPPORTED_IMAGE, "The uploaded content could not be decoded."
            )

    client = TestClient(_app(tmp_path, decoder=_RejectingDecoder()))
    response = client.post(
        "/v1/receipts/analyze", files={"file": ("bad.png", b"not-an-image", "image/png")}
    )
    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_IMAGE"


def test_image_dimensions_exceeded_returns_422(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path, decoder=_StubDecoder(width=20000, height=20000)))
    response = client.post(
        "/v1/receipts/analyze", files={"file": ("huge.png", b"pixels", "image/png")}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "IMAGE_DIMENSIONS_EXCEEDED"


def test_analysis_timeout_returns_504(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path, use_case=_AlwaysTimesOutUseCase()))
    response = client.post(
        "/v1/receipts/analyze", files={"file": ("receipt.png", b"pixels", "image/png")}
    )
    assert response.status_code == 504
    assert response.json()["code"] == "ANALYSIS_TIMEOUT"


@pytest.mark.parametrize(
    "endpoint",
    ["/v1/receipts/analyze"],
)
def test_every_problem_response_matches_documented_shape(tmp_path: Path, endpoint: str) -> None:
    client = TestClient(_app(tmp_path))
    response = client.post(endpoint, data={})
    body = response.json()
    assert set(body.keys()) == {
        "type",
        "title",
        "status",
        "detail",
        "instance",
        "request_id",
        "code",
    }
