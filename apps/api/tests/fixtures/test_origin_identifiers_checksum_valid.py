"""Guards `samples/generate.py`'s `ORIGIN_CBU`/`ORIGIN_CUIT` literals.

Traces to design.md's fixture plan risk callout: these values must be
*computed* to satisfy the CBU/CUIT check-digit algorithms, never
hand-typed digits that merely look plausible. Loads `generate.py` directly
by file path (it lives outside `src/receipt_risk/`, see its own module
docstring) rather than importing it as a package.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from receipt_risk.domain.financial.cbu import validate_cbu
from receipt_risk.domain.financial.cuit import validate_cuit

SAMPLES_DIR = Path(__file__).resolve().parents[4] / "samples"


def _load_generate_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("samples_generate", SAMPLES_DIR / "generate.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_origin_cbu_and_cuit_are_checksum_valid_by_construction() -> None:
    generate = _load_generate_module()

    cbu_result = validate_cbu(generate.ORIGIN_CBU)
    cuit_result = validate_cuit(generate.ORIGIN_CUIT)

    assert cbu_result.is_valid, cbu_result
    assert cuit_result.is_valid, cuit_result
