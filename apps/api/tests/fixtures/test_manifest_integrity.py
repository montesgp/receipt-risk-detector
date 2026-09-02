"""Fixture manifest integrity tests.

Traces to design.md's fixture design: `samples/manifest.json` records a
sha256 per fixture so drift between the committed image bytes and the
manifest is detected in CI rather than silently changing OCR-dependent test
expectations.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parents[4] / "samples"
MANIFEST_PATH = SAMPLES_DIR / "manifest.json"


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_every_fixture_sha256_matches_committed_bytes() -> None:
    manifest = _load_manifest()
    assert manifest["fixtures"], "manifest must declare at least one fixture"

    for fixture in manifest["fixtures"]:
        image_path = SAMPLES_DIR / fixture["path"]
        assert image_path.exists(), f"missing fixture file: {fixture['path']}"
        actual_sha256 = hashlib.sha256(image_path.read_bytes()).hexdigest()
        assert actual_sha256 == fixture["sha256"], (
            f"sha256 drift for fixture '{fixture['id']}': "
            f"manifest says {fixture['sha256']}, file is {actual_sha256}"
        )


def test_manifest_declares_the_three_minimum_slice1_fixtures() -> None:
    manifest = _load_manifest()
    fixture_ids = {fixture["id"] for fixture in manifest["fixtures"]}

    assert "clean_valid_transfer" in fixture_ids
    assert "invalid_cbu_check_digit" in fixture_ids
    assert "corrupted_truncated" in fixture_ids
