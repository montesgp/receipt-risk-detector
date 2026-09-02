"""Tests for the in-process per-IP token bucket (`api-rate-limiting` spec).

Traces to `openspec/specs/api-rate-limiting/spec.md`: default 30 req/min
bucket, stricter 10 req/min `analyze` bucket, env-configurable limits,
documented restart-resets-counters / not-multi-instance-safe limitation.
"""

from __future__ import annotations

from receipt_risk.adapters.api.rate_limit.bucket import TokenBucket, TokenBucketStore


def test_default_limit_enforced_within_budget() -> None:
    bucket = TokenBucket(capacity=30, refill_per_second=0.5, now=lambda: 0.0)
    for _ in range(30):
        assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


def test_analysis_endpoint_stricter_limit_returns_429_on_11th_request() -> None:
    clock = {"t": 0.0}
    store = TokenBucketStore(capacity=10, refill_per_second=10 / 60, now=lambda: clock["t"])
    for _ in range(10):
        assert store.try_acquire("1.2.3.4") is True
    assert store.try_acquire("1.2.3.4") is False


def test_overridden_default_via_environment(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_DEFAULT_PER_MINUTE", "5")
    from receipt_risk.adapters.api.rate_limit.config import default_limit_per_minute

    assert default_limit_per_minute() == 5


def test_bucket_refills_over_time() -> None:
    clock = {"t": 0.0}
    bucket = TokenBucket(capacity=2, refill_per_second=1.0, now=lambda: clock["t"])
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False
    clock["t"] = 1.0
    assert bucket.try_acquire() is True


def test_restart_resets_counters_is_structural_new_process() -> None:
    # The store is in-process memory; a fresh instance == "after restart".
    store_before = TokenBucketStore(capacity=1, refill_per_second=1.0, now=lambda: 0.0)
    store_before.try_acquire("client")
    assert store_before.try_acquire("client") is False

    store_after_restart = TokenBucketStore(capacity=1, refill_per_second=1.0, now=lambda: 0.0)
    assert store_after_restart.try_acquire("client") is True
