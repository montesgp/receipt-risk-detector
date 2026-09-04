"""Unit tests for `adapters/ocr/field_parsers.py`.

Traces to spec.md "Field extracted with confidence" (FR-005) and the
generic-receipt-field-extraction change: detection must never depend on a
fixed label vocabulary. No real OCR engine is invoked here --
`boxes_from_engine_output` accepts a RapidOCR-shaped raw result literal, or
tests build `RawTextBox` records directly for the scan/select primitives.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from receipt_risk.adapters.ocr.field_parsers import (
    CORE_FIELD_NAMES,
    RawTextBox,
    _context_window,
    _digit_candidates,
    _digit_runs,
    _disambiguate_destination,
    _fold,
    _grouped_runs,
    _has_date_shape,
    _keyword_score,
    _repair_month_tokens,
    _scan_amount_candidates,
    _scan_cbu_candidates,
    _scan_cuit_candidates,
    _scan_date_candidates,
    _select_amount,
    _select_date,
    _select_identifier,
    boxes_from_engine_output,
    extract_core_fields,
)
from receipt_risk.application.financial_validation import validate_financials
from receipt_risk.domain.financial.contradictions import detect_contradictions

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


def _box(text: str, *, top: float = 0.0, left: float = 0.0, confidence: str = "0.90") -> RawTextBox:
    return RawTextBox(text=text, confidence=Decimal(confidence), top=top, left=left)


# ---------------------------------------------------------------------------
# Existing end-to-end coverage (must survive the label-independent rewrite).
# ---------------------------------------------------------------------------


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


def test_box_with_no_recognizable_value_shape_yields_no_fields() -> None:
    lonely_label = [[[80, 280], [200, 280], [200, 310], [80, 310]], "Monto", 0.99]
    boxes = boxes_from_engine_output([lonely_label])
    assert extract_core_fields(boxes) == ()


# ---------------------------------------------------------------------------
# Phase 2: digit-run scanning primitives (CBU/CUIT).
# ---------------------------------------------------------------------------


def test_digit_runs_extracts_hyphenated_11_digit_run() -> None:
    runs = _digit_runs("CUIT/CUIL:20-34240499-6")
    assert runs == ["20-34240499-6"]


def test_digit_runs_ignores_letter_glued_digits() -> None:
    runs = _digit_runs("OP12345678901X")
    assert runs == []


def test_grouped_runs_concatenates_spaced_groups_to_exact_target() -> None:
    runs = _grouped_runs("2850 5909 4009 0418 1352 01", 22)
    assert runs == ["2850590940090418135201"]


def test_grouped_runs_abandons_on_overflow() -> None:
    runs = _grouped_runs("11 2345 6789 9999", 11)
    assert runs == []


def test_digit_candidates_tier1_hyphenated_and_tier2_grouped() -> None:
    boxes = [
        _box("CUIT/CUIL:20-34240499-6", top=0.0),
        _box("2850 5909 4009 0418 1352 01", top=50.0),
    ]
    cuit_candidates = _digit_candidates(boxes, 11)
    cbu_candidates = _digit_candidates(boxes, 22)
    assert [c.value for c in cuit_candidates] == ["20342404996"]
    assert [c.value for c in cbu_candidates] == ["2850590940090418135201"]


def test_digit_candidates_merged_33_digit_box_yields_nothing() -> None:
    merged = "285059094009041813520120342404996"  # 22 + 11 concatenated, no separators
    assert len(merged) == 33
    boxes = [_box(merged)]
    assert _digit_candidates(boxes, 11) == []
    assert _digit_candidates(boxes, 22) == []


def test_scan_cuit_candidates_inline_label_value() -> None:
    boxes = [_box("CUIT: 20-12345678-9")]
    candidates = _scan_cuit_candidates(boxes)
    assert len(candidates) == 1
    assert candidates[0].value == "20123456789"


def test_scan_cbu_candidates_inline_cvu_prefix() -> None:
    boxes = [_box("CVU:0000003100094065748023")]
    candidates = _scan_cbu_candidates(boxes)
    assert len(candidates) == 1
    assert candidates[0].value == "0000003100094065748023"


def test_scan_cuit_candidates_ignores_unrelated_operation_id() -> None:
    boxes = [
        _box("CUIT: 20-17254359-7", top=0.0),
        _box("N° de operación 483927183", top=50.0),
        _box("11 2345-6789", top=100.0),
    ]
    candidates = _scan_cuit_candidates(boxes)
    assert [c.value for c in candidates] == ["20172543597"]


def test_scan_cbu_candidates_dedupes_same_digit_string_printed_twice() -> None:
    boxes = [
        _box("CBU: 2850590940090418135201", top=0.0),
        _box("2850590940090418135201", top=50.0),
    ]
    identifier = _select_identifier(_scan_cbu_candidates(boxes), boxes)
    assert identifier is not None
    assert identifier.value == "2850590940090418135201"


# ---------------------------------------------------------------------------
# Phase 3: amount and date scanners.
# ---------------------------------------------------------------------------


def test_scan_amount_candidates_ar_locale_symbol_prefixed() -> None:
    boxes = [_box("$ 8.000")]
    candidates = _scan_amount_candidates(boxes)
    assert [c.value for c in candidates] == ["8000"]


def test_scan_amount_candidates_us_locale_symbol_prefixed() -> None:
    boxes = [_box("$1,234.56")]
    candidates = _scan_amount_candidates(boxes)
    assert [c.value for c in candidates] == ["1234.56"]


def test_select_amount_prefers_largest_within_winning_tier() -> None:
    boxes = [_box("Comision $ 50,00", top=0.0), _box("Transferido $ 8.000", top=50.0)]
    candidates = _scan_amount_candidates(boxes)
    winner = _select_amount(candidates)
    assert winner is not None
    assert winner.value == "8000"


def test_scan_amount_candidates_symbol_tier_beats_grouped_no_symbol_tier() -> None:
    boxes = [_box("saldo 12.345.678", top=0.0), _box("$ 8.000", top=50.0)]
    candidates = _scan_amount_candidates(boxes)
    assert [c.value for c in candidates] == ["8000"]


def test_repair_month_tokens_fixes_digit_for_letter_typo() -> None:
    repaired = _repair_month_tokens("1 de ag0sto de 2026, 14:43 hs")
    assert "agosto" in repaired
    assert "2026" in repaired


def test_repair_month_tokens_leaves_unrelated_typo_unrepaired() -> None:
    repaired = _repair_month_tokens("x0y not a month")
    assert "x0y" in repaired


def test_scan_date_candidates_wide_format_coverage_same_instant() -> None:
    texts = [
        "15/03/2026 14:30",
        "2026-03-15T14:30:00",
        "15 de marzo de 2026",
        "15 de mar20 de 2026",
    ]
    for text in texts:
        boxes = [_box(text)]
        candidates = _scan_date_candidates(boxes, excluded_orders=frozenset())
        assert len(candidates) == 1, f"expected exactly one date candidate for {text!r}"
        parsed = datetime.fromisoformat(candidates[0].value)
        assert (parsed.year, parsed.month, parsed.day) == (2026, 3, 15)


def test_scan_date_candidates_excludes_boxes_with_accepted_identifier_candidate() -> None:
    boxes = [_box("20-17254359-7")]
    candidates = _scan_date_candidates(boxes, excluded_orders=frozenset({0}))
    assert candidates == []


def test_scan_date_candidates_unparseable_text_yields_no_candidate() -> None:
    boxes = [_box("N° de operación 483927183")]
    candidates = _scan_date_candidates(boxes, excluded_orders=frozenset())
    assert candidates == []


def test_select_date_bounds_are_ranking_only_never_a_rejection_filter() -> None:
    reference = datetime(2026, 9, 1, tzinfo=UTC)
    implausible = _scan_date_candidates([_box("15 de marzo de 1920")], excluded_orders=frozenset())
    assert len(implausible) == 1
    selected = _select_date(implausible, reference=reference)
    assert selected is not None
    assert selected.value.startswith("1920-03-15")


# ---------------------------------------------------------------------------
# Phase 4: disambiguation and selection.
# ---------------------------------------------------------------------------


def test_fold_normalizes_accents_and_case() -> None:
    assert _fold("Acreditación") == "acreditacion"


def test_keyword_score_destination_origin_and_both() -> None:
    assert _keyword_score("cbu destino 123") == 1
    assert _keyword_score("cuenta origen 123") == -1
    assert _keyword_score("origen y destino") == 0
    assert _keyword_score("sin nada relevante") == 0


def test_context_window_includes_boxes_before_and_after_within_dy() -> None:
    boxes = [
        _box("Destino", top=100.0),
        _box("2850590940090418135201", top=140.0),
        _box("Banco Ejemplo", top=180.0),
        _box("Otra fila lejana", top=1000.0),
    ]
    candidate = _scan_cbu_candidates(boxes)[0]
    window = _context_window(boxes, candidate)
    assert "destino" in window
    assert "banco ejemplo" in window
    assert "otra fila lejana" not in window


def test_disambiguate_destination_single_candidate_wins_with_no_scoring() -> None:
    boxes = [_box("2850590940090418135201")]
    candidates = _scan_cbu_candidates(boxes)
    winner = _disambiguate_destination(candidates, boxes)
    assert winner is candidates[0]


def test_disambiguate_destination_by_keyword_proximity() -> None:
    origin_cbu = "1000000300000000000000"
    destination_cbu = "2850590940090418135201"
    boxes = [
        _box("Origen", top=0.0),
        _box(origin_cbu, top=40.0),
        _box("Destino", top=200.0),
        _box(destination_cbu, top=240.0),
    ]
    candidates = _scan_cbu_candidates(boxes)
    winner = _disambiguate_destination(candidates, boxes)
    assert winner is not None
    assert winner.value == destination_cbu


def test_disambiguate_destination_by_position_when_no_keyword_signal() -> None:
    first_cbu = "1000000300000000000000"
    second_cbu = "2850590940090418135201"
    boxes = [
        _box(first_cbu, top=0.0),
        _box(second_cbu, top=200.0),
    ]
    candidates = _scan_cbu_candidates(boxes)
    winner = _disambiguate_destination(candidates, boxes)
    assert winner is not None
    assert winner.value == second_cbu


def test_select_identifier_sole_checksum_failing_candidate_is_still_surfaced() -> None:
    mutated_cbu = "2850590940090418135202"  # block-2 check digit deliberately wrong
    boxes = [_box(mutated_cbu)]
    candidates = _scan_cbu_candidates(boxes)
    assert candidates[0].checksum_valid is False
    selected = _select_identifier(candidates, boxes)
    assert selected is not None
    assert selected.value == mutated_cbu


def test_select_identifier_disambiguates_within_checksum_valid_subset() -> None:
    valid_cuit = "20172543597"
    invalid_operation_id = "48392718301"  # 11 digits, fails CUIT checksum
    boxes = [
        _box(invalid_operation_id, top=0.0),
        _box(valid_cuit, top=50.0),
    ]
    candidates = _scan_cuit_candidates(boxes)
    selected = _select_identifier(candidates, boxes)
    assert selected is not None
    assert selected.value == valid_cuit


def test_extract_core_fields_emits_at_most_one_field_per_name_and_no_contradictions() -> None:
    origin_cbu = "1000000300000000000000"
    origin_cuit = "20111111112"
    destination_cbu = "2850590940090418135201"
    destination_cuit = "20172543597"
    raw_result = [
        [[[80, 100], [200, 100], [200, 130], [80, 130]], "Cuenta origen", 0.97],
        [[[80, 136], [520, 136], [520, 170], [80, 170]], origin_cbu, 0.95],
        [[[80, 176], [340, 176], [340, 210], [80, 210]], origin_cuit, 0.95],
        [[[80, 400], [200, 400], [200, 430], [80, 430]], "Destino beneficiario", 0.97],
        [[[80, 436], [520, 436], [520, 470], [80, 470]], destination_cbu, 0.95],
        [[[80, 476], [340, 476], [340, 510], [80, 510]], destination_cuit, 0.95],
    ]
    boxes = boxes_from_engine_output(raw_result)
    fields = extract_core_fields(boxes)

    names = [f.name for f in fields]
    assert len(names) == len(set(names))
    by_name = {f.name: f for f in fields}
    assert by_name["destination_cbu"].normalized == destination_cbu
    assert by_name["cuit"].normalized == destination_cuit
    assert detect_contradictions(fields) == []


def test_select_identifier_sole_checksum_failing_candidate_feeds_financial_validation() -> None:
    mutated_cbu = "2850590940090418135202"
    boxes = [_box(mutated_cbu)]
    candidates = _scan_cbu_candidates(boxes)
    selected = _select_identifier(candidates, boxes)
    assert selected is not None

    field = _make_extracted_field("destination_cbu", selected)
    signals = validate_financials((field,))
    codes = {s.code.value for s in signals}
    assert "INVALID_CBU_CHECK_DIGIT" in codes


def _make_extracted_field(name, candidate):
    from receipt_risk.domain.analysis import ExtractedField

    return ExtractedField(
        name=name,
        raw_text=candidate.raw_text,
        normalized=candidate.value,
        confidence=candidate.confidence,
    )


# ---------------------------------------------------------------------------
# Phase 7: fixture-shaped data (mirrors samples/generate.py's layout
# constants: FIRST_ROW_Y=280, ROW_HEIGHT=130, LABEL_VALUE_GAP-adjusted value
# row) without invoking the real OCR engine.
# ---------------------------------------------------------------------------

_FIRST_ROW_Y = 280.0
_ROW_HEIGHT = 130.0
_LABEL_VALUE_OFFSET = 36.0


def _labeled_rows_boxes(rows: list[tuple[str, str]]) -> list[RawTextBox]:
    boxes: list[RawTextBox] = []
    for index, (label, value) in enumerate(rows):
        row_y = _FIRST_ROW_Y + index * _ROW_HEIGHT
        boxes.append(_box(label, top=row_y, confidence="0.97"))
        boxes.append(_box(value, top=row_y + _LABEL_VALUE_OFFSET, confidence="0.95"))
    return boxes


def _values_only_boxes(values: list[str]) -> list[RawTextBox]:
    boxes: list[RawTextBox] = []
    for index, value in enumerate(values):
        row_y = _FIRST_ROW_Y + index * _ROW_HEIGHT
        boxes.append(_box(value, top=row_y + _LABEL_VALUE_OFFSET, confidence="0.95"))
    return boxes


def test_alt_vocabulary_inline_layout_extracts_all_four_core_fields() -> None:
    rows = [
        ("Importe transferido", "$ 8.000"),
        ("Realizada el", "1 de ag0sto de 2026, 14:43 hs"),
        ("Para", "PATRICIO EJEMPLO"),
        ("CVU", "2850590940090418135201"),
        ("CUIT/CUIL", "20-17254359-7"),
        ("Comprobante", "483927183"),
    ]
    boxes = _labeled_rows_boxes(rows)
    fields = extract_core_fields(boxes)
    by_name = {field.name: field for field in fields}

    assert set(by_name) == set(CORE_FIELD_NAMES)
    assert by_name["amount"].normalized == "8000"
    assert by_name["destination_cbu"].normalized == "2850590940090418135201"
    assert by_name["cuit"].normalized == "20172543597"
    parsed = datetime.fromisoformat(by_name["date_time"].normalized)
    assert (parsed.year, parsed.month, parsed.day) == (2026, 8, 1)


def test_no_label_layout_extracts_all_fields_and_ignores_decoys() -> None:
    values = [
        "$ 125.000,00",
        "2026-09-01T14:43:00-03:00",
        "PATRICIO EJEMPLO",
        "2850590940090418135201",
        "20-17254359-7",
        "Comprobante",
        "483927183",  # decoy: 9-digit operation id
        "+54 11 2345-6789",  # decoy: phone number
    ]
    boxes = _values_only_boxes(values)
    fields = extract_core_fields(boxes)
    by_name = {field.name: field for field in fields}

    assert set(by_name) == set(CORE_FIELD_NAMES)
    assert by_name["destination_cbu"].normalized == "2850590940090418135201"
    assert by_name["cuit"].normalized == "20172543597"


def test_two_party_labeled_and_no_labels_both_select_the_destination_pair() -> None:
    origin_cbu = "0720001400004444444448"
    origin_cuit = "27098765439"
    destination_cbu = "2850590940090418135201"
    destination_cuit = "20172543597"

    labeled_rows = [
        ("Cuenta origen", origin_cbu),
        ("Titular", "ORIGEN EJEMPLO"),
        ("CUIT origen", origin_cuit),
        ("Destino", destination_cbu),
        ("Beneficiario", "PATRICIO EJEMPLO"),
        ("CUIT destino", destination_cuit),
    ]
    labeled_fields = extract_core_fields(_labeled_rows_boxes(labeled_rows))
    labeled_by_name = {field.name: field for field in labeled_fields}
    assert labeled_by_name["destination_cbu"].normalized == destination_cbu
    assert labeled_by_name["cuit"].normalized == destination_cuit

    no_label_values = [
        origin_cbu,
        "ORIGEN EJEMPLO",
        origin_cuit,
        destination_cbu,
        "PATRICIO EJEMPLO",
        destination_cuit,
    ]
    no_label_fields = extract_core_fields(_values_only_boxes(no_label_values))
    no_label_by_name = {field.name: field for field in no_label_fields}
    assert no_label_by_name["destination_cbu"].normalized == destination_cbu
    assert no_label_by_name["cuit"].normalized == destination_cuit


# ---------------------------------------------------------------------------
# Batch 2 (verify CRITICAL fix): real Mercado Pago OCR text glues "2026"
# directly to "alas" (OCR dropped the space of "a las"), so the year has no
# word-boundary transition immediately after it -- both are \w characters.
# See openspec/changes/generic-receipt-field-extraction/verify-report.md
# Critical Finding 1.
# ---------------------------------------------------------------------------


def test_has_date_shape_accepts_year_glued_to_trailing_connector_text() -> None:
    text = "30/ag0sto/2026alas20:53."
    repaired = _repair_month_tokens(text)
    assert _has_date_shape(text, repaired=repaired) is True


def test_scan_date_candidates_parses_year_glued_to_connector_text() -> None:
    boxes = [_box("30/ag0sto/2026alas20:53.")]
    candidates = _scan_date_candidates(boxes, excluded_orders=frozenset())
    assert len(candidates) == 1
    parsed = datetime.fromisoformat(candidates[0].value)
    assert (parsed.year, parsed.month, parsed.day, parsed.hour, parsed.minute) == (
        2026,
        8,
        30,
        20,
        53,
    )


def test_extract_core_fields_real_mercado_pago_ocr_text_extracts_all_four_fields() -> None:
    """Literal RawTextBox inputs from the production receipt that motivated
    this change (verify-report.md's Independent Verification #10)."""
    raw_result = [
        [[[80, 280], [200, 280], [200, 310], [80, 310]], "$ 8.000", 0.95],
        [[[80, 410], [420, 410], [420, 440], [80, 440]], "CUIT/CUIL:20-34240499-6", 0.96],
        [[[80, 540], [520, 540], [520, 570], [80, 570]], "CVU:0000003100094065748023", 0.91],
        [[[80, 670], [420, 670], [420, 700], [80, 700]], "30/ag0sto/2026alas20:53.", 0.93],
    ]
    boxes = boxes_from_engine_output(raw_result)
    fields = extract_core_fields(boxes)
    by_name = {field.name: field for field in fields}

    assert set(by_name) == set(CORE_FIELD_NAMES)
    for name in CORE_FIELD_NAMES:
        assert by_name[name].normalized is not None

    assert by_name["amount"].normalized == "8000"
    assert by_name["destination_cbu"].normalized == "0000003100094065748023"
    assert by_name["cuit"].normalized == "20342404996"
    parsed = datetime.fromisoformat(by_name["date_time"].normalized)
    assert (parsed.year, parsed.month, parsed.day, parsed.hour, parsed.minute) == (
        2026,
        8,
        30,
        20,
        53,
    )
