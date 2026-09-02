"""`OcrPort` implementation over RapidOCR's ONNX Runtime PP-OCRv4 models
(the "PaddleOCR ONNX variant" locked in proposal.md's "Locked technical
decisions"). Adapter-only per `docs/ARCHITECTURE.md` §5: `cv2` and
`rapidocr_onnxruntime` never cross into `domain/` or `application/` (ruff
banned-api).

Implements design.md's "OCR adapter -- bounded single retry" state
machine exactly: attempt 1, evaluate coverage, one bounded preprocessing
retry, keep the better result, emit `CORE_FIELD_EXTRACTION_FAILED` when
coverage still falls short. `extract` never raises.

Threat matrix: "Process integration (OCR model loading)" -- the engine is
loaded once, lazily, strictly from `RECEIPT_RISK_OCR_MODEL_DIR` (or an
explicit `model_dir`); a missing/incomplete model directory fails closed
to `AnalyzerResult(status="failed", error_code="ANALYZER_UNAVAILABLE")`
*before* `rapidocr_onnxruntime.RapidOCR` is ever constructed, so no
download is ever attempted.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Final

import anyio
import cv2  # noqa: TID251 -- adapters/** is exempt, see pyproject.toml
import numpy as np

from receipt_risk.adapters.ocr.field_parsers import (
    CORE_FIELD_NAMES,
    boxes_from_engine_output,
    extract_core_fields,
)
from receipt_risk.adapters.ocr.preprocess import preprocess
from receipt_risk.application.models import SafeImageRef
from receipt_risk.domain.analysis import AnalyzerResult, ExtractedField
from receipt_risk.domain.signals import (
    ExtractionFailureReason,
    Severity,
    SignalCategory,
    SignalCode,
    ValidationSignal,
)

_MODEL_DIR_ENV_VAR: Final[str] = "RECEIPT_RISK_OCR_MODEL_DIR"
_DET_MODEL_FILENAME: Final[str] = "det.onnx"
_CLS_MODEL_FILENAME: Final[str] = "cls.onnx"
_REC_MODEL_FILENAME: Final[str] = "rec.onnx"

COVERAGE_THRESHOLD: Final[Decimal] = Decimal("0.75")
FIELD_CONFIDENCE_THRESHOLD: Final[Decimal] = Decimal("0.60")
DEFAULT_BUDGET_MS: Final[int] = 6000  # NFR-001's ocr_s budget (design.md TimeBudget.ocr_s)

EngineCallable = Callable[[np.ndarray], list]


class OcrEngineUnavailable(Exception):
    """Raised when `RECEIPT_RISK_OCR_MODEL_DIR` is unset, missing, or
    incomplete. Raised *before* any engine is constructed -- no network
    call is ever made to satisfy a missing model."""


def _model_dir_from_env() -> Path | None:
    value = os.environ.get(_MODEL_DIR_ENV_VAR)
    # .expanduser() matters here: GitHub Actions' `env:` mapping passes values
    # through literally, it does not shell-expand them the way a `run:` step's
    # command line does -- ci.yml sets this to "~/.cache/receipt-risk/ocr-models",
    # which without expansion is a literal "~" path component, not a home
    # directory reference (confirmed: reproduces identically on Windows/Linux).
    return Path(value).expanduser() if value else None


def _load_rapidocr_engine(model_dir: Path | None) -> EngineCallable:
    """Validate `model_dir` contains every required baked model file, then
    construct a real `RapidOCR` engine bound to those exact files. Never
    downloads: the check happens strictly before import/construction."""
    if model_dir is None:
        raise OcrEngineUnavailable(f"{_MODEL_DIR_ENV_VAR} is not set")

    model_dir = Path(model_dir)
    det_path = model_dir / _DET_MODEL_FILENAME
    cls_path = model_dir / _CLS_MODEL_FILENAME
    rec_path = model_dir / _REC_MODEL_FILENAME
    if not (det_path.is_file() and cls_path.is_file() and rec_path.is_file()):
        raise OcrEngineUnavailable(
            f"OCR model directory {model_dir} is missing one or more baked model files"
        )

    from rapidocr_onnxruntime import RapidOCR  # noqa: TID251 -- adapter-only import

    engine = RapidOCR(
        det_model_path=str(det_path), cls_model_path=str(cls_path), rec_model_path=str(rec_path)
    )

    def _run(pixels: np.ndarray) -> list:
        result, _elapse = engine(pixels)
        return result or []

    return _run


def _read_pixels(path: Path) -> np.ndarray:
    pixels = cv2.imread(str(path))
    if pixels is None:
        raise OcrEngineUnavailable(f"could not decode image at {path}")
    return pixels


def _coverage(fields: tuple[ExtractedField, ...]) -> Decimal:
    by_name = {field.name: field for field in fields}
    hits = sum(
        1
        for name in CORE_FIELD_NAMES
        if (field := by_name.get(name)) is not None
        and field.normalized is not None
        and field.confidence >= FIELD_CONFIDENCE_THRESHOLD
    )
    return (Decimal(hits) / Decimal(len(CORE_FIELD_NAMES))).quantize(Decimal("0.01"))


def _mean_confidence(fields: tuple[ExtractedField, ...]) -> Decimal:
    if not fields:
        return Decimal("0.00")
    return (sum((field.confidence for field in fields), Decimal("0")) / len(fields)).quantize(
        Decimal("0.01")
    )


def _elapsed_ms(started_monotonic: float) -> int:
    return int((time.monotonic() - started_monotonic) * 1000)


def _extraction_failed_signal(
    reason: ExtractionFailureReason, *, coverage: Decimal, retry_count: int
) -> ValidationSignal:
    return ValidationSignal(
        code=SignalCode.CORE_FIELD_EXTRACTION_FAILED,
        category=SignalCategory.DATA_QUALITY,
        severity=Severity.MEDIUM,
        confidence=Decimal("1.00"),
        description="One or more core receipt fields could not be reliably extracted.",
        evidence={
            "reason": reason.value,
            "retry_count": str(retry_count),
            "core_field_coverage": str(coverage),
        },
    )


class PaddleOnnxOcrAdapter:
    """Concrete `OcrPort` implementation. `engine`/`model_dir` are
    constructor-injectable so tests never load a real ONNX model."""

    name = "paddleocr-onnx"
    version = "1.0.0"

    def __init__(
        self,
        *,
        model_dir: Path | None = None,
        engine: EngineCallable | None = None,
        budget_ms: int = DEFAULT_BUDGET_MS,
    ) -> None:
        self._model_dir = model_dir if model_dir is not None else _model_dir_from_env()
        self._engine_override = engine
        self._lazy_engine: EngineCallable | None = None
        self._budget_ms = budget_ms

    def _resolve_engine(self) -> EngineCallable:
        if self._engine_override is not None:
            return self._engine_override
        if self._lazy_engine is None:
            self._lazy_engine = _load_rapidocr_engine(self._model_dir)
        return self._lazy_engine

    async def extract(self, image: SafeImageRef) -> AnalyzerResult:
        started = time.monotonic()
        try:
            engine = self._resolve_engine()
        except OcrEngineUnavailable:
            return AnalyzerResult(
                analyzer=self.name,
                version=self.version,
                status="failed",
                error_code="ANALYZER_UNAVAILABLE",
                duration_ms=_elapsed_ms(started),
            )

        return await anyio.to_thread.run_sync(self._run_bounded_retry, engine, image.path, started)

    def _run_bounded_retry(
        self, engine: EngineCallable, path: Path, started: float
    ) -> AnalyzerResult:
        pixels = _read_pixels(path)

        attempt1_started = time.monotonic()
        boxes1 = boxes_from_engine_output(engine(pixels))
        fields1 = extract_core_fields(boxes1)
        coverage1 = _coverage(fields1)
        attempt1_elapsed_ms = _elapsed_ms(attempt1_started)
        reason1 = (
            ExtractionFailureReason.NO_TEXT_DETECTED
            if not boxes1
            else ExtractionFailureReason.LOW_CONFIDENCE
        )

        if coverage1 >= COVERAGE_THRESHOLD:
            return AnalyzerResult(
                analyzer=self.name,
                version=self.version,
                status="completed",
                extracted_fields=fields1,
                duration_ms=_elapsed_ms(started),
            )

        remaining_budget_ms = self._budget_ms - _elapsed_ms(started)
        if remaining_budget_ms <= 0 or remaining_budget_ms < attempt1_elapsed_ms:
            reason = reason1 if not boxes1 else ExtractionFailureReason.TIMEOUT
            return AnalyzerResult(
                analyzer=self.name,
                version=self.version,
                status="partial",
                extracted_fields=fields1,
                signals=(_extraction_failed_signal(reason, coverage=coverage1, retry_count=0),),
                duration_ms=_elapsed_ms(started),
            )

        preprocessed = preprocess(pixels)
        boxes2 = boxes_from_engine_output(engine(preprocessed))
        fields2 = extract_core_fields(boxes2)
        coverage2 = _coverage(fields2)

        if (coverage2, _mean_confidence(fields2)) > (coverage1, _mean_confidence(fields1)):
            best_fields, best_coverage, best_boxes = fields2, coverage2, boxes2
        else:
            best_fields, best_coverage, best_boxes = fields1, coverage1, boxes1

        if best_coverage >= COVERAGE_THRESHOLD:
            return AnalyzerResult(
                analyzer=self.name,
                version=self.version,
                status="completed",
                extracted_fields=best_fields,
                duration_ms=_elapsed_ms(started),
            )

        final_reason = (
            ExtractionFailureReason.NO_TEXT_DETECTED
            if not best_boxes
            else ExtractionFailureReason.LOW_CONFIDENCE
        )
        return AnalyzerResult(
            analyzer=self.name,
            version=self.version,
            status="partial",
            extracted_fields=best_fields,
            signals=(
                _extraction_failed_signal(final_reason, coverage=best_coverage, retry_count=1),
            ),
            duration_ms=_elapsed_ms(started),
        )
