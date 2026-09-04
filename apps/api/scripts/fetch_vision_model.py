#!/usr/bin/env python3
"""Fetch and verify the pinned MobileNetV3-Small weights for
`adapters/vision/mobilenet_embedder.py`.

Downloads the exact `torchvision.models.mobilenet_v3_small` ImageNet
checkpoint, verifies it against a pinned sha256, and writes it to
`--dest` as `mobilenet_v3_small.pth` -- the exact filename
`MobileNetV3VisionAdapter._load_embedder` expects.

This is a BUILD-TIME step only (Dockerfile's `vision-model` stage, CI's
model cache/fetch step). The running adapter never downloads anything
itself -- see `mobilenet_embedder.py`'s `VisionEngineUnavailable`
fail-closed check and the "zero outbound network calls during visual
inspection" spec scenario. This script intentionally does NOT use
`torchvision`'s own weights-download machinery (`weights=...` enum) or
`torch.hub` -- both are a runtime network call in disguise; a plain
pinned-URL HTTP fetch keeps the network boundary explicit and auditable
(design.md's "Weight distribution" decision).

The URL and sha256 below were verified by hand: the file was downloaded
and hashed independently with `sha256sum`, and its first bytes were
inspected to confirm real PyTorch pickle/zip content (not an HTML error
page) before pinning. Re-verify both if this pin is ever bumped.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

# Pinned to torchvision 0.29's MobileNet_V3_Small_Weights.DEFAULT (IMAGENET1K_V1)
# checkpoint. Bump deliberately, never silently -- re-download and re-hash by
# hand before changing these values.
_WEIGHTS_URL = "https://download.pytorch.org/models/mobilenet_v3_small-047dcff4.pth"

# Hand-verified 2026-09-04: downloaded via `curl -sSL -o ... $_WEIGHTS_URL`
# then `sha256sum`, cross-checked that the URL's trailing hash segment
# ("047dcff4") is a prefix of this digest (torchvision's own naming
# convention), which it is.
_WEIGHTS_SHA256 = "047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f"

_DEST_FILENAME = "mobilenet_v3_small.pth"


@dataclass(frozen=True, slots=True)
class _PinnedModel:
    dest_filename: str
    url: str
    sha256: str


_PINNED_MODEL = _PinnedModel(dest_filename=_DEST_FILENAME, url=_WEIGHTS_URL, sha256=_WEIGHTS_SHA256)


class ModelVerificationError(Exception):
    """Raised when the downloaded weights file's sha256 does not match the pin."""


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: Path, *, timeout_s: int = 120) -> None:
    with requests.get(url, stream=True, timeout=timeout_s) as response:
        response.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                fh.write(chunk)


def fetch_model(dest_dir: Path, *, verify: bool) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / _PINNED_MODEL.dest_filename

    name = _PINNED_MODEL.dest_filename
    if dest_path.is_file() and verify and _sha256_of(dest_path) == _PINNED_MODEL.sha256:
        print(f"[fetch_vision_model] {name}: already present, sha256 matches")
        return

    print(f"[fetch_vision_model] {name}: downloading from {_PINNED_MODEL.url}")
    _download(_PINNED_MODEL.url, dest_path)

    if verify:
        actual = _sha256_of(dest_path)
        if actual != _PINNED_MODEL.sha256:
            raise ModelVerificationError(
                f"{_PINNED_MODEL.dest_filename}: sha256 mismatch -- "
                f"expected {_PINNED_MODEL.sha256}, got {actual}. "
                "Refusing to use an unverified model file."
            )
        print(f"[fetch_vision_model] {_PINNED_MODEL.dest_filename}: sha256 verified")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        required=True,
        help="Directory to write mobilenet_v3_small.pth into.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the downloaded (or already-present) file's sha256 against the pin.",
    )
    args = parser.parse_args(argv)

    try:
        fetch_model(args.dest, verify=args.verify)
    except ModelVerificationError as exc:
        print(f"[fetch_vision_model] ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
