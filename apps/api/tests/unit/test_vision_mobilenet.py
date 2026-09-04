"""Unit tests for `adapters/vision/mobilenet_embedder.py`'s fail-closed
model-loading path and pure distance -> severity signal derivation.

Every test injects a fake `embed` callable and a synthetic reference
matrix via the adapter's constructor so no real MobileNetV3 weights are
ever loaded -- mirrors `tests/unit/test_ocr_paddle_onnx.py`. The one test
exercising the real model against baked weights lives in
`tests/integration/test_vision_integration.py`, `skipif`-guarded.
"""

from __future__ import annotations

import asyncio
import socket
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest

from receipt_risk.adapters.vision.mobilenet_embedder import (
    MobileNetV3VisionAdapter,
    VisionEngineUnavailable,
    _derive_signal,
    _model_dir_from_env,
)
from receipt_risk.application.models import SafeImageRef
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode

_MODEL_DIR_ENV_VAR = "RECEIPT_RISK_VISION_MODEL_DIR"


def _make_image(tmp_path: Path) -> SafeImageRef:
    path = tmp_path / "receipt.png"
    path.write_bytes(b"not-a-real-png-but-unread-by-fake-embed")
    return SafeImageRef(
        path=path, sha256="deadbeef", media_type="image/png", width=10, height=10, byte_size=1
    )


def _extract(adapter: MobileNetV3VisionAdapter, image: SafeImageRef):
    return asyncio.run(adapter.inspect(image))


def test_unset_model_dir_env_var_returns_analyzer_unavailable_zero_network(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(_MODEL_DIR_ENV_VAR, raising=False)

    _real_connect = socket.socket.connect

    def _guarded_connect(self, address, *args, **kwargs):
        host = address[0] if isinstance(address, tuple) else address
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError("vision analysis attempted an outbound network connection")
        return _real_connect(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)

    adapter = MobileNetV3VisionAdapter()
    result = _extract(adapter, _make_image(tmp_path))

    assert result.status == "failed"
    assert result.error_code == "ANALYZER_UNAVAILABLE"


def test_model_dir_from_env_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(_MODEL_DIR_ENV_VAR, raising=False)
    assert _model_dir_from_env() is None


def test_bogus_model_dir_raises_vision_engine_unavailable(tmp_path: Path) -> None:
    from receipt_risk.adapters.vision.mobilenet_embedder import _load_embedder

    bogus_dir = tmp_path / "does-not-exist"
    with pytest.raises(VisionEngineUnavailable):
        _load_embedder(bogus_dir)


def test_distance_to_severity_mapping_at_each_threshold_boundary() -> None:
    below = _derive_signal(cosine_distance=Decimal("0.10"), reference_set_size=12)
    assert below is None

    just_below_low = _derive_signal(cosine_distance=Decimal("0.2999"), reference_set_size=12)
    assert just_below_low is None

    low = _derive_signal(cosine_distance=Decimal("0.30"), reference_set_size=12)
    assert low is not None
    assert low.severity == Severity.LOW
    assert low.confidence == Decimal("0.50")
    assert low.code == SignalCode.VISUAL_ANOMALY_DETECTED
    assert low.category == SignalCategory.VISUAL

    just_below_medium = _derive_signal(cosine_distance=Decimal("0.4499"), reference_set_size=12)
    assert just_below_medium is not None
    assert just_below_medium.severity == Severity.LOW

    medium = _derive_signal(cosine_distance=Decimal("0.45"), reference_set_size=12)
    assert medium is not None
    assert medium.severity == Severity.MEDIUM
    assert medium.confidence == Decimal("0.70")

    high_distance = _derive_signal(cosine_distance=Decimal("0.90"), reference_set_size=12)
    assert high_distance is not None
    assert high_distance.severity == Severity.MEDIUM


def test_visual_outlier_signal_shape_matches_design_evidence_fields() -> None:
    signal = _derive_signal(cosine_distance=Decimal("0.52"), reference_set_size=12)
    assert signal is not None
    assert signal.evidence["cosine_distance"] == "0.52"
    assert signal.evidence["threshold"] == "0.45"
    assert signal.evidence["reference_set_version"] == "v1"
    assert signal.evidence["reference_set_size"] == "12"
    assert "AI-generated" not in signal.description
    assert "fake" not in signal.description.lower()


def test_adapter_emits_no_signal_when_close_to_reference_set(tmp_path: Path) -> None:
    reference = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)

    def _fake_embed(path: Path) -> np.ndarray:
        return np.array([0.99, 0.01, 0.0, 0.0], dtype=np.float32) / np.linalg.norm(
            [0.99, 0.01, 0.0, 0.0]
        )

    adapter = MobileNetV3VisionAdapter(embed=_fake_embed, reference_embeddings=reference)
    result = _extract(adapter, _make_image(tmp_path))

    assert result.status == "completed"
    assert result.signals == ()


def test_adapter_emits_visual_anomaly_signal_when_far_from_reference_set(tmp_path: Path) -> None:
    reference = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)

    def _fake_embed(path: Path) -> np.ndarray:
        vector = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)
        return vector / np.linalg.norm(vector)

    adapter = MobileNetV3VisionAdapter(embed=_fake_embed, reference_embeddings=reference)
    result = _extract(adapter, _make_image(tmp_path))

    assert result.status == "completed"
    assert len(result.signals) == 1
    assert result.signals[0].code == SignalCode.VISUAL_ANOMALY_DETECTED


def test_adapter_only_accepts_validated_safeimageref_path_never_client_supplied(
    tmp_path: Path,
) -> None:
    """The adapter's `inspect` signature only accepts a `SafeImageRef`
    (already validated/decoded by the ingestion path) -- there is no
    parameter that lets a caller pass an arbitrary client-supplied path
    string directly into the embedder."""
    import inspect as inspect_module

    signature = inspect_module.signature(MobileNetV3VisionAdapter.inspect)
    params = list(signature.parameters.values())
    assert [p.name for p in params] == ["self", "image"]
    assert params[1].annotation in ("SafeImageRef", SafeImageRef)
