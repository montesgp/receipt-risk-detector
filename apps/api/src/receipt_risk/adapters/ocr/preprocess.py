"""Bounded, deterministic preprocessing applied on the OCR adapter's single
retry attempt (slice 3b). Adapter-only per `docs/ARCHITECTURE.md` §5: `cv2`
never crosses into `domain/` or `application/` (ruff banned-api).

Traces to design.md's OCR retry state machine: "deskew (min-area rect over
the binarized text mask, |angle| <= 15 degrees) -> CLAHE contrast
normalization -> unsharp mask (fixed parameters, no randomness -
determinism requirement)". Every parameter below is a literal constant —
there is no random or time-based input anywhere in this module, so calling
`preprocess` twice on the same array always returns byte-identical output.
"""

from __future__ import annotations

import cv2  # noqa: TID251 -- adapters/** is exempt, see pyproject.toml
import numpy as np

MAX_DESKEW_DEGREES: float = 15.0
CLAHE_CLIP_LIMIT: float = 2.0
CLAHE_TILE_GRID_SIZE: tuple[int, int] = (8, 8)
UNSHARP_AMOUNT: float = 1.5
UNSHARP_SIGMA: float = 1.0


def _to_gray(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image


def _deskew_angle(gray: np.ndarray) -> float:
    """Estimate the skew angle from the min-area rect of the binarized text
    mask, clamped to `+-MAX_DESKEW_DEGREES`. Returns `0.0` when no
    foreground pixels are found (a blank/near-blank image)."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    coords = cv2.findNonZero(binary)
    if coords is None:
        return 0.0

    rect_angle = cv2.minAreaRect(coords)[-1]
    # cv2.minAreaRect reports an angle in [-90, 0); normalize to the
    # nearest-axis rotation that would make the box upright.
    angle = -(90 + rect_angle) if rect_angle < -45 else -rect_angle
    return max(-MAX_DESKEW_DEGREES, min(MAX_DESKEW_DEGREES, angle))


def deskew(image: np.ndarray) -> np.ndarray:
    """Rotate `image` to correct skew, bounded to
    `+-MAX_DESKEW_DEGREES` (design.md: never an unbounded correction)."""
    angle = _deskew_angle(_to_gray(image))
    if angle == 0.0:
        return image
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(
        image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def normalize_contrast(image: np.ndarray) -> np.ndarray:
    """Apply CLAHE contrast normalization with fixed parameters."""
    is_color = image.ndim == 3
    gray = _to_gray(image)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID_SIZE)
    equalized = clahe.apply(gray)
    return cv2.cvtColor(equalized, cv2.COLOR_GRAY2BGR) if is_color else equalized


def sharpen(image: np.ndarray) -> np.ndarray:
    """Fixed-parameter unsharp mask."""
    blurred = cv2.GaussianBlur(image, (0, 0), UNSHARP_SIGMA)
    return cv2.addWeighted(image, 1 + UNSHARP_AMOUNT, blurred, -UNSHARP_AMOUNT, 0)


def preprocess(image: np.ndarray) -> np.ndarray:
    """The single bounded preprocessing pass applied on the OCR adapter's
    one retry attempt: deskew -> CLAHE -> unsharp mask, in that order."""
    return sharpen(normalize_contrast(deskew(image)))
