"""Unit tests for `adapters.provenance.c2pa_reader`'s pure signal derivation.

Traces to spec.md's "Valid AI-generated provenance claim" scenario and
AGENTS.md's invariant that a valid AI-generation claim alone is a critical
signal, never proof about the underlying bank transaction. Per design.md's
open question, the signed-asset integration path is unit-tested here against
a captured manifest JSON dict (no real signed C2PA fixture exists yet); the
real-`Reader` integration test is skip-marked separately.
"""

from __future__ import annotations

from receipt_risk.adapters.provenance.c2pa_reader import _derive_signals
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
