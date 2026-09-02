"""Pure token-bucket algorithm — no framework import, unit-testable
without ASGI (design decision DD5, `openspec/changes/archive/
2026-09-01-mvp-init-foundation/design.md`).

Lazy refill on a monotonic clock; no background task. Each key (per-IP,
per-bucket) is tracked independently and evicted from an LRU-capped map so
IP rotation cannot turn the limiter itself into a memory-exhaustion vector.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field

DEFAULT_MAX_TRACKED_KEYS = 10_000


@dataclass
class TokenBucket:
    """One bucket for one key. `now` is injectable for deterministic tests."""

    capacity: float
    refill_per_second: float
    now: Callable[[], float] = time.monotonic
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = self.capacity
        self._last_refill = self.now()

    def _refill(self) -> None:
        current = self.now()
        elapsed = max(0.0, current - self._last_refill)
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_per_second)
        self._last_refill = current

    def try_acquire(self) -> bool:
        self._refill()
        if self._tokens < 1.0:
            return False
        self._tokens -= 1.0
        return True

    def retry_after_seconds(self) -> int:
        """Ceiling of the time until at least one token is available."""
        self._refill()
        if self._tokens >= 1.0:
            return 0
        deficit = 1.0 - self._tokens
        seconds = deficit / self.refill_per_second if self.refill_per_second > 0 else 1.0
        return max(1, int(seconds) + (1 if seconds % 1 else 0))

    def remaining(self) -> int:
        self._refill()
        return int(self._tokens)


class TokenBucketStore:
    """LRU-capped map of `key -> TokenBucket` for one rate-limit bucket
    (e.g. `default` or `analyze`). A single `asyncio.Lock` in the ASGI
    middleware guards concurrent access; this class itself is not
    thread-safe on its own (single event loop, one uvicorn worker)."""

    def __init__(
        self,
        *,
        capacity: float,
        refill_per_second: float,
        max_tracked_keys: int = DEFAULT_MAX_TRACKED_KEYS,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._max_tracked_keys = max_tracked_keys
        self._now = now
        self._buckets: OrderedDict[str, TokenBucket] = OrderedDict()

    def _bucket_for(self, key: str) -> TokenBucket:
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = TokenBucket(
                capacity=self._capacity, refill_per_second=self._refill_per_second, now=self._now
            )
            self._buckets[key] = bucket
            if len(self._buckets) > self._max_tracked_keys:
                self._buckets.popitem(last=False)  # evict least-recently-used
        else:
            self._buckets.move_to_end(key)
        return bucket

    def try_acquire(self, key: str) -> bool:
        return self._bucket_for(key).try_acquire()

    def retry_after_seconds(self, key: str) -> int:
        return self._bucket_for(key).retry_after_seconds()

    def remaining(self, key: str) -> int:
        return self._bucket_for(key).remaining()
