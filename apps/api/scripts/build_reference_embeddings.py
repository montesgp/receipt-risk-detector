#!/usr/bin/env python3
"""Build `adapters/vision/reference_embeddings_v1.json`: the committed,
versioned reference-embedding artifact `MobileNetV3VisionAdapter` compares
each analyzed receipt against (design.md "Reference set construction").

This is a BUILD-TIME step only, run by a maintainer whenever the reference
image set changes -- never at adapter startup (design.md's "Reference
embeddings" decision: computing them at startup would cost cold-start
seconds and make results depend on load order). Requires
`RECEIPT_RISK_VISION_MODEL_DIR` to point at a directory containing
`mobilenet_v3_small.pth` (see `fetch_vision_model.py`).

Usage:
    python scripts/build_reference_embeddings.py --model-dir /path/to/vision-model
    python scripts/build_reference_embeddings.py --model-dir ... --check   # drift check, no writes
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

_SCRIPT_DIR = Path(__file__).resolve().parent
_API_SRC = _SCRIPT_DIR.parent / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

_SAMPLES_DIR = _SCRIPT_DIR.parent.parent.parent / "samples"
_REFERENCE_IMAGES_DIR = _SAMPLES_DIR / "images" / "reference"
_OUTPUT_PATH = _API_SRC / "receipt_risk" / "adapters" / "vision" / "reference_embeddings_v1.json"

_SCHEMA_VERSION = 1
_MODEL_NAME = "mobilenetv3-embedding/1.0.0"
_EMBEDDING_DIM = 576


def _source_fixtures() -> list[Path]:
    if not _REFERENCE_IMAGES_DIR.is_dir():
        raise SystemExit(f"reference image directory not found: {_REFERENCE_IMAGES_DIR}")
    paths = sorted(_REFERENCE_IMAGES_DIR.glob("*.*"))
    if not paths:
        raise SystemExit(f"no reference images found under {_REFERENCE_IMAGES_DIR}")
    return paths


def build(model_dir: Path) -> dict[str, object]:
    from receipt_risk.adapters.vision.mobilenet_embedder import _load_embedder

    embed = _load_embedder(model_dir)
    fixtures = _source_fixtures()

    embeddings: list[list[float]] = []
    source_fixtures: list[str] = []
    for path in fixtures:
        vector = embed(path)
        assert vector.shape == (_EMBEDDING_DIM,), f"unexpected embedding shape for {path}"
        embeddings.append([round(float(x), 6) for x in vector])
        source_fixtures.append(f"samples/images/reference/{path.name}")

    return {
        "schema_version": _SCHEMA_VERSION,
        "model": _MODEL_NAME,
        "embedding_dim": _EMBEDDING_DIM,
        "source_fixtures": source_fixtures,
        "embeddings": embeddings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-dir",
        type=Path,
        required=True,
        help="Directory containing mobilenet_v3_small.pth (see fetch_vision_model.py).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify the committed artifact matches a fresh build; do not write anything.",
    )
    args = parser.parse_args(argv)

    artifact = build(args.model_dir)

    if args.check:
        if not _OUTPUT_PATH.is_file():
            print(f"[build_reference_embeddings] missing: {_OUTPUT_PATH}", file=sys.stderr)
            return 1
        committed = json.loads(_OUTPUT_PATH.read_text(encoding="utf-8"))
        fresh = np.asarray(artifact["embeddings"], dtype=np.float32)
        old = np.asarray(committed["embeddings"], dtype=np.float32)
        if fresh.shape != old.shape or not np.allclose(fresh, old, atol=1e-4):
            print(
                "[build_reference_embeddings] drift detected between committed and fresh build",
                file=sys.stderr,
            )
            return 1
        print("[build_reference_embeddings] committed artifact matches a fresh build.")
        return 0

    _OUTPUT_PATH.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    count = len(artifact["embeddings"])
    print(f"[build_reference_embeddings] wrote {count} embeddings to {_OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
