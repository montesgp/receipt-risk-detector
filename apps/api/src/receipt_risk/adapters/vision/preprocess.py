"""Deterministic PIL-only preprocessing for the vision adapter (design.md
Data Flow: "PIL open -> RGB -> resize 256 -> center-crop 224 -> ImageNet
normalise"). Adapter-only per `docs/ARCHITECTURE.md` §5. No `torch` import
here -- the embedder converts this pure numpy output to a tensor only at
inference time (mirrors `adapters/ocr/preprocess.py`'s no-RNG,
no-system-state determinism invariant: identical bytes always produce a
byte-identical array).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

RESIZE_SHORT_SIDE: int = 256
IMAGE_SIZE: int = 224

# torchvision's documented ImageNet normalization constants.
_IMAGENET_MEAN: tuple[float, float, float] = (0.485, 0.456, 0.406)
_IMAGENET_STD: tuple[float, float, float] = (0.229, 0.224, 0.225)


def _resize_short_side(image: Image.Image, target: int) -> Image.Image:
    width, height = image.size
    if width <= height:
        new_width = target
        new_height = round(height * target / width)
    else:
        new_height = target
        new_width = round(width * target / height)
    return image.resize((new_width, new_height), Image.Resampling.BILINEAR)


def _center_crop(image: Image.Image, size: int) -> Image.Image:
    width, height = image.size
    left = (width - size) // 2
    top = (height - size) // 2
    return image.crop((left, top, left + size, top + size))


def preprocess(path: Path) -> np.ndarray:
    """Load the image at `path`, resize/crop/normalise it, and return a
    `(3, IMAGE_SIZE, IMAGE_SIZE)` float32 array in CHW order, ImageNet
    normalised. Deterministic: identical input bytes always produce a
    byte-identical output array."""
    with Image.open(path) as raw:
        image = raw.convert("RGB")
        image = _resize_short_side(image, RESIZE_SHORT_SIDE)
        image = _center_crop(image, IMAGE_SIZE)
        pixels = np.asarray(image, dtype=np.float32) / 255.0  # (H, W, 3)

    mean = np.array(_IMAGENET_MEAN, dtype=np.float32)
    std = np.array(_IMAGENET_STD, dtype=np.float32)
    normalized = (pixels - mean) / std
    return np.transpose(normalized, (2, 0, 1)).astype(np.float32, copy=False)  # (3, H, W)
