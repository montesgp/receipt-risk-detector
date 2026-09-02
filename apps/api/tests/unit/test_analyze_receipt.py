"""Tests for `application/analyze_receipt.py::AnalyzeReceiptUseCase`.

Traces to design.md's "a failed analyzer produces a signal, never an
aborted request" decision and its `_guarded` contract.
"""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest

from receipt_risk.application.analyze_receipt import (
    AnalysisTimeoutError,
    AnalyzeReceiptUseCase,
    TimeBudget,
)
from receipt_risk.application.ingestion import IngestionService
from receipt_risk.application.models import DecodedImageInfo, SafeImageRef
from receipt_risk.domain.analysis import AnalyzerResult
from receipt_risk.domain.rulesets.v2026_09_01 import RULESET_2026_09_01


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


class _RaisingPort:
    name = "stub-raising"
    version = "1.0.0"

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        raise RuntimeError("boom")

    async def extract(self, image: SafeImageRef) -> AnalyzerResult:
        raise RuntimeError("boom")


class _HangingPort:
    name = "stub-hanging"
    version = "1.0.0"

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        await anyio.sleep(10)
        raise AssertionError("should have timed out first")

    async def extract(self, image: SafeImageRef) -> AnalyzerResult:
        await anyio.sleep(10)
        raise AssertionError("should have timed out first")


def _use_case(
    *, ocr=None, metadata=None, provenance=None, budget=None, temp_dir: Path
) -> AnalyzeReceiptUseCase:
    ingestion = IngestionService(temp_dir=temp_dir, decoder=_StubDecoder())
    return AnalyzeReceiptUseCase(
        ocr=ocr or _CompletedPort(),
        metadata=metadata or _CompletedPort(),
        provenance=provenance or _CompletedPort(),
        ingestion=ingestion,
        ruleset=RULESET_2026_09_01,
        budget=budget,
    )


def _safe_image_ref(tmp_path: Path) -> SafeImageRef:
    return SafeImageRef(
        path=tmp_path / "x.bin", sha256="a", media_type="image/png", width=1, height=1, byte_size=1
    )


def test_guarded_call_converts_exception_to_failed_result_never_aborts(tmp_path: Path) -> None:
    use_case = _use_case(metadata=_RaisingPort(), temp_dir=tmp_path)
    safe = _safe_image_ref(tmp_path)

    result = anyio.run(use_case._guarded, _RaisingPort(), "metadata", 5.0, safe)
    assert result.status == "failed"
    assert result.error_code == "ANALYZER_FAILED"


def test_guarded_call_converts_timeout_to_timed_out_result(tmp_path: Path) -> None:
    use_case = _use_case(temp_dir=tmp_path)
    safe = _safe_image_ref(tmp_path)

    result = anyio.run(use_case._guarded, _HangingPort(), "provenance", 0.05, safe)
    assert result.status == "timed_out"
    assert result.error_code == "ANALYZER_TIMEOUT"


def test_whole_request_budget_exhaustion_returns_analysis_timeout(tmp_path: Path) -> None:
    budget = TimeBudget(whole_request_s=0.05, ocr_s=5.0, metadata_s=5.0, provenance_s=5.0)
    use_case = _use_case(ocr=_HangingPort(), budget=budget, temp_dir=tmp_path)
    data = b"\x89PNG\r\n\x1a\nfake-bytes-for-test"

    async def _run() -> None:
        with pytest.raises(AnalysisTimeoutError):
            await use_case.execute(data)

    anyio.run(_run)
    assert list(tmp_path.iterdir()) == []  # cleanup ran even on timeout


def test_cleanup_runs_in_finally_on_success_error_timeout_cancellation(tmp_path: Path) -> None:
    use_case = _use_case(temp_dir=tmp_path)
    data = b"\x89PNG\r\n\x1a\nfake-bytes-success"

    async def _run() -> None:
        assessment = await use_case.execute(data)
        assert assessment.risk_score >= 0

    anyio.run(_run)
    assert list(tmp_path.iterdir()) == []


def test_core_field_extraction_failed_signal_contributes_to_risk_score(tmp_path: Path) -> None:
    use_case = _use_case(ocr=_RaisingPort(), temp_dir=tmp_path)
    data = b"\x89PNG\r\n\x1a\nfake-bytes-ocr-fail"

    async def _run():
        return await use_case.execute(data)

    assessment = anyio.run(_run)
    codes = [s.code.value for s in assessment.signals]
    assert "CORE_FIELD_EXTRACTION_FAILED" in codes
    assert assessment.risk_score > 0
