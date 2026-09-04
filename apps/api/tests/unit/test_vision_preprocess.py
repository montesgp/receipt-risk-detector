"""Unit tests for `adapters/vision/preprocess.py`'s deterministic PIL-only
preprocessing pipeline.

Traces to design.md's Data Flow: "PIL open -> RGB -> resize 256 ->
center-crop 224 -> ImageNet normalise". No cv2, no torch import here — the
adapter converts the resulting numpy array to a tensor only at inference
time, mirroring `adapters/ocr/preprocess.py`'s pure, deterministic style
(no RNG, no system state).
"""

from __future__ import annotations

import hashlib
import io

import numpy as np
from PIL import Image

from receipt_risk.adapters.vision.preprocess import IMAGE_SIZE, preprocess


def _png_bytes(*, width: int, height: int, color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (width, height), color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_preprocessing_deterministic_same_bytes_identical_tensor_hash(tmp_path) -> None:
    data = _png_bytes(width=400, height=300, color=(120, 40, 200))
    path = tmp_path / "receipt.png"
    path.write_bytes(data)

    first = preprocess(path)
    second = preprocess(path)

    first_hash = hashlib.sha256(first.tobytes()).hexdigest()
    second_hash = hashlib.sha256(second.tobytes()).hexdigest()
    assert first_hash == second_hash


def test_preprocess_output_shape_is_chw_224() -> None:
    data = _png_bytes(width=800, height=200, color=(10, 200, 30))
    path = "irrelevant"  # overwritten below

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "wide.png"
        path.write_bytes(data)
        result = preprocess(path)

    assert result.shape == (3, IMAGE_SIZE, IMAGE_SIZE)
    assert result.dtype == np.float32


def test_preprocess_normalizes_with_imagenet_stats_not_raw_0_255() -> None:
    data = _png_bytes(width=224, height=224, color=(255, 255, 255))
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "white.png"
        path.write_bytes(data)
        result = preprocess(path)

    # A pure white pixel normalized by ImageNet mean/std must not remain 1.0/255.0-ish;
    # it lands roughly in the (2.0, 2.7) range per channel for the documented stats.
    assert result.max() > 1.5
    assert result.min() > -3.0
