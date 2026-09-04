"""`VisionPort` implementation over a frozen `torchvision.models.
mobilenet_v3_small` embedder (the "MobileNetV3-Small, weights=None + local
state_dict" locked choice in design.md's Architecture Decisions table).
Adapter-only per `docs/ARCHITECTURE.md` §5: `torch`/`torchvision` never
cross into `domain/` or `application/` (ruff banned-api, `TID251`).

Mirrors `adapters/ocr/paddle_onnx.py`'s fail-closed model-loading pattern
exactly: the model directory is validated to contain every required file
strictly *before* `torch`/`torchvision` are ever imported or a model is
constructed. A missing/incomplete `RECEIPT_RISK_VISION_MODEL_DIR` folds
into `AnalyzerResult(status="failed", error_code="ANALYZER_UNAVAILABLE")`
-- never an exception, never an implicit download. Reference embeddings
are a committed, versioned JSON artifact (`reference_embeddings_v1.json`),
loaded once at construction with a pure JSON read (no torch).

Threshold rationale (documented default, not benchmarked -- see
design.md's Architecture Decisions "Thresholds" row and the ruleset
docstring's "reasonable defaults, not fake precision" stance): the
reference set is a small, deliberately multi-modal collection of
known-legitimate receipt renders. Nearest-neighbour cosine distance
(`d = 1 - max_j cos(e, r_j)`) is the correct one-class outlier rule for
that shape of data; a mean/centroid distance would sit between modes and
flag every legitimate template. `d < 0.30` is treated as "close enough to
a known template" (no signal); `0.30 <= d < 0.45` is a weak outlier
(LOW, confidence 0.50); `d >= 0.45` is a stronger outlier (MEDIUM,
confidence 0.70). This is pixel-space evidence only -- it is deliberately
capped at MEDIUM and carries no `_CRITICAL_FLOOR` entry, so it can raise a
risk score but never force a verdict on its own.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Final

import anyio
import numpy as np

from receipt_risk.adapters.vision.preprocess import preprocess
from receipt_risk.application.models import SafeImageRef
from receipt_risk.domain.analysis import AnalyzerResult
from receipt_risk.domain.signals import (
    Severity,
    SignalCategory,
    SignalCode,
    ValidationSignal,
)

_MODEL_DIR_ENV_VAR: Final[str] = "RECEIPT_RISK_VISION_MODEL_DIR"
_WEIGHTS_FILENAME: Final[str] = "mobilenet_v3_small.pth"

_REFERENCE_EMBEDDINGS_PATH: Final[Path] = Path(__file__).parent / "reference_embeddings_v1.json"
_REFERENCE_SET_VERSION: Final[str] = "v1"

# Documented reasoned defaults -- see module docstring "Threshold rationale".
OUTLIER_THRESHOLD: Final[Decimal] = Decimal("0.30")  # d >= this -> LOW
MEDIUM_THRESHOLD: Final[Decimal] = Decimal("0.45")  # d >= this -> MEDIUM
LOW_CONFIDENCE: Final[Decimal] = Decimal("0.50")
MEDIUM_CONFIDENCE: Final[Decimal] = Decimal("0.70")

EmbedCallable = Callable[[Path], np.ndarray]  # -> (576,) L2-normalised float32


class VisionEngineUnavailable(Exception):
    """Raised when `RECEIPT_RISK_VISION_MODEL_DIR` is unset, missing, or
    incomplete, or the reference-embedding artifact cannot be read. Raised
    *before* any model is constructed -- no network call is ever made to
    satisfy a missing model."""


def _model_dir_from_env() -> Path | None:
    value = os.environ.get(_MODEL_DIR_ENV_VAR)
    # Mirrors adapters/ocr/paddle_onnx.py: CI's `env:` mapping passes values
    # through literally without shell-expanding "~".
    return Path(value).expanduser() if value else None


def _load_reference_embeddings() -> np.ndarray:
    if not _REFERENCE_EMBEDDINGS_PATH.is_file():
        raise VisionEngineUnavailable(
            f"reference embeddings artifact missing at {_REFERENCE_EMBEDDINGS_PATH}"
        )
    payload = json.loads(_REFERENCE_EMBEDDINGS_PATH.read_text(encoding="utf-8"))
    embeddings = payload.get("embeddings", [])
    if not embeddings:
        raise VisionEngineUnavailable("reference embeddings artifact contains zero embeddings")
    return np.asarray(embeddings, dtype=np.float32)


def _load_embedder(model_dir: Path | None) -> EmbedCallable:
    """Validate `model_dir` contains the baked weights file, then construct
    a real embedder bound to those weights. Never downloads: the check
    happens strictly before `torch`/`torchvision` import/construction."""
    if model_dir is None:
        raise VisionEngineUnavailable(f"{_MODEL_DIR_ENV_VAR} is not set")

    model_dir = Path(model_dir)
    weights_path = model_dir / _WEIGHTS_FILENAME
    if not weights_path.is_file():
        raise VisionEngineUnavailable(
            f"vision model directory {model_dir} is missing {_WEIGHTS_FILENAME}"
        )

    # Deferred imports: torch/torchvision only cross the adapter boundary
    # once the fail-closed check above has already passed. HF_HUB_OFFLINE
    # and weights_only=True keep this a zero-network, pickle-safe load.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import torch  # noqa: TID251 -- adapters/** is exempt, see pyproject.toml
    import torchvision  # noqa: TID251 -- adapters/** is exempt, see pyproject.toml

    model = torchvision.models.mobilenet_v3_small(weights=None)
    state_dict = torch.load(str(weights_path), map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()

    def _embed(path: Path) -> np.ndarray:
        array = preprocess(path)  # (3, 224, 224) float32, ImageNet-normalised
        tensor = torch.from_numpy(array).unsqueeze(0)  # (1, 3, 224, 224)
        with torch.no_grad():
            features = model.features(tensor)  # (1, C, H', W')
            pooled = torch.nn.functional.adaptive_avg_pool2d(features, 1)
            flat = torch.flatten(pooled, 1)  # (1, 576)
            normalized = torch.nn.functional.normalize(flat, p=2, dim=1)
        return normalized.squeeze(0).cpu().numpy().astype(np.float32)

    return _embed


def _max_cosine_similarity(embedding: np.ndarray, reference: np.ndarray) -> float:
    # Both `embedding` and each row of `reference` are already L2-normalised,
    # so cosine similarity reduces to a dot product.
    similarities = reference @ embedding
    return float(np.max(similarities))


def _derive_signal(*, cosine_distance: Decimal, reference_set_size: int) -> ValidationSignal | None:
    """Pure distance -> signal derivation, mirroring
    `adapters/provenance/c2pa_reader._derive_signals`'s style. Returns
    `None` when the embedding is close enough to the reference set (no
    outlier finding)."""
    if cosine_distance >= MEDIUM_THRESHOLD:
        severity, confidence = Severity.MEDIUM, MEDIUM_CONFIDENCE
    elif cosine_distance >= OUTLIER_THRESHOLD:
        severity, confidence = Severity.LOW, LOW_CONFIDENCE
    else:
        return None

    return ValidationSignal(
        code=SignalCode.VISUAL_ANOMALY_DETECTED,
        category=SignalCategory.VISUAL,
        severity=severity,
        confidence=confidence,
        description=(
            "This receipt's visual appearance is an outlier relative to the "
            "bundled set of known-legitimate receipt renders."
        ),
        evidence={
            "cosine_distance": str(cosine_distance),
            "threshold": str(MEDIUM_THRESHOLD),
            "reference_set_version": _REFERENCE_SET_VERSION,
            "reference_set_size": str(reference_set_size),
        },
    )


def _elapsed_ms(started_monotonic: float) -> int:
    return int((time.monotonic() - started_monotonic) * 1000)


class MobileNetV3VisionAdapter:
    """Concrete `VisionPort` implementation. `embed`/`reference_embeddings`
    are constructor-injectable so tests never load real weights."""

    name = "mobilenetv3-embedding"
    version = "1.0.0"

    def __init__(
        self,
        *,
        model_dir: Path | None = None,
        embed: EmbedCallable | None = None,
        reference_embeddings: np.ndarray | None = None,
    ) -> None:
        self._model_dir = model_dir if model_dir is not None else _model_dir_from_env()
        self._embed_override = embed
        self._reference_override = reference_embeddings
        self._lazy_embed: EmbedCallable | None = None
        self._lazy_reference: np.ndarray | None = None

    def _resolve(self) -> tuple[EmbedCallable, np.ndarray]:
        if self._embed_override is not None:
            reference = (
                self._reference_override
                if self._reference_override is not None
                else _load_reference_embeddings()
            )
            return self._embed_override, reference

        if self._lazy_embed is None:
            self._lazy_embed = _load_embedder(self._model_dir)
        if self._lazy_reference is None:
            self._lazy_reference = (
                self._reference_override
                if self._reference_override is not None
                else _load_reference_embeddings()
            )
        return self._lazy_embed, self._lazy_reference

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        started = time.monotonic()
        try:
            embed, reference = self._resolve()
        except VisionEngineUnavailable:
            return AnalyzerResult(
                analyzer=self.name,
                version=self.version,
                status="failed",
                error_code="ANALYZER_UNAVAILABLE",
                duration_ms=_elapsed_ms(started),
            )

        return await anyio.to_thread.run_sync(self._run, embed, reference, image.path, started)

    def _run(
        self, embed: EmbedCallable, reference: np.ndarray, path: Path, started: float
    ) -> AnalyzerResult:
        embedding = embed(path)
        similarity = _max_cosine_similarity(embedding, reference)
        raw_distance = Decimal(1) - Decimal(str(round(similarity, 4)))
        cosine_distance = raw_distance.quantize(Decimal("0.01"))
        signal = _derive_signal(cosine_distance=cosine_distance, reference_set_size=len(reference))
        return AnalyzerResult(
            analyzer=self.name,
            version=self.version,
            status="completed",
            signals=(signal,) if signal is not None else (),
            duration_ms=_elapsed_ms(started),
        )
