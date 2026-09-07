"""Real-model vision integration test.

Runs `MobileNetV3VisionAdapter` against the actual MobileNetV3-Small
checkpoint and the actual committed fixture bytes -- no injected fake
`embed`, unlike every test in `tests/unit/test_vision_mobilenet.py`.
Requires `RECEIPT_RISK_VISION_MODEL_DIR` to point at a real baked
`mobilenet_v3_small.pth` (CI fetches this via
`scripts/fetch_vision_model.py`; skipped locally when unset). Mirrors
`test_ocr_integration.py`'s skip pattern.
"""

from __future__ import annotations

import os
from pathlib import Path

import anyio
import numpy as np
import pytest
from PIL import Image

from conftest import fixture
from receipt_risk.adapters.vision.mobilenet_embedder import (
    OUTLIER_THRESHOLD,
    MobileNetV3VisionAdapter,
)
from receipt_risk.application.models import SafeImageRef

pytestmark = pytest.mark.skipif(
    not os.environ.get("RECEIPT_RISK_VISION_MODEL_DIR"),
    reason=(
        "RECEIPT_RISK_VISION_MODEL_DIR not set -- CI fetches baked weights, this sandbox does not"
    ),
)

_REFERENCE_FIXTURE_IDS = (
    "reference_bank2_clean",
    "reference_bank2_degraded",
    "reference_compact_clean",
    "reference_compact_degraded",
    "reference_dark_header_clean",
    "reference_dark_header_degraded",
)


def _ref_for(fixture) -> SafeImageRef:
    with Image.open(fixture.path) as img:
        width, height = img.size
    return SafeImageRef(
        path=fixture.path,
        sha256=fixture.sha256,
        media_type="image/jpeg" if fixture.path.suffix == ".jpg" else "image/png",
        width=width,
        height=height,
        byte_size=fixture.path.stat().st_size,
    )


@pytest.mark.parametrize("fixture_id", _REFERENCE_FIXTURE_IDS)
def test_every_reference_fixture_scores_below_outlier_threshold(fixture_id: str) -> None:
    fixture_record = fixture(fixture_id)
    adapter = MobileNetV3VisionAdapter()

    result = anyio.run(adapter.inspect, _ref_for(fixture_record))

    assert result.status == "completed"
    # Every reference fixture is one of the images the reference set was
    # built from (or a close variant), so its distance to its own set must
    # sit strictly below the outlier threshold -- no VISUAL_ANOMALY_DETECTED
    # signal for its own reference images.
    for signal in result.signals:
        evidence_distance = float(signal.evidence["cosine_distance"])
        is_outlier_code = signal.code != "VISUAL_ANOMALY_DETECTED"
        assert evidence_distance < float(OUTLIER_THRESHOLD) or is_outlier_code


def test_real_vision_inference_makes_zero_outbound_network_connections() -> None:
    """Extends the zero-outbound-network guarantee (already proven for OCR
    by `test_ocr_paddle_onnx.py::test_ocr_analysis_makes_zero_outbound_
    network_connections`) to the vision adapter's real inference path: the
    embedder loads local weights and reads the local reference-embedding
    JSON artifact, never touching the network."""
    import socket

    clean = fixture("clean_valid_transfer")
    _LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
    _real_connect = socket.socket.connect

    def _guarded_connect(self: socket.socket, address: object, *args: object, **kwargs: object):
        host = address[0] if isinstance(address, tuple) else address
        if host not in _LOOPBACK_HOSTS:
            raise AssertionError("vision analysis attempted an outbound network connection")
        return _real_connect(self, address, *args, **kwargs)

    original_connect = socket.socket.connect
    socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
    try:
        adapter = MobileNetV3VisionAdapter()
        result = anyio.run(adapter.inspect, _ref_for(clean))
    finally:
        socket.socket.connect = original_connect  # type: ignore[method-assign]

    assert result.status == "completed"


def test_off_domain_image_scores_higher_than_reference_fixtures(tmp_path: Path) -> None:
    rng = np.random.default_rng(42)
    noise = (rng.random((600, 400, 3)) * 255).astype(np.uint8)
    noise_path = tmp_path / "off_domain_noise.png"
    Image.fromarray(noise).save(noise_path)
    noise_ref = SafeImageRef(
        path=noise_path, sha256="x", media_type="image/png", width=400, height=600, byte_size=1
    )

    adapter = MobileNetV3VisionAdapter()
    result = anyio.run(adapter.inspect, noise_ref)

    assert result.status == "completed"
    assert len(result.signals) == 1
    assert result.signals[0].code == "VISUAL_ANOMALY_DETECTED"
