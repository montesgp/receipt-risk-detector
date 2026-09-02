#!/usr/bin/env python3
"""Fetch and verify the pinned OCR model set for `adapters/ocr/paddle_onnx.py`.

Downloads the exact PP-OCRv4 (mobile) detection/classification/recognition
ONNX models RapidOCR ships, verifies each against a pinned sha256, and
writes them to `--dest` as `det.onnx`, `cls.onnx`, `rec.onnx` -- the exact
filenames `PaddleOnnxOcrAdapter._load_rapidocr_engine` expects.

This is a BUILD-TIME step only (Dockerfile's `ocr-models` stage, CI's model
cache/fetch step). The running adapter never downloads anything itself --
see `paddle_onnx.py`'s `OcrEngineUnavailable` fail-closed check and the
"zero outbound network connections during analysis" threat-matrix test.

The model URLs and sha256 hashes below were verified by hand: each file was
downloaded and hashed independently, and its first bytes were inspected to
confirm real ONNX/protobuf content (not an HTML error page) before pinning.
Re-verify both if this pin is ever bumped.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

# Pinned at RapidOCR v3.9.2's ModelScope release. Bump deliberately, never
# silently -- re-download and re-hash by hand before changing these values.
_MODELSCOPE_BASE = "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/onnx"


@dataclass(frozen=True, slots=True)
class _PinnedModel:
    dest_filename: str
    url: str
    sha256: str


_PINNED_MODELS: tuple[_PinnedModel, ...] = (
    _PinnedModel(
        dest_filename="det.onnx",
        url=f"{_MODELSCOPE_BASE}/PP-OCRv4/det/ch_PP-OCRv4_det_mobile.onnx",
        sha256="d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9",
    ),
    _PinnedModel(
        dest_filename="cls.onnx",
        url=f"{_MODELSCOPE_BASE}/PP-OCRv4/cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx",
        sha256="e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c",
    ),
    _PinnedModel(
        dest_filename="rec.onnx",
        url=f"{_MODELSCOPE_BASE}/PP-OCRv4/rec/ch_PP-OCRv4_rec_mobile.onnx",
        sha256="48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b",
    ),
)


class ModelVerificationError(Exception):
    """Raised when a downloaded model's sha256 does not match the pin."""


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: Path, *, timeout_s: int = 60) -> None:
    with requests.get(url, stream=True, timeout=timeout_s) as response:
        response.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                fh.write(chunk)


def fetch_models(dest_dir: Path, *, verify: bool) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)

    for model in _PINNED_MODELS:
        dest_path = dest_dir / model.dest_filename

        if dest_path.is_file() and verify and _sha256_of(dest_path) == model.sha256:
            print(f"[fetch_ocr_models] {model.dest_filename}: already present, sha256 matches")
            continue

        print(f"[fetch_ocr_models] {model.dest_filename}: downloading from {model.url}")
        _download(model.url, dest_path)

        if verify:
            actual = _sha256_of(dest_path)
            if actual != model.sha256:
                raise ModelVerificationError(
                    f"{model.dest_filename}: sha256 mismatch -- "
                    f"expected {model.sha256}, got {actual}. "
                    "Refusing to use an unverified model file."
                )
            print(f"[fetch_ocr_models] {model.dest_filename}: sha256 verified")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Directory to write det.onnx, cls.onnx, rec.onnx into.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify each downloaded (or already-present) file's sha256 against the pin.",
    )
    args = parser.parse_args(argv)

    try:
        fetch_models(args.dest, verify=args.verify)
    except ModelVerificationError as exc:
        print(f"[fetch_ocr_models] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
