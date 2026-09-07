"""Tests for `bootstrap/app.py`'s `/ready` and `/version` analyzer roster,
verifying the vision analyzer is wired alongside ocr/metadata/provenance
(public-api-contract spec: "Analyzer readiness roster").
"""

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

import receipt_risk.bootstrap.app as bootstrap_app
from receipt_risk.adapters.ocr.paddle_onnx import PaddleOnnxOcrAdapter
from receipt_risk.adapters.vision.mobilenet_embedder import MobileNetV3VisionAdapter
from receipt_risk.bootstrap.app import app

# The bare `TestClient(app)` form below is deliberate: under the pinned
# Starlette 1.6.0, only `with TestClient(app) as client:` sends the ASGI
# "lifespan.startup" message (see design.md's "TestClient / lifespan: settled
# from source"), so these three tests never trigger real warmup -- fast, no
# real model load, unaffected by this change.


def test_ready_endpoint_reports_four_analyzers_including_vision() -> None:
    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 200
    analyzers = response.json()["analyzers"]
    assert set(analyzers) == {"ocr", "metadata", "provenance", "vision"}
    assert analyzers["vision"].startswith("mobilenetv3-embedding/")


def test_version_endpoint_includes_vision_analyzer_entry() -> None:
    client = TestClient(app)
    response = client.get("/version")

    assert response.status_code == 200
    body = response.json()
    assert "engine_version" in body
    assert "ruleset_version" in body
    assert set(body["analyzers"]) == {"ocr", "metadata", "provenance", "vision"}


def test_version_endpoint_reports_active_ruleset_2026_09_06() -> None:
    client = TestClient(app)
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["ruleset_version"] == "2026-09-07"


def test_lifespan_warms_ocr_and_vision_concurrently(monkeypatch: pytest.MonkeyPatch) -> None:
    windows: dict[str, tuple[float, float]] = {}

    async def _make_spy(name: str, delay_s: float):
        async def _spy() -> None:
            entered = time.monotonic()
            await asyncio.sleep(delay_s)
            exited = time.monotonic()
            windows[name] = (entered, exited)

        return _spy

    ocr_spy = asyncio.run(_make_spy("ocr", 0.05))
    vision_spy = asyncio.run(_make_spy("vision", 0.05))
    ocr_calls = 0
    vision_calls = 0

    async def _ocr_wrapper() -> None:
        nonlocal ocr_calls
        ocr_calls += 1
        await ocr_spy()

    async def _vision_wrapper() -> None:
        nonlocal vision_calls
        vision_calls += 1
        await vision_spy()

    monkeypatch.setattr(bootstrap_app._ocr, "warmup", _ocr_wrapper)
    monkeypatch.setattr(bootstrap_app._vision, "warmup", _vision_wrapper)

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200

    assert ocr_calls == 1
    assert vision_calls == 1
    ocr_start, ocr_end = windows["ocr"]
    vision_start, vision_end = windows["vision"]
    # Overlapping windows prove concurrent scheduling (max), not sequential (sum).
    assert ocr_start < vision_end
    assert vision_start < ocr_end


@pytest.mark.parametrize("missing_analyzer", ["ocr", "vision"])
def test_lifespan_missing_model_dir_still_starts_app(
    missing_analyzer: str, monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    bogus_dir = tmp_path / "does-not-exist"  # type: ignore[operator]
    if missing_analyzer == "ocr":
        monkeypatch.setattr(bootstrap_app, "_ocr", PaddleOnnxOcrAdapter(model_dir=bogus_dir))
    else:
        monkeypatch.setattr(bootstrap_app, "_vision", MobileNetV3VisionAdapter(model_dir=bogus_dir))

    with TestClient(app) as client:
        health_response = client.get("/health")
        ready_response = client.get("/ready")

    assert health_response.status_code == 200
    assert ready_response.status_code == 200


@pytest.mark.parametrize("missing_analyzer", ["ocr", "vision"])
def test_availability_contract_unchanged_after_failed_warmup(
    missing_analyzer: str, monkeypatch: pytest.MonkeyPatch, tmp_path: object
) -> None:
    from receipt_risk.application.models import SafeImageRef

    bogus_dir = tmp_path / "does-not-exist"  # type: ignore[operator]
    image_path = tmp_path / "receipt.png"  # type: ignore[operator]
    image_path.write_bytes(b"not-a-real-image")
    safe_image = SafeImageRef(
        path=image_path, sha256="deadbeef", media_type="image/png", width=1, height=1, byte_size=1
    )

    if missing_analyzer == "ocr":
        monkeypatch.setattr(bootstrap_app, "_ocr", PaddleOnnxOcrAdapter(model_dir=bogus_dir))
        with TestClient(app):
            result = asyncio.run(bootstrap_app._ocr.extract(safe_image))
    else:
        monkeypatch.setattr(bootstrap_app, "_vision", MobileNetV3VisionAdapter(model_dir=bogus_dir))
        with TestClient(app):
            result = asyncio.run(bootstrap_app._vision.inspect(safe_image))

    assert result.status == "failed"
    assert result.error_code == "ANALYZER_UNAVAILABLE"
