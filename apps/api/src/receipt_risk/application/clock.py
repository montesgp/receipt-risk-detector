"""Monotonic clock abstraction so `application/` never reads `time.monotonic`
directly — keeps duration measurement injectable/testable per design.md's
`AnalyzeReceiptUseCase.__init__(..., clock: Clock)`.
"""

from __future__ import annotations

import time
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def monotonic_ms(self) -> int: ...


class SystemClock:
    """Real wall-clock implementation of `Clock`."""

    def monotonic_ms(self) -> int:
        return int(time.monotonic() * 1000)
