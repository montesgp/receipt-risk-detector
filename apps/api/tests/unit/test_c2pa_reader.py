"""Unit tests for `adapters.provenance.c2pa_reader`'s pure signal derivation.

Traces to spec.md's "Valid AI-generated provenance claim" scenario and
AGENTS.md's invariant that a valid AI-generation claim alone is a critical
signal, never proof about the underlying bank transaction. Per design.md's
open question, the signed-asset integration path is unit-tested here against
a captured manifest JSON dict (no real signed C2PA fixture exists yet); the
real-`Reader` integration test is skip-marked separately.
"""

from __future__ import annotations

import anyio

from receipt_risk.adapters.provenance.c2pa_reader import C2paProvenanceAdapter, _derive_signals
from receipt_risk.application.models import SafeImageRef
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode


def test_c2pa_missing_manifest_emits_no_signal() -> None:
    assert _derive_signals(None) == ()


def test_c2pa_valid_ai_generated_claim_emits_critical_signal() -> None:
    manifest = {
        "active_manifest": "urn:uuid:valid-ai",
        "manifests": {
            "urn:uuid:valid-ai": {
                "validation_status": [],  # empty = claim verified
                "assertions": [
                    {
                        "label": "stds.iptc.photo-metadata",
                        "data": {
                            "Iptc4xmpExt:DigitalSourceType": (
                                "http://cv.iptc.org/newscodes/digitalsourcetype/"
                                "trainedAlgorithmicMedia"
                            )
                        },
                    }
                ],
            }
        },
    }

    signals = _derive_signals(manifest)

    assert len(signals) == 1
    assert signals[0].code == SignalCode.VALID_AI_GENERATED_CLAIM
    assert signals[0].severity == Severity.CRITICAL
    assert signals[0].category == SignalCategory.PROVENANCE


def test_c2pa_failed_validation_emits_lower_severity_non_critical_signal() -> None:
    manifest = {
        "active_manifest": "urn:uuid:tampered",
        "manifests": {
            "urn:uuid:tampered": {
                "validation_status": [
                    {"code": "assertion.dataHash.mismatch", "explanation": "hash mismatch"}
                ],
                "assertions": [
                    {
                        "label": "stds.iptc.photo-metadata",
                        "data": {
                            "Iptc4xmpExt:DigitalSourceType": (
                                "http://cv.iptc.org/newscodes/digitalsourcetype/"
                                "trainedAlgorithmicMedia"
                            )
                        },
                    }
                ],
            }
        },
    }

    signals = _derive_signals(manifest)

    assert len(signals) == 1
    assert signals[0].code == SignalCode.PROVENANCE_VALIDATION_FAILED
    assert signals[0].severity != Severity.CRITICAL


def test_c2pa_inspect_sets_evidence_observed_true_when_manifest_found(
    tmp_path, monkeypatch
) -> None:
    import receipt_risk.adapters.provenance.c2pa_reader as c2pa_reader_module

    monkeypatch.setattr(
        c2pa_reader_module, "_read_manifest", lambda path: {"active_manifest": None}
    )

    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"not-a-real-image")
    safe = SafeImageRef(
        path=image_path, sha256="x" * 64, media_type="image/png", width=1, height=1, byte_size=17
    )

    result = anyio.run(C2paProvenanceAdapter().inspect, safe)

    assert result.evidence_observed is True


def test_c2pa_inspect_sets_evidence_observed_false_when_no_manifest(tmp_path, monkeypatch) -> None:
    import receipt_risk.adapters.provenance.c2pa_reader as c2pa_reader_module

    monkeypatch.setattr(c2pa_reader_module, "_read_manifest", lambda path: None)

    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"not-a-real-image")
    safe = SafeImageRef(
        path=image_path, sha256="x" * 64, media_type="image/png", width=1, height=1, byte_size=17
    )

    result = anyio.run(C2paProvenanceAdapter().inspect, safe)

    assert result.evidence_observed is False


def test_c2pa_valid_manifest_without_ai_claim_emits_no_signal() -> None:
    manifest = {
        "active_manifest": "urn:uuid:camera",
        "manifests": {
            "urn:uuid:camera": {
                "validation_status": [],
                "assertions": [
                    {
                        "label": "stds.iptc.photo-metadata",
                        "data": {
                            "Iptc4xmpExt:DigitalSourceType": (
                                "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture"
                            )
                        },
                    }
                ],
            }
        },
    }

    assert _derive_signals(manifest) == ()
