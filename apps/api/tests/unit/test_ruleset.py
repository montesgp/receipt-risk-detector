"""Tests for `domain/ruleset.py` and the versioned ruleset registry.

Traces to design.md's "Versioned ruleset as a frozen declarative data
module" decision: `ScoringRuleset` is a frozen dataclass keyed by version
string in a registry, never hardcoded weights in scoring logic.

`RULESET_2026_09_04` (vision analyzer role, current MVP1 default) is the
active ruleset under test for current behavior. `RULESET_2026_09_01` stays
registered and unmodified so any request logged with that version string
remains reproducible (CONTRIBUTING.md: scoring changes bump
`ruleset_version` rather than mutate a shipped one in place).
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

from receipt_risk.domain.ruleset import Classification, RecommendedAction, ScoringRuleset
from receipt_risk.domain.rulesets import RULESETS
from receipt_risk.domain.rulesets.v2026_09_01 import RULESET_2026_09_01
from receipt_risk.domain.rulesets.v2026_09_04 import RULESET_2026_09_04
from receipt_risk.domain.signals import Severity, SignalCode


def test_scoring_ruleset_is_frozen_dataclass_keyed_by_version() -> None:
    assert dataclasses.is_dataclass(ScoringRuleset)
    assert ScoringRuleset.__dataclass_params__.frozen is True
    assert RULESET_2026_09_04.version == "2026-09-04"
    assert RULESETS[RULESET_2026_09_04.version] is RULESET_2026_09_04


def test_prior_ruleset_version_stays_registered_and_unmodified() -> None:
    """`v2026_09_01` predates the vision analyzer: no weight/evidence entry
    for it, original 3-role evidence split. Never mutate this ruleset in
    place -- add a new version instead (this is exactly that precedent)."""
    assert RULESET_2026_09_01.version == "2026-09-01"
    assert RULESETS[RULESET_2026_09_01.version] is RULESET_2026_09_01
    assert SignalCode.VISUAL_ANOMALY_DETECTED not in RULESET_2026_09_01.weights
    assert set(RULESET_2026_09_01.analyzer_evidence_weights) == {"ocr", "metadata", "provenance"}
    assert sum(RULESET_2026_09_01.analyzer_evidence_weights.values()) == Decimal("1.00")


def test_ruleset_declares_weights_for_every_defined_signal_code() -> None:
    for code in SignalCode:
        assert code in RULESET_2026_09_04.weights, f"missing weight for {code}"


def test_ruleset_declares_severity_multiplier_for_every_severity() -> None:
    for severity in Severity:
        assert severity in RULESET_2026_09_04.severity_multiplier


def test_ruleset_analyzer_evidence_weights_sum_to_one() -> None:
    total = sum(RULESET_2026_09_04.analyzer_evidence_weights.values())
    assert total == Decimal("1.00")


def test_evidence_weights_sum_to_one_across_four_roles() -> None:
    weights = RULESET_2026_09_04.analyzer_evidence_weights
    assert set(weights) == {"ocr", "metadata", "provenance", "vision"}
    assert weights["ocr"] == Decimal("0.43")
    assert weights["metadata"] == Decimal("0.17")
    assert weights["provenance"] == Decimal("0.25")
    assert weights["vision"] == Decimal("0.15")
    assert sum(weights.values()) == Decimal("1.00")


def test_visual_anomaly_detected_weight_20_no_critical_floor_entry() -> None:
    assert RULESET_2026_09_04.weights[SignalCode.VISUAL_ANOMALY_DETECTED] == 20
    assert SignalCode.VISUAL_ANOMALY_DETECTED not in RULESET_2026_09_04.critical_floor


def test_ruleset_inconclusive_threshold_is_decimal() -> None:
    assert RULESET_2026_09_04.inconclusive_coverage_threshold == Decimal("0.35")


def test_ruleset_bands_are_ordered_ascending() -> None:
    thresholds = [threshold for threshold, _classification in RULESET_2026_09_04.bands]
    assert thresholds == sorted(thresholds)
    assert thresholds[-1] == 100


def test_ruleset_declares_combination_floors_field_empty_on_historical_versions() -> None:
    """`ScoringRuleset.combination_floors` is required (frozen dataclass, no
    default); v2026_09_01/v2026_09_04 declare it explicitly empty so their
    scores are unaffected by the new policy field."""
    assert RULESET_2026_09_01.combination_floors == {}
    assert RULESET_2026_09_04.combination_floors == {}


def test_ruleset_2026_09_05_registered_with_combination_floor() -> None:
    from receipt_risk.domain.rulesets.v2026_09_05 import RULESET_2026_09_05

    assert len(RULESETS) == 3
    assert RULESET_2026_09_05.version == "2026-09-05"
    assert RULESETS[RULESET_2026_09_05.version] is RULESET_2026_09_05
    expected_key = frozenset(
        {SignalCode.CORE_FIELD_EXTRACTION_FAILED, SignalCode.DATE_OUT_OF_BOUNDS}
    )
    assert RULESET_2026_09_05.combination_floors == {expected_key: 55}


def test_classification_and_recommended_action_enums_match_docs_api() -> None:
    assert {c.value for c in Classification} == {
        "LOW_RISK",
        "REVIEW_RECOMMENDED",
        "SUSPICIOUS",
        "HIGH_RISK",
        "INCONCLUSIVE",
    }
    assert {a.value for a in RecommendedAction} == {
        "STANDARD_MANUAL_RECONCILIATION",
        "PRIORITY_MANUAL_RECONCILIATION",
        "DO_NOT_RELY_ON_RECEIPT",
    }
