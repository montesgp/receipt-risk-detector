"""Unit tests for `adapters/ocr/paddle_onnx.py`'s bounded-retry state
machine and fail-closed model-loading path.

Every test here injects a fake `engine` callable via the adapter's
constructor so no real OCR model is ever loaded — traces to design.md's
"OCR adapter -- bounded single retry" state machine and the "Process
integration (OCR model loading)" threat-matrix row. The one test that
exercises the real engine against a baked model lives in
`tests/integration/test_ocr_integration.py` and is `skipif`-guarded.
"""

from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from receipt_risk.adapters.ocr.paddle_onnx import (  # noqa: E402
    OcrEngineUnavailable,
    PaddleOnnxOcrAdapter,
    _load_rapidocr_engine,
    _model_dir_from_env,
)
from receipt_risk.application.models import SafeImageRef  # noqa: E402
from receipt_risk.domain.analysis import AnalyzerResult  # noqa: E402
from receipt_risk.domain.signals import ExtractionFailureReason, SignalCode  # noqa: E402


def _row(text: str, top: float, score: float = 0.95) -> list:
    return [[[80, top], [80 + 200, top], [80 + 200, top + 20], [80, top + 20]], text, score]


_FULL_COVERAGE_RESULT = [
    _row("Monto", 280),
    _row("$ 125.000,00", 316),
    _row("Fecha y hora", 410),
    _row("2026-09-01T14:43:00-03:00", 446),
    _row("CBU destino", 670),
    _row("2850590940090418135201", 706),
    _row("CUIT", 800),
    _row("20-17254359-7", 836),
]

_NO_TEXT_RESULT: list = []

_PARTIAL_RESULT = [
    _row("Monto", 280),
    _row("$ 125.000,00", 316),
]


def _make_image(tmp_path: Path) -> SafeImageRef:
    path = tmp_path / "receipt.png"
    canvas = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.imwrite(str(path), canvas)
    return SafeImageRef(
        path=path, sha256="deadbeef", media_type="image/png", width=100, height=100, byte_size=1
    )


class _CountingEngine:
    """A fake engine returning one scripted result per call, counting how
    many times it was invoked."""

    def __init__(self, results: list[list]) -> None:
        self._results = list(results)
        self.call_count = 0

    def __call__(self, pixels: np.ndarray) -> list:
        self.call_count += 1
        index = min(self.call_count - 1, len(self._results) - 1)
        return self._results[index]


def _extract(adapter: PaddleOnnxOcrAdapter, image: SafeImageRef) -> AnalyzerResult:
    return asyncio.run(adapter.extract(image))


def test_attempt1_completed_when_coverage_at_or_above_075_no_retry(tmp_path: Path) -> None:
    engine = _CountingEngine([_FULL_COVERAGE_RESULT])
    adapter = PaddleOnnxOcrAdapter(engine=engine, budget_ms=6000)

    result = _extract(adapter, _make_image(tmp_path))

    assert result.status == "completed"
    assert engine.call_count == 1
    assert result.signals == ()


def test_exactly_one_preprocessing_retry_when_below_threshold(tmp_path: Path) -> None:
    engine = _CountingEngine([_PARTIAL_RESULT, _PARTIAL_RESULT])
    adapter = PaddleOnnxOcrAdapter(engine=engine, budget_ms=6000)

    result = _extract(adapter, _make_image(tmp_path))

    assert engine.call_count == 2
    assert result.status == "partial"


def test_retry_keeps_better_result_by_coverage_and_confidence(tmp_path: Path) -> None:
    engine = _CountingEngine([_PARTIAL_RESULT, _NO_TEXT_RESULT])
    adapter = PaddleOnnxOcrAdapter(engine=engine, budget_ms=6000)

    result = _extract(adapter, _make_image(tmp_path))

    assert engine.call_count == 2
    assert len(result.extracted_fields) == 1
    assert result.extracted_fields[0].name == "amount"


