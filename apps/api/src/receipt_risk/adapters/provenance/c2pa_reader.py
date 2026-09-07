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

`digitalSourceType` is read from two shapes (c2pa-ai-claim-detection
change): the flat IPTC assertion field (`Iptc4xmpExt:DigitalSourceType`,
claim-v1-style) AND the nested `c2pa.actions.v2` shape
(`assertions[].data.actions[].digitalSourceType`) real claim-v2 producers
(e.g. Google Gemini) actually use. Both are additive — a manifest matching
either shape is treated as an AI claim. `validation_status` is further
tiered by a fail-closed allowlist: empty status still means
`VALID_AI_GENERATED_CLAIM`; a status where every entry is a CA-trust-only
code (currently only `signingCredential.untrusted`) means
`AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` — the manifest is cryptographically
intact but signed by an unrecognized CA, which is direct evidence of AI
generation, just from an unfamiliar signer; any other status (including
`signingCredential.expired`, deliberately not allowlisted this slice) stays
in the strict `PROVENANCE_VALIDATION_FAILED` bucket.

`AnalyzerResult.evidence_observed` is set to `manifest is not None`: a clean
run with no manifest found (or an undecodable one) still returns
`status="completed"`, but nothing was actually evaluated, so
`evidence_observed=False` tells `domain/scoring.py::_completeness` not to
credit this role with coverage it never earned (scoring-confidence-
calibration change).
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
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
    "compositesynthetic",
)

# `validation_status` codes that mean "we do not recognize the signing CA",
# NOT "the asset or its signature is broken". Fail-closed allowlist: any code
# absent from this set keeps the whole manifest in the stricter
# PROVENANCE_VALIDATION_FAILED bucket. `signingCredential.expired` is
# deliberately NOT allowlisted this slice (design.md decision 2).
_CA_TRUST_ONLY_STATUS_CODES: Final[frozenset[str]] = frozenset({"signingCredential.untrusted"})


def _read_manifest(path: Path) -> dict[str, Any] | None:
    try:
        with Reader(str(path)) as reader:
            return json.loads(reader.json())
    except Exception:  # noqa: BLE001 — no manifest / unsupported format is neutral, not an error
        return None


def _iter_source_types(manifest_entry: dict[str, Any]) -> Iterator[str]:
    """Yield every lowercased `digitalSourceType` value declared by the
    manifest, across both shapes we have observed in the wild:

    * flat IPTC assertion data (`Iptc4xmpExt:DigitalSourceType`) — the
      original claim-v1 style shape the first three unit tests pin;
    * `c2pa.actions.v2` assertions, which nest the value per action under
      `data.actions[].digitalSourceType` — the shape a real Google Gemini
      `claim_version: 2` manifest actually uses.

    Additive by construction: a manifest declaring either shape (or both)
    yields all of its values, so no previously-detected claim is lost.
    """
    for assertion in manifest_entry.get("assertions", []):
        data = assertion.get("data", {})
        if not isinstance(data, dict):
            continue

        flat = data.get("Iptc4xmpExt:DigitalSourceType")
        if flat:
            yield str(flat).lower()

        actions = data.get("actions", [])
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            nested = action.get("digitalSourceType")
            if nested:
                yield str(nested).lower()


def _has_algorithmic_source_claim(manifest_entry: dict[str, Any]) -> bool:
    return any(
        marker in source_type
        for source_type in _iter_source_types(manifest_entry)
        for marker in _ALGORITHMIC_SOURCE_MARKERS
    )


def _is_ca_trust_only(validation_status: list[dict[str, Any]]) -> bool:
    """True when EVERY reported status entry is a CA-trust-only code.

    Worst-case precedence: a single non-allowlisted entry (hash mismatch,
    broken signature, expired credential) makes this False, keeping the
    manifest in the strict `PROVENANCE_VALIDATION_FAILED` bucket. Callers
    must have already established `validation_status` is non-empty.
    """
    return all(
        str(entry.get("code", "")) in _CA_TRUST_ONLY_STATUS_CODES
        for entry in validation_status
        if isinstance(entry, dict)
    ) and any(isinstance(entry, dict) for entry in validation_status)


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

    if _is_ca_trust_only(validation_status):
        return (
            ValidationSignal(
                code=SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER,
                category=SignalCategory.PROVENANCE,
                severity=Severity.CRITICAL,
                confidence=Decimal("0.85"),
                description=(
                    "A cryptographically intact Content Credentials (C2PA) "
                    "manifest declares this image as algorithmically "
                    "generated or composited, but it was signed by a "
                    "certificate authority this engine does not recognize."
                ),
                evidence={
                    "active_manifest": str(active_label),
                    "validation_status_codes": ",".join(
                        str(entry.get("code", "")) for entry in validation_status
                    ),
                },
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
            evidence_observed=manifest is not None,
        )
