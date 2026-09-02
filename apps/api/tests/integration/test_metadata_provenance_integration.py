"""Integration tests for the metadata/provenance adapters against a real
`exiftool` binary and the committed `samples/` fixtures.

Traces to design.md's Testing Strategy: "Integration: ExifTool, C2PA, OCR
adapters — real binaries against committed samples/, skip-marked when the
binary is absent locally, required in CI." CI installs `libimage-exiftool-
perl` via `.github/workflows/ci.yml`'s "Install system dependencies" step;
locally (this sandbox has no `exiftool` on PATH) the test is skipped rather
than silently passing without exercising real behavior.
"""

from __future__ import annotations

import asyncio
import shutil

import pytest

from conftest import fixture as load_fixture
from receipt_risk.adapters.metadata.exiftool import ExifToolMetadataAdapter
from receipt_risk.adapters.provenance.c2pa_reader import C2paProvenanceAdapter
from receipt_risk.application.models import SafeImageRef

pytestmark = pytest.mark.skipif(
    shutil.which("exiftool") is None,
    reason="exiftool binary not on PATH — CI installs it, this sandbox does not",
)


def test_exiftool_inspects_real_fixture_without_metadata_neutrally() -> None:
    clean = load_fixture("clean_valid_transfer")
    safe = SafeImageRef(
        path=clean.path,
        sha256=clean.sha256,
        media_type="image/png",
        width=1080,
        height=1920,
        byte_size=len(clean.bytes),
    )

    result = asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    assert result.status == "completed"
    assert result.analyzer == "exiftool"


def test_c2pa_reader_inspects_real_fixture_without_manifest_neutrally() -> None:
    clean = load_fixture("clean_valid_transfer")
    safe = SafeImageRef(
        path=clean.path,
        sha256=clean.sha256,
        media_type="image/png",
        width=1080,
        height=1920,
        byte_size=len(clean.bytes),
    )

    result = asyncio.run(C2paProvenanceAdapter().inspect(safe))

    assert result.status == "completed"
    assert result.signals == ()  # synthetic fixture carries no C2PA manifest
