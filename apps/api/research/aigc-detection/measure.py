#!/usr/bin/env python3
"""Data-collection skeleton for the AI-regeneration detection research
(issue #67). Not a detector -- computes and dumps raw per-text-box geometry
for every sample in `manifest.json` so real-vs-fake comparison has actual
numbers to work from once enough samples exist. See README.md.

Reuses the exact RapidOCR engine the production adapter uses
(`adapters/ocr/paddle_onnx.py`), but talks to it one level lower than that
adapter does: `boxes_from_engine_output` (the production parser) keeps only
`text`/`confidence`/`top`/`left` because that's all field-extraction needs --
it throws away box width/height/rotation, which is exactly what a
font/kerning comparison needs. This script reads the raw engine rows
directly instead.

Usage:
    uv run python research/aigc-detection/measure.py
    uv run python research/aigc-detection/measure.py --model-dir /path/to/ocr-models
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_API_SRC = _SCRIPT_DIR.parent.parent / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

_MANIFEST_PATH = _SCRIPT_DIR / "manifest.json"
_MEASUREMENTS_DIR = _SCRIPT_DIR / "measurements"


def _box_geometry(points: list[list[float]]) -> dict[str, float]:
    """Derive width/height/rotation from a RapidOCR-style 4-point polygon
    (top-left, top-right, bottom-right, bottom-left, clockwise) -- the
    geometry `RawTextBox` (production's parser) discards."""
    import math

    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = points
    top_width = math.hypot(x1 - x0, y1 - y0)
    bottom_width = math.hypot(x2 - x3, y2 - y3)
    left_height = math.hypot(x3 - x0, y3 - y0)
    right_height = math.hypot(x2 - x1, y2 - y1)
    rotation_deg = math.degrees(math.atan2(y1 - y0, x1 - x0))
    return {
        "top": min(y0, y1, y2, y3),
        "left": min(x0, x1, x2, x3),
        "width": (top_width + bottom_width) / 2,
        "height": (left_height + right_height) / 2,
        "rotation_deg": rotation_deg,
    }


def _measure_one(image_path: Path, run_engine: Any) -> list[dict[str, Any]]:
    from receipt_risk.adapters.ocr.paddle_onnx import _read_pixels

    pixels = _read_pixels(image_path)
    raw_rows = run_engine(pixels)

    boxes: list[dict[str, Any]] = []
    for row in raw_rows:
        try:
            points, text, score = row
        except (TypeError, ValueError):
            continue
        geometry = _box_geometry(points)
        boxes.append({"text": text, "confidence": float(score), **geometry})
    return boxes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=None,
        help="OCR model dir (det/cls/rec.onnx). Defaults to RECEIPT_RISK_OCR_MODEL_DIR.",
    )
    args = parser.parse_args(argv)

    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    samples = manifest.get("samples", [])
    if not samples:
        print(
            "[measure] manifest.json has no samples yet -- nothing to measure. "
            "See README.md / issue #68.",
            file=sys.stderr,
        )
        return 0

    from receipt_risk.adapters.ocr.paddle_onnx import _load_rapidocr_engine, _model_dir_from_env

    model_dir = args.model_dir or _model_dir_from_env()
    run_engine = _load_rapidocr_engine(model_dir)

    _MEASUREMENTS_DIR.mkdir(exist_ok=True)
    for sample in samples:
        image_path = _SCRIPT_DIR / sample["path"]
        if not image_path.is_file():
            print(
                f"[measure] missing file for sample '{sample['id']}': {image_path}",
                file=sys.stderr,
            )
            continue

        boxes = _measure_one(image_path, run_engine)
        out_path = _MEASUREMENTS_DIR / f"{sample['id']}.json"
        out_path.write_text(
            json.dumps({"sample_id": sample["id"], "boxes": boxes}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"[measure] {sample['id']}: {len(boxes)} boxes -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
