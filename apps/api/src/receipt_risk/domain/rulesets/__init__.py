"""Registry of every versioned `ScoringRuleset`, keyed by `version` string.

Importing this module registers every ruleset module below. Keeping the
registry here (rather than in `domain/ruleset.py`) avoids a circular import:
each `v*.py` module imports `ScoringRuleset` from `domain.ruleset`, so
`domain.ruleset` itself must not import back from `domain.rulesets`.
"""

from __future__ import annotations

from typing import Final

from receipt_risk.domain.ruleset import ScoringRuleset
from receipt_risk.domain.rulesets.v2026_09_01 import RULESET_2026_09_01
from receipt_risk.domain.rulesets.v2026_09_04 import RULESET_2026_09_04
from receipt_risk.domain.rulesets.v2026_09_05 import RULESET_2026_09_05

RULESETS: Final[dict[str, ScoringRuleset]] = {
    RULESET_2026_09_01.version: RULESET_2026_09_01,
    RULESET_2026_09_04.version: RULESET_2026_09_04,
    RULESET_2026_09_05.version: RULESET_2026_09_05,
}

__all__ = ["RULESETS"]
