"""Unit tests for `adapters/ocr/field_parsers.py`.

Traces to spec.md "Field extracted with confidence" (FR-005): the amount
field must come back with raw text, a normalized value, and a confidence
score. No real OCR engine is invoked here — `boxes_from_engine_output`
accepts a RapidOCR-shaped raw result literal.
"""

from __future__ import annotations

from decimal import Decimal

from receipt_risk.adapters.ocr.field_parsers import (
    CORE_FIELD_NAMES,
    boxes_from_engine_output,
    extract_core_fields,
)

# RapidOCR-shaped rows: [box_points, text, score]. Coordinates loosely mirror
# samples/generate.py's "Monto" label directly above its value row.
_RAW_RESULT = [
    [[[80, 280], [200, 280], [200, 310], [80, 310]], "Monto", 0.99],
    [[[80, 316], [320, 316], [320, 350], [80, 350]], "$ 125.000,00", 0.95],
    [[[80, 410], [260, 410], [260, 440], [80, 440]], "Fecha y hora", 0.98],
    [[[80, 446], [420, 446], [420, 480], [80, 480]], "2026-09-01T14:43:00-03:00", 0.93],
    [[[80, 670], [260, 670], [260, 700], [80, 700]], "CBU destino", 0.97],
    [[[80, 706], [520, 706], [520, 740], [80, 740]], "2850590940090418135201", 0.91],
    [[[80, 800], [200, 800], [200, 830], [80, 830]], "CUIT", 0.96],
    [[[80, 836], [340, 836], [340, 870], [80, 870]], "20-17254359-7", 0.90],
]


def test_amount_extracted_with_raw_normalized_and_confidence() -> None:
    boxes = boxes_from_engine_output(_RAW_RESULT)
    fields = extract_core_fields(boxes)
    by_name = {field.name: field for field in fields}

    amount = by_name["amount"]
    assert amount.raw_text == "$ 125.000,00"
    assert amount.normalized == "125000.00"
    assert amount.confidence == Decimal("0.95")


def test_all_core_fields_extracted_from_a_clean_layout() -> None:
    boxes = boxes_from_engine_output(_RAW_RESULT)
    fields = extract_core_fields(boxes)
    by_name = {field.name: field for field in fields}

    assert set(by_name) == set(CORE_FIELD_NAMES)
    assert by_name["destination_cbu"].normalized == "2850590940090418135201"
    assert by_name["cuit"].normalized == "20172543597"
    assert by_name["date_time"].normalized == "2026-09-01T14:43:00-03:00"


def test_malformed_engine_rows_are_dropped_not_raised() -> None:
    boxes = boxes_from_engine_output([["not", "a", "valid", "row"], None])
    assert boxes == []


def test_label_without_a_nearby_value_is_omitted() -> None:
    lonely_label = [[[80, 280], [200, 280], [200, 310], [80, 310]], "Monto", 0.99]
    boxes = boxes_from_engine_output([lonely_label])
    assert extract_core_fields(boxes) == ()
