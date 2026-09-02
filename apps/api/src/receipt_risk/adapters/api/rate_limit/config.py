"""Env-configurable rate-limit thresholds (api-rate-limiting spec's
"Env-configurable limits" requirement, D2)."""

from __future__ import annotations

import os

DEFAULT_DEFAULT_PER_MINUTE = 30
DEFAULT_ANALYZE_PER_MINUTE = 10
DEFAULT_MAX_TRACKED_KEYS = 10_000


def default_limit_per_minute() -> int:
    return int(os.environ.get("RATE_LIMIT_DEFAULT_PER_MINUTE", DEFAULT_DEFAULT_PER_MINUTE))


def analyze_limit_per_minute() -> int:
    return int(os.environ.get("RATE_LIMIT_ANALYZE_PER_MINUTE", DEFAULT_ANALYZE_PER_MINUTE))


def max_tracked_keys() -> int:
    return int(os.environ.get("RATE_LIMIT_MAX_TRACKED_KEYS", DEFAULT_MAX_TRACKED_KEYS))


def trust_forwarded_for() -> bool:
    return os.environ.get("RATE_LIMIT_TRUST_FORWARDED_FOR", "false").lower() == "true"
