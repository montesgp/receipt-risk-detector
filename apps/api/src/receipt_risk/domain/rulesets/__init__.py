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

RULESETS: Final[dict[str, ScoringRuleset]] = {
    RULESET_2026_09_01.version: RULESET_2026_09_01,
}

__all__ = ["RULESETS"]
