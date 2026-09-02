"""FastAPI dependency providers. `bootstrap/app.py` overrides
`get_use_case` with a real `AnalyzeReceiptUseCase` wired to concrete
adapters; tests override it with stub/mock ports (see `tests/unit/
test_router.py`).
"""

from __future__ import annotations

from receipt_risk.application.analyze_receipt import AnalyzeReceiptUseCase


def get_use_case() -> AnalyzeReceiptUseCase:
    """Placeholder dependency: `bootstrap/app.py` MUST override this with a
    real `AnalyzeReceiptUseCase` before serving traffic."""
    raise RuntimeError(
        "AnalyzeReceiptUseCase dependency is not wired -- "
        "bootstrap/app.py must override get_use_case()."
    )
