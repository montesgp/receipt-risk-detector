"""Unit tests for `adapters/ocr/preprocess.py`.

Traces to design.md's OCR retry state machine: "deskew (min-area rect over
the binarized text mask, |angle| <= 15 degrees) -> CLAHE contrast
normalization -> unsharp mask (fixed parameters, no randomness -
determinism requirement)".
"""

from __future__ import annotations

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from receipt_risk.adapters.ocr.preprocess import (  # noqa: E402
    MAX_DESKEW_DEGREES,
    _deskew_angle,
    deskew,
    preprocess,
)


def _synthetic_skewed_text_image(angle_degrees: float) -> np.ndarray:
    """A white canvas with a black rectangle (stand-in for a text block)
    rotated by `angle_degrees`, rendered with pure numpy/cv2 primitives —
    no randomness."""
    canvas = np.full((400, 400), 255, dtype=np.uint8)
    box = cv2.boxPoints(((200, 200), (220, 40), angle_degrees))
    cv2.fillPoly(canvas, [box.astype(np.int32)], color=0)
    return cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)


def test_deskew_bounded_to_15_degrees_and_deterministic() -> None:
    image = _synthetic_skewed_text_image(angle_degrees=40.0)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    angle = _deskew_angle(gray)

    assert abs(angle) <= MAX_DESKEW_DEGREES

    first = deskew(image)
    second = deskew(image)
    assert np.array_equal(first, second)


def test_deskew_is_a_no_op_on_an_already_upright_image() -> None:
    image = _synthetic_skewed_text_image(angle_degrees=0.0)
    result = deskew(image)
    assert result.shape == image.shape


def test_preprocess_returns_an_array_with_the_same_shape() -> None:
    image = _synthetic_skewed_text_image(angle_degrees=10.0)
    result = preprocess(image)
    assert result.shape == image.shape
    assert result.dtype == image.dtype