def test_core_field_extraction_failed_emitted_with_reason_low_confidence_after_retry(
    tmp_path: Path,
) -> None:
    engine = _CountingEngine([_PARTIAL_RESULT, _PARTIAL_RESULT])
    adapter = PaddleOnnxOcrAdapter(engine=engine, budget_ms=6000)

    result = _extract(adapter, _make_image(tmp_path))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.code == SignalCode.CORE_FIELD_EXTRACTION_FAILED
    assert signal.evidence["reason"] == ExtractionFailureReason.LOW_CONFIDENCE.value
    assert signal.evidence["retry_count"] == "1"


def test_no_text_detected_reason_skips_retry_when_budget_insufficient(tmp_path: Path) -> None:
    engine = _CountingEngine([_NO_TEXT_RESULT, _FULL_COVERAGE_RESULT])
    # budget_ms=0 leaves no room for a second attempt regardless of how fast
    # attempt 1 ran, so the retry must be skipped deterministically.
    adapter = PaddleOnnxOcrAdapter(engine=engine, budget_ms=0)

    result = _extract(adapter, _make_image(tmp_path))

    assert engine.call_count == 1
    assert len(result.signals) == 1
    assert result.signals[0].evidence["reason"] == ExtractionFailureReason.NO_TEXT_DETECTED.value


def test_model_dir_from_env_expands_tilde_to_home_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ci.yml sets RECEIPT_RISK_OCR_MODEL_DIR to "~/.cache/receipt-risk/ocr-models"
    # inside a workflow `env:` mapping, which is passed through literally --
    # unlike a `run:` step's command line, it is never shell-expanded. Without
    # .expanduser(), Path("~/...") stays a literal "~" path segment on both
    # Windows and Linux, so CI's Test step would look in the wrong place.
    monkeypatch.setenv("RECEIPT_RISK_OCR_MODEL_DIR", "~/.cache/receipt-risk/ocr-models")

    resolved = _model_dir_from_env()

    assert resolved is not None
    assert "~" not in str(resolved)
    assert resolved.is_absolute()


def test_ocr_adapter_bogus_model_dir_returns_analyzer_unavailable_no_download(
    tmp_path: Path,
) -> None:
    bogus_dir = tmp_path / "does-not-exist"
    with pytest.raises(OcrEngineUnavailable):
        _load_rapidocr_engine(bogus_dir)


def test_ocr_adapter_extract_with_bogus_model_dir_returns_analyzer_unavailable(
    tmp_path: Path,
) -> None:
    adapter = PaddleOnnxOcrAdapter(model_dir=tmp_path / "does-not-exist")

    result = _extract(adapter, _make_image(tmp_path))

    assert result.status == "failed"
    assert result.error_code == "ANALYZER_UNAVAILABLE"


def test_ocr_analysis_makes_zero_outbound_network_connections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Block outbound (non-loopback) connections only. asyncio's Windows
    # ProactorEventLoop opens a real loopback socketpair as internal
    # self-pipe plumbing on every `asyncio.run()` (socket.py's
    # `_fallback_socketpair`) -- that's not network I/O our code performs,
    # and blocking it unconditionally breaks the event loop itself rather
    # than proving anything about OCR's network behavior.
    _LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
    _real_connect = socket.socket.connect
    _real_connect_ex = socket.socket.connect_ex

    def _guarded_connect(self: socket.socket, address: object, *args: object, **kwargs: object):
        host = address[0] if isinstance(address, tuple) else address
        if host not in _LOOPBACK_HOSTS:
            raise AssertionError("OCR analysis attempted to open an outbound network connection")
        return _real_connect(self, address, *args, **kwargs)

    def _guarded_connect_ex(self: socket.socket, address: object, *args: object, **kwargs: object):
        host = address[0] if isinstance(address, tuple) else address
        if host not in _LOOPBACK_HOSTS:
            raise AssertionError("OCR analysis attempted to open an outbound network connection")
        return _real_connect_ex(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)

    engine = _CountingEngine([_FULL_COVERAGE_RESULT])
    adapter = PaddleOnnxOcrAdapter(engine=engine, budget_ms=6000)

    result = _extract(adapter, _make_image(tmp_path))

    assert result.status == "completed"
