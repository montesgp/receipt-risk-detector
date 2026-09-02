"""`c2pa-python` Reader-only adapter — `ProvenancePort` implementation.

Adapters own every framework/tool import per `docs/ARCHITECTURE.md` §5;
`c2pa` is allowed here only via the `TID251` per-file-ignore on
`adapters/**` and is banned everywhere else (pyproject.toml banned-api).

Only `Reader` is imported — no `Builder`, no signer, no CLI subprocess
(design.md "Provenance adapter"). `VALID_AI_GENERATED_CLAIM` (critical) fires
only when the active manifest validates cleanly (empty `validation_status`)
AND declares an algorithmic `digitalSourceType`. A manifest present but
failing validation is itself suspicious — tampering with a signed asset, or a
broken signature — so it emits `PROVENANCE_VALIDATION_FAILED` at a
non-critical severity; design.md's code table lists only the two AI-claim
codes for slice 2, but its prose explicitly requires "a separate
lower-severity signal" for the failed-validation case, so this code was
added (documented apply-time deviation). A missing/undecodable manifest is
neutral per spec.md's "Missing metadata is neutral" scenario — it emits
nothing, never an error.
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import anyio
from c2pa import Reader

from receipt_risk.application.models import SafeImageRef
from receipt_risk.domain.analysis import AnalyzerResult
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode, ValidationSignal

# IPTC digitalSourceType URIs (or their trailing path segment) that indicate
# algorithmic/AI-composited media. Not exhaustive — a documented default per
# the proposal's "reasonable defaults, not fake precision" stance.
_ALGORITHMIC_SOURCE_MARKERS: Final[tuple[str, ...]] = (
    "trainedalgorithmicmedia",
    "compositewithtrainedalgorithmicmedia",
    "algorithmicmedia",
)


def _read_manifest(path: Path) -> dict[str, Any] | None:
    try:
        with Reader(str(path)) as reader:
            return json.loads(reader.json())
    except Exception:  # noqa: BLE001 — no manifest / unsupported format is neutral, not an error
        return None


def _has_algorithmic_source_claim(manifest_entry: dict[str, Any]) -> bool:
    for assertion in manifest_entry.get("assertions", []):
        data = assertion.get("data", {})
        source_type = str(data.get("Iptc4xmpExt:DigitalSourceType", "")).lower()
        if any(marker in source_type for marker in _ALGORITHMIC_SOURCE_MARKERS):
            return True
    return False


def _derive_signals(manifest: dict[str, Any] | None) -> tuple[ValidationSignal, ...]:
    if manifest is None:
        return ()

    active_label = manifest.get("active_manifest")
    manifests = manifest.get("manifests", {})
    active = manifests.get(active_label) if active_label else None
    if active is None:
        return ()

    validation_status = active.get("validation_status", [])
    is_ai_claim = _has_algorithmic_source_claim(active)

    if not is_ai_claim:
        return ()

    if not validation_status:
        return (
            ValidationSignal(
                code=SignalCode.VALID_AI_GENERATED_CLAIM,
                category=SignalCategory.PROVENANCE,
                severity=Severity.CRITICAL,
                confidence=Decimal("1.00"),
                description=(
                    "A valid Content Credentials (C2PA) manifest declares this "
                    "image as algorithmically generated or composited."
                ),
                evidence={"active_manifest": str(active_label)},
            ),
        )

    return (
        ValidationSignal(
            code=SignalCode.PROVENANCE_VALIDATION_FAILED,
            category=SignalCategory.PROVENANCE,
            severity=Severity.MEDIUM,
            confidence=Decimal("0.60"),
            description=(
                "A Content Credentials (C2PA) manifest is present but failed "
                "validation; its provenance claims cannot be trusted."
            ),
            evidence={"active_manifest": str(active_label)},
        ),
    )


def _elapsed_ms(started_monotonic: float) -> int:
    return int((time.monotonic() - started_monotonic) * 1000)


class C2paProvenanceAdapter:
    """Concrete `ProvenancePort` implementation."""

    name = "c2pa"
    version = "1.0.0"

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        started = time.monotonic()
        manifest = await anyio.to_thread.run_sync(_read_manifest, image.path)
        return AnalyzerResult(
            analyzer=self.name,
            version=self.version,
            status="completed",
            signals=_derive_signals(manifest),
            duration_ms=_elapsed_ms(started),
        )
