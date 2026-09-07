"""Real-engine OCR integration test.

Runs `PaddleOnnxOcrAdapter` against the actual `rapidocr_onnxruntime` engine
and the actual committed fixture bytes -- no fake/mocked engine, unlike
every test in `tests/unit/test_ocr_paddle_onnx.py`. Requires
`RECEIPT_RISK_OCR_MODEL_DIR` to point at a real baked model set (CI fetches
this via `scripts/fetch_ocr_models.py`; skipped locally when unset).

Honesty note: `low_quality_skewed.jpg`'s degradation (rotation + JPEG-45 +
blur, per `samples/generate.py`) does NOT push the real engine below the
0.75 coverage threshold on attempt 1 -- verified by instrumenting the
engine call count, which stays at 1. This test therefore does NOT prove the
bounded-retry branch fires; that branch is proven by
`tests/unit/test_ocr_paddle_onnx.py::test_exactly_one_preprocessing_retry_when_below_threshold`
against a fake engine forced to return low-confidence results on attempt 1.
This test proves something different and still valuable: the real engine,
against real (if degraded) fixture bytes, extracts every field the manifest
expects, at the confidence/coverage the adapter's threshold requires.
"""

from __future__ import annotations

import os

import pytest

from conftest import fixture
from receipt_risk.adapters.ocr.paddle_onnx import PaddleOnnxOcrAdapter
from receipt_risk.application.models import SafeImageRef

pytestmark = pytest.mark.skipif(
    not os.environ.get("RECEIPT_RISK_OCR_MODEL_DIR"),
    reason="RECEIPT_RISK_OCR_MODEL_DIR not set -- CI fetches baked models, this sandbox does not",
)


def _ref_for(fixture) -> SafeImageRef:
    from PIL import Image

    with Image.open(fixture.path) as img:
        width, height = img.size
    return SafeImageRef(
        path=fixture.path,
        sha256=fixture.sha256,
        media_type="image/jpeg" if fixture.path.suffix == ".jpg" else "image/png",
        width=width,
        height=height,
        byte_size=fixture.path.stat().st_size,
    )


def test_real_engine_extracts_all_core_fields_from_clean_fixture() -> None:
    import anyio

    clean = fixture("clean_valid_transfer")
    adapter = PaddleOnnxOcrAdapter()

    result = anyio.run(adapter.extract, _ref_for(clean))

    assert result.status == "completed"
    extracted = {f.name: f.normalized for f in result.extracted_fields}
    assert extracted["destination_cbu"] == "2850590940090418135201"
    assert extracted["cuit"] == "20172543597"
    assert extracted["amount"] == "125000.00"


def test_real_engine_extracts_all_core_fields_from_alt_vocabulary_fixture() -> None:
    """generic-receipt-field-extraction: disjoint label vocabulary, inline
    `label: value` lines, AR-locale amount, digit-for-letter-typo'd month
    name -- proves label-independent extraction against the real engine,
    not just hand-written `RawTextBox` fixtures."""
    import anyio

    alt_vocabulary = fixture("alt_vocabulary_inline")
    adapter = PaddleOnnxOcrAdapter()

    result = anyio.run(adapter.extract, _ref_for(alt_vocabulary))

    assert result.status == "completed"
    extracted = {f.name: f.normalized for f in result.extracted_fields}
    assert extracted["destination_cbu"] == "2850590940090418135201"
    assert extracted["cuit"] == "20172543597"
    assert extracted["amount"] == "8000"


def test_real_engine_selects_destination_pair_on_two_party_labeled_fixture() -> None:
    import anyio

    two_party = fixture("two_party_labeled")
    adapter = PaddleOnnxOcrAdapter()

    result = anyio.run(adapter.extract, _ref_for(two_party))

    assert result.status == "completed"
    extracted = {f.name: f.normalized for f in result.extracted_fields}
    assert extracted["destination_cbu"] == "2850590940090418135201"
    assert extracted["cuit"] == "20172543597"


def test_real_engine_completes_on_low_quality_skewed_fixture_without_retry() -> None:
    """Documents actual behavior (see module docstring): this fixture's
    degradation does not trigger the retry branch with the real engine --
    attempt 1 alone reaches the coverage threshold."""
    import anyio

    from receipt_risk.adapters.ocr.paddle_onnx import _load_rapidocr_engine, _model_dir_from_env

    skewed = fixture("low_quality_skewed")
    real_engine = _load_rapidocr_engine(_model_dir_from_env())
    call_count = 0

    def counting_engine(pixels):
        nonlocal call_count
        call_count += 1
        return real_engine(pixels)

    adapter = PaddleOnnxOcrAdapter(engine=counting_engine)

    result = anyio.run(adapter.extract, _ref_for(skewed))

    assert result.status == "completed"
    assert call_count == 1, (
        "engine was called more than once -- if this now fails, the fixture's "
        "degradation has become strong enough to trigger the retry branch; "
        "update this test's assertion and the module docstring's honesty note"
    )
