"""Shared pytest fixtures for `apps/api`.

Exposes `fixture(id)`: loads `samples/manifest.json` once per test session,
verifies every declared sha256 against the committed bytes (drift
detection), and returns a `Fixture` record for the requested id.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
MANIFEST_PATH = SAMPLES_DIR / "manifest.json"


@dataclass(frozen=True, slots=True)
class Fixture:
    id: str
    path: Path
    sha256: str
    declared_fields: dict[str, str] = field(default_factory=dict)
    expected_signals: list[dict[str, Any]] = field(default_factory=list)
    expected_analyzer_statuses: dict[str, str] = field(default_factory=dict)
    expected_classification: str | None = None
    expected_error: dict[str, Any] | None = None
    notes: str = ""

    @property
    def bytes(self) -> bytes:
        return self.path.read_bytes()


_manifest_cache: dict[str, Any] | None = None


def _load_manifest() -> dict[str, Any]:
    global _manifest_cache
    if _manifest_cache is None:
        _manifest_cache = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return _manifest_cache


def fixture(fixture_id: str) -> Fixture:
    """Return the `Fixture` record for `fixture_id`, verifying its sha256
    against the committed image bytes on every load (drift detection)."""
    manifest = _load_manifest()
    for entry in manifest["fixtures"]:
        if entry["id"] != fixture_id:
            continue
        image_path = SAMPLES_DIR / entry["path"]
        actual_sha256 = hashlib.sha256(image_path.read_bytes()).hexdigest()
        if actual_sha256 != entry["sha256"]:
            raise AssertionError(
                f"sha256 drift for fixture '{fixture_id}': "
                f"manifest says {entry['sha256']}, file is {actual_sha256}"
            )
        return Fixture(
            id=entry["id"],
            path=image_path,
            sha256=entry["sha256"],
            declared_fields=entry.get("declared_fields", {}),
            expected_signals=entry.get("expected_signals", []),
            expected_analyzer_statuses=entry.get("expected_analyzer_statuses", {}),
            expected_classification=entry.get("expected_classification"),
            expected_error=entry.get("expected_error"),
            notes=entry.get("notes", ""),
        )
    raise KeyError(f"Unknown fixture id: {fixture_id!r}")
