#!/usr/bin/env python3
"""Deterministic synthetic Argentine transfer-receipt fixture generator.

This is fixture-authoring tooling (test/dev only), not production code — it
lives outside `src/receipt_risk/` and is exempt from the `TID251`
framework-import ban (`pyproject.toml`'s `per-file-ignores`).

Design invariant (design.md "Fixture Design"): every rendering parameter is
a literal constant. No RNG, no system font lookup, no timestamp — running
this script twice, on any machine, must produce byte-identical images and
an unchanged `manifest.json` (aside from the sha256 values it records,
which are themselves a function of the deterministic bytes).

All content is 100% fabricated per AGENTS.md's fixture policy: "Banco
Ejemplo" is not a real institution, and the CBU/CUIT/amount values are the
proposal's published known-answer literals, not real account data.

Usage:
    python samples/generate.py            # write images + manifest.json
    python samples/generate.py --check    # verify committed bytes match (no writes)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

SAMPLES_DIR = Path(__file__).resolve().parent
IMAGES_DIR = SAMPLES_DIR / "images"
FONT_PATH = SAMPLES_DIR / "fonts" / "DejaVuSans.ttf"
MANIFEST_PATH = SAMPLES_DIR / "manifest.json"

CANVAS_SIZE = (1080, 1920)
BACKGROUND = "white"
TEXT_COLOR = (20, 20, 20)
INSTITUTION_NAME = "Banco Ejemplo"

TITLE_FONT_SIZE = 48
LABEL_FONT_SIZE = 30
VALUE_FONT_SIZE = 34

LEFT_MARGIN = 80
TITLE_Y = 100
FIRST_ROW_Y = 280
ROW_HEIGHT = 130
LABEL_VALUE_GAP = 6

# Reference-set template constants (visual-anomaly-detection change):
# three additional deterministic templates so the vision adapter's
# reference-embedding set spans more than one visual "mode" (design.md
# "Reference set construction"). Every value below is a literal constant
# -- same no-RNG/no-system-font/no-timestamp invariant as the rest of this
# module.
INSTITUTION_NAME_2 = "Cooperativa Financiera del Sur"
HEADER_BAND_COLOR_2 = (18, 74, 133)
HEADER_BAND_HEIGHT_2 = 180

COMPACT_CANVAS_SIZE = (800, 1200)
COMPACT_TITLE_FONT_SIZE = 34
COMPACT_LABEL_FONT_SIZE = 20
COMPACT_VALUE_FONT_SIZE = 24
COMPACT_LEFT_MARGIN = 50
COMPACT_TITLE_Y = 60
COMPACT_FIRST_ROW_Y = 170
COMPACT_ROW_HEIGHT = 80

DARK_HEADER_COLOR = (24, 24, 28)
DARK_HEADER_TEXT_COLOR = (240, 240, 245)
DARK_HEADER_HEIGHT = 220
BOX_ROW_COLOR = (235, 238, 242)
BOX_ROW_PADDING = 14

# Declared field values shared by the "clean" and "invalid CBU" fixtures.
# Amounts/CBU/CUIT are the proposal's published known-answer literals —
# fabricated for testing, not a real transfer.
VALID_CBU = "2850590940090418135201"
MUTATED_CBU = "2850590940090418135202"  # block-2 check digit 1 -> 2
CUIT = "20-17254359-7"
AMOUNT = "125000.00"
DATE_TIME = "2026-09-01T14:43:00-03:00"
BENEFICIARY = "PATRICIO EJEMPLO"
OPERATION_ID = "483927183"

ROWS: tuple[tuple[str, str], ...] = (
    ("Monto", f"$ {AMOUNT}"),
    ("Fecha y hora", DATE_TIME),
    ("Destinatario", BENEFICIARY),
    ("CBU destino", "{cbu}"),  # filled in per-fixture
    ("CUIT", CUIT),
    ("N° de operación", OPERATION_ID),
)

# generic-receipt-field-extraction change: new fixture literals. Origin
# identifiers must be *computed* to satisfy the CBU (two mod-10 blocks) /
# CUIT (mod-11) check-digit algorithms, never hand-typed digits that merely
# look plausible -- asserted by
# tests/fixtures/test_origin_identifiers_checksum_valid.py. Destination
# identifiers on the two-party fixtures reuse VALID_CBU / CUIT above.
ORIGIN_CBU = "0720001400004444444448"
ORIGIN_CUIT = "27098765439"
ORIGIN_BENEFICIARY = "ORIGEN EJEMPLO"
ALT_AMOUNT = "8.000"
ALT_DATE_TEXT = "1 de ag0sto de 2026, 14:43 hs"
ALT_DATE_ISO = "2026-08-01T14:43:00"
DECOY_PHONE = "+54 11 2345-6789"

# alt_vocabulary_inline: disjoint label wording from ROWS above, inline
# "label: value" (no separate label/value rows), an AR-locale amount, and a
# digit-for-letter-typo'd month name in the date.
ROWS_ALT_VOCABULARY: tuple[tuple[str, str], ...] = (
    ("Importe transferido", f"$ {ALT_AMOUNT}"),
    ("Realizada el", ALT_DATE_TEXT),
    ("Para", BENEFICIARY),
    ("CVU", VALID_CBU),
    ("CUIT/CUIL", CUIT),
    ("Comprobante", OPERATION_ID),
)

# no_label_layout: values only, zero labels, plus decoys (a 9-digit
# operation id and a phone number) that must never be mistaken for a core
# field.
ROWS_NO_LABEL: tuple[str, ...] = (
    f"$ {AMOUNT}",
    DATE_TIME,
    BENEFICIARY,
    VALID_CBU,
    CUIT,
    "Comprobante",
    OPERATION_ID,
    DECOY_PHONE,
)

# two_party_labeled / two_party_no_labels: origin block then destination
# block, both CBU/CUIT pairs checksum-valid (so keyword-proximity, not
# checksum validity, is what the labeled test proves).
ROWS_TWO_PARTY: tuple[tuple[str, str], ...] = (
    ("Cuenta origen", ORIGIN_CBU),
    ("Titular", ORIGIN_BENEFICIARY),
    ("CUIT origen", ORIGIN_CUIT),
    ("Destino", VALID_CBU),
    ("Beneficiario", BENEFICIARY),
    ("CUIT destino", CUIT),
)
ROWS_TWO_PARTY_NO_LABELS: tuple[str, ...] = (
    ORIGIN_CBU,
    ORIGIN_BENEFICIARY,
    ORIGIN_CUIT,
    VALID_CBU,
    BENEFICIARY,
    CUIT,
)

# Degraded-variant post-processing parameters (design.md "Fixture Design").
SKEW_ANGLE_DEGREES = -3.2
CONTRAST_FACTOR = 0.55
BLUR_RADIUS = 1.4
JPEG_QUALITY = 45


def _render_receipt(cbu: str) -> Image.Image:
    image = Image.new("RGB", CANVAS_SIZE, color=BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.truetype(str(FONT_PATH), TITLE_FONT_SIZE)
    label_font = ImageFont.truetype(str(FONT_PATH), LABEL_FONT_SIZE)
    value_font = ImageFont.truetype(str(FONT_PATH), VALUE_FONT_SIZE)

    draw.text((LEFT_MARGIN, TITLE_Y), INSTITUTION_NAME, font=title_font, fill=TEXT_COLOR)
    draw.text(
        (LEFT_MARGIN, TITLE_Y + 70),
        "Comprobante de transferencia",
        font=label_font,
        fill=TEXT_COLOR,
    )

    for index, (label, value_template) in enumerate(ROWS):
        value = value_template.format(cbu=cbu)
        row_y = FIRST_ROW_Y + index * ROW_HEIGHT
        draw.text((LEFT_MARGIN, row_y), label, font=label_font, fill=TEXT_COLOR)
        draw.text(
            (LEFT_MARGIN, row_y + LABEL_FONT_SIZE + LABEL_VALUE_GAP),
            value,
            font=value_font,
            fill=TEXT_COLOR,
        )

    return image


def _render_receipt_bank2(cbu: str) -> Image.Image:
    """Second bank identity: different institution string, a coloured
    header band, right-aligned value column."""
    image = Image.new("RGB", CANVAS_SIZE, color=BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (CANVAS_SIZE[0], HEADER_BAND_HEIGHT_2)], fill=HEADER_BAND_COLOR_2)

    title_font = ImageFont.truetype(str(FONT_PATH), TITLE_FONT_SIZE)
    label_font = ImageFont.truetype(str(FONT_PATH), LABEL_FONT_SIZE)
    value_font = ImageFont.truetype(str(FONT_PATH), VALUE_FONT_SIZE)

    draw.text((LEFT_MARGIN, TITLE_Y - 30), INSTITUTION_NAME_2, font=title_font, fill=BACKGROUND)
    draw.text(
        (LEFT_MARGIN, TITLE_Y + 40),
        "Comprobante de transferencia",
        font=label_font,
        fill=BACKGROUND,
    )

    for index, (label, value_template) in enumerate(ROWS):
        value = value_template.format(cbu=cbu)
        row_y = FIRST_ROW_Y + index * ROW_HEIGHT
        draw.text((LEFT_MARGIN, row_y), label, font=label_font, fill=TEXT_COLOR)
        value_width = draw.textlength(value, font=value_font)
        draw.text(
            (CANVAS_SIZE[0] - LEFT_MARGIN - value_width, row_y + LABEL_FONT_SIZE + LABEL_VALUE_GAP),
            value,
            font=value_font,
            fill=TEXT_COLOR,
        )

    return image


def _render_receipt_compact(cbu: str) -> Image.Image:
    """Compact layout: smaller canvas, tighter rows, different font sizes."""
    image = Image.new("RGB", COMPACT_CANVAS_SIZE, color=BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.truetype(str(FONT_PATH), COMPACT_TITLE_FONT_SIZE)
    label_font = ImageFont.truetype(str(FONT_PATH), COMPACT_LABEL_FONT_SIZE)
    value_font = ImageFont.truetype(str(FONT_PATH), COMPACT_VALUE_FONT_SIZE)

    draw.text(
        (COMPACT_LEFT_MARGIN, COMPACT_TITLE_Y), INSTITUTION_NAME, font=title_font, fill=TEXT_COLOR
    )
    draw.text(
        (COMPACT_LEFT_MARGIN, COMPACT_TITLE_Y + 45),
        "Comprobante de transferencia",
        font=label_font,
        fill=TEXT_COLOR,
    )

    for index, (label, value_template) in enumerate(ROWS):
        value = value_template.format(cbu=cbu)
        row_y = COMPACT_FIRST_ROW_Y + index * COMPACT_ROW_HEIGHT
        draw.text((COMPACT_LEFT_MARGIN, row_y), label, font=label_font, fill=TEXT_COLOR)
        draw.text(
            (COMPACT_LEFT_MARGIN, row_y + COMPACT_LABEL_FONT_SIZE + LABEL_VALUE_GAP),
            value,
            font=value_font,
            fill=TEXT_COLOR,
        )

    return image


def _render_receipt_dark_header(cbu: str) -> Image.Image:
    """Dark-header, boxed-rows layout: a dark banner and shaded row
    backgrounds behind each label/value pair."""
    image = Image.new("RGB", CANVAS_SIZE, color=BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (CANVAS_SIZE[0], DARK_HEADER_HEIGHT)], fill=DARK_HEADER_COLOR)

    title_font = ImageFont.truetype(str(FONT_PATH), TITLE_FONT_SIZE)
    label_font = ImageFont.truetype(str(FONT_PATH), LABEL_FONT_SIZE)
    value_font = ImageFont.truetype(str(FONT_PATH), VALUE_FONT_SIZE)

    draw.text(
        (LEFT_MARGIN, TITLE_Y - 10), INSTITUTION_NAME, font=title_font, fill=DARK_HEADER_TEXT_COLOR
    )
    draw.text(
        (LEFT_MARGIN, TITLE_Y + 60),
        "Comprobante de transferencia",
        font=label_font,
        fill=DARK_HEADER_TEXT_COLOR,
    )

    for index, (label, value_template) in enumerate(ROWS):
        value = value_template.format(cbu=cbu)
        row_y = FIRST_ROW_Y + index * ROW_HEIGHT
        box_top = row_y - BOX_ROW_PADDING
        box_bottom = row_y + LABEL_FONT_SIZE + LABEL_VALUE_GAP + VALUE_FONT_SIZE + BOX_ROW_PADDING
        draw.rectangle(
            [(LEFT_MARGIN - BOX_ROW_PADDING, box_top), (CANVAS_SIZE[0] - LEFT_MARGIN, box_bottom)],
            fill=BOX_ROW_COLOR,
        )
        draw.text((LEFT_MARGIN, row_y), label, font=label_font, fill=TEXT_COLOR)
        draw.text(
            (LEFT_MARGIN, row_y + LABEL_FONT_SIZE + LABEL_VALUE_GAP),
            value,
            font=value_font,
            fill=TEXT_COLOR,
        )

    return image


def _render_labeled_rows(rows: tuple[tuple[str, str], ...]) -> Image.Image:
    """Same clean layout as `_render_receipt`, but takes an arbitrary
    label/value row tuple instead of always filling in `{cbu}` -- used by
    the generic-receipt-field-extraction fixtures below, which need
    disjoint label vocabulary or a two-party layout."""
    image = Image.new("RGB", CANVAS_SIZE, color=BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.truetype(str(FONT_PATH), TITLE_FONT_SIZE)
    label_font = ImageFont.truetype(str(FONT_PATH), LABEL_FONT_SIZE)
    value_font = ImageFont.truetype(str(FONT_PATH), VALUE_FONT_SIZE)

    draw.text((LEFT_MARGIN, TITLE_Y), INSTITUTION_NAME, font=title_font, fill=TEXT_COLOR)
    draw.text(
        (LEFT_MARGIN, TITLE_Y + 70),
        "Comprobante de transferencia",
        font=label_font,
        fill=TEXT_COLOR,
    )

    for index, (label, value) in enumerate(rows):
        row_y = FIRST_ROW_Y + index * ROW_HEIGHT
        draw.text((LEFT_MARGIN, row_y), label, font=label_font, fill=TEXT_COLOR)
        draw.text(
            (LEFT_MARGIN, row_y + LABEL_FONT_SIZE + LABEL_VALUE_GAP),
            value,
            font=value_font,
            fill=TEXT_COLOR,
        )

    return image


def _render_values_only(values: tuple[str, ...]) -> Image.Image:
    """Label-independent layout: no label text at all, just values in
    reading order -- proves detection never depends on a label."""
    image = Image.new("RGB", CANVAS_SIZE, color=BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = ImageFont.truetype(str(FONT_PATH), TITLE_FONT_SIZE)
    label_font = ImageFont.truetype(str(FONT_PATH), LABEL_FONT_SIZE)
    value_font = ImageFont.truetype(str(FONT_PATH), VALUE_FONT_SIZE)

    draw.text((LEFT_MARGIN, TITLE_Y), INSTITUTION_NAME, font=title_font, fill=TEXT_COLOR)
    draw.text(
        (LEFT_MARGIN, TITLE_Y + 70),
        "Comprobante de transferencia",
        font=label_font,
        fill=TEXT_COLOR,
    )

    for index, value in enumerate(values):
        row_y = FIRST_ROW_Y + index * ROW_HEIGHT
        draw.text(
            (LEFT_MARGIN, row_y + LABEL_FONT_SIZE + LABEL_VALUE_GAP),
            value,
            font=value_font,
            fill=TEXT_COLOR,
        )

    return image


def _degrade(image: Image.Image) -> Image.Image:
    """Apply the fixed, deterministic degradation pipeline used by
    `low_quality_skewed.jpg` (design.md "Fixture Design")."""
    rotated = image.rotate(SKEW_ANGLE_DEGREES, resample=Image.BICUBIC, expand=True)
    contrasted = ImageEnhance.Contrast(rotated).enhance(CONTRAST_FACTOR)
    blurred = contrasted.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    return blurred


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate() -> dict[str, str]:
    """Render every fixture image to `samples/images/` and return a mapping
    of fixture id -> sha256 of the written bytes."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    digests: dict[str, str] = {}

    clean = _render_receipt(VALID_CBU)
    clean_path = IMAGES_DIR / "clean_valid_transfer.png"
    clean.save(clean_path, format="PNG")
    digests["clean_valid_transfer"] = _sha256_of(clean_path)

    invalid_cbu = _render_receipt(MUTATED_CBU)
    invalid_cbu_path = IMAGES_DIR / "invalid_cbu_check_digit.png"
    invalid_cbu.save(invalid_cbu_path, format="PNG")
    digests["invalid_cbu_check_digit"] = _sha256_of(invalid_cbu_path)

    degraded = _degrade(clean)
    low_quality_path = IMAGES_DIR / "low_quality_skewed.jpg"
    degraded.convert("RGB").save(low_quality_path, format="JPEG", quality=JPEG_QUALITY)
    digests["low_quality_skewed"] = _sha256_of(low_quality_path)

    # corrupted_truncated.jpg: the first 2 KB of a valid JPEG, so it fails
    # decode (must never be produced by re-encoding, only by truncation, or
    # its bytes would still parse as a valid smaller image).
    valid_jpeg_bytes = _jpeg_bytes(clean)
    truncated_path = IMAGES_DIR / "corrupted_truncated.jpg"
    truncated_path.write_bytes(valid_jpeg_bytes[:2048])
    digests["corrupted_truncated"] = _sha256_of(truncated_path)

    # Reference-set templates (visual-anomaly-detection change): each new
    # template gets a clean render plus its one degraded variant, giving
    # the vision adapter's reference set coverage across template, layout,
    # and degradation axes (design.md "Reference set construction").
    reference_dir = IMAGES_DIR / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)

    templates: tuple[tuple[str, Image.Image], ...] = (
        ("bank2", _render_receipt_bank2(VALID_CBU)),
        ("compact", _render_receipt_compact(VALID_CBU)),
        ("dark_header", _render_receipt_dark_header(VALID_CBU)),
    )
    for slug, rendered in templates:
        clean_id = f"reference_{slug}_clean"
        clean_path = reference_dir / f"{clean_id}.png"
        rendered.save(clean_path, format="PNG")
        digests[clean_id] = _sha256_of(clean_path)

        degraded_id = f"reference_{slug}_degraded"
        degraded_path = reference_dir / f"{degraded_id}.jpg"
        _degrade(rendered).convert("RGB").save(degraded_path, format="JPEG", quality=JPEG_QUALITY)
        digests[degraded_id] = _sha256_of(degraded_path)

    # generic-receipt-field-extraction fixtures: OCR-only, land in
    # samples/images/ (root), not images/reference/, so the vision
    # reference-embedding builder does not pick them up.
    alt_vocabulary = _render_labeled_rows(ROWS_ALT_VOCABULARY)
    alt_vocabulary_path = IMAGES_DIR / "alt_vocabulary_inline.png"
    alt_vocabulary.save(alt_vocabulary_path, format="PNG")
    digests["alt_vocabulary_inline"] = _sha256_of(alt_vocabulary_path)

    no_label = _render_values_only(ROWS_NO_LABEL)
    no_label_path = IMAGES_DIR / "no_label_layout.png"
    no_label.save(no_label_path, format="PNG")
    digests["no_label_layout"] = _sha256_of(no_label_path)

    two_party_labeled = _render_labeled_rows(ROWS_TWO_PARTY)
    two_party_labeled_path = IMAGES_DIR / "two_party_labeled.png"
    two_party_labeled.save(two_party_labeled_path, format="PNG")
    digests["two_party_labeled"] = _sha256_of(two_party_labeled_path)

    two_party_no_labels = _render_values_only(ROWS_TWO_PARTY_NO_LABELS)
    two_party_no_labels_path = IMAGES_DIR / "two_party_no_labels.png"
    two_party_no_labels.save(two_party_no_labels_path, format="PNG")
    digests["two_party_no_labels"] = _sha256_of(two_party_no_labels_path)

    return digests


def _jpeg_bytes(image: Image.Image) -> bytes:
    import io

    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


_REFERENCE_TEMPLATE_SLUGS: tuple[str, ...] = ("bank2", "compact", "dark_header")


def _reference_fixture_entries(digests: dict[str, str]) -> list[dict[str, object]]:
    """Manifest entries for the vision reference-set images (visual-anomaly-
    detection change). These carry `vision`-only expectations: no financial
    signals are asserted since these fixtures exist for
    `build_reference_embeddings.py`, not for financial-validation tests."""
    entries: list[dict[str, object]] = []
    for slug in _REFERENCE_TEMPLATE_SLUGS:
        clean_id = f"reference_{slug}_clean"
        entries.append(
            {
                "id": clean_id,
                "path": f"images/reference/{clean_id}.png",
                "sha256": digests[clean_id],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "amount": AMOUNT,
                    "destination_cbu": VALID_CBU,
                    "cuit": CUIT,
                },
                "expected_signals": [],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "notes": f"Vision reference-set image: '{slug}' template, clean render.",
            }
        )
        degraded_id = f"reference_{slug}_degraded"
        entries.append(
            {
                "id": degraded_id,
                "path": f"images/reference/{degraded_id}.jpg",
                "sha256": digests[degraded_id],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "amount": AMOUNT,
                    "destination_cbu": VALID_CBU,
                    "cuit": CUIT,
                },
                "expected_signals": [],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "notes": f"Vision reference-set image: '{slug}' template, degraded variant.",
            }
        )
    return entries


def _build_manifest(digests: dict[str, str]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "generator": {
            "script": "samples/generate.py",
            "pillow": "11.0.0",
            "font": "samples/fonts/DejaVuSans.ttf",
        },
        "fixtures": [
            {
                "id": "clean_valid_transfer",
                "path": "images/clean_valid_transfer.png",
                "sha256": digests["clean_valid_transfer"],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "amount": AMOUNT,
                    "currency": "ARS",
                    "date_time": DATE_TIME,
                    "beneficiary_name": BENEFICIARY,
                    "destination_cbu": VALID_CBU,
                    "cuit": CUIT,
                    "operation_id": OPERATION_ID,
                },
                "expected_signals": [],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "expected_classification": "LOW_RISK",
                "notes": (
                    "Baseline: all core fields legible, valid check digits, no provenance claim."
                ),
            },
            {
                "id": "invalid_cbu_check_digit",
                "path": "images/invalid_cbu_check_digit.png",
                "sha256": digests["invalid_cbu_check_digit"],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "destination_cbu": MUTATED_CBU,
                    "amount": AMOUNT,
                },
                "expected_signals": [
                    {
                        "code": "INVALID_CBU_CHECK_DIGIT",
                        "category": "financial_consistency",
                        "severity": "high",
                    }
                ],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "expected_classification": "REVIEW_RECOMMENDED",
                "notes": (
                    "Identical render to the baseline with only the block-2 check digit"
                    " mutated 1 -> 2."
                ),
            },
            {
                "id": "low_quality_skewed",
                "path": "images/low_quality_skewed.jpg",
                "sha256": digests["low_quality_skewed"],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "amount": AMOUNT,
                    "destination_cbu": VALID_CBU,
                    "cuit": CUIT,
                },
                "expected_signals": [],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "expected_classification": "LOW_RISK",
                "notes": (
                    "Rotated, contrast-reduced, blurred, low-quality JPEG re-encode of the"
                    " baseline; exercises the OCR adapter's single preprocessing retry (slice 3)."
                ),
            },
            {
                "id": "corrupted_truncated",
                "path": "images/corrupted_truncated.jpg",
                "sha256": digests["corrupted_truncated"],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "n/a",
                },
                "declared_fields": {},
                "expected_signals": [],
                "expected_error": {"status": 415, "code": "UNSUPPORTED_IMAGE"},
                "notes": (
                    "First 2 KB of a valid JPEG; must be rejected at ingestion before any"
                    " analyzer runs."
                ),
            },
            {
                "id": "alt_vocabulary_inline",
                "path": "images/alt_vocabulary_inline.png",
                "sha256": digests["alt_vocabulary_inline"],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "amount": ALT_AMOUNT.replace(".", ""),
                    "date_time": ALT_DATE_ISO,
                    "beneficiary_name": BENEFICIARY,
                    "destination_cbu": VALID_CBU,
                    "cuit": CUIT,
                    "operation_id": OPERATION_ID,
                },
                "expected_signals": [],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "expected_classification": "LOW_RISK",
                "notes": (
                    "generic-receipt-field-extraction: disjoint label vocabulary, inline"
                    " 'label: value' lines, AR-locale amount, digit-for-letter-typo'd"
                    " month name -- proves extraction never depends on a fixed label set."
                ),
            },
            {
                "id": "no_label_layout",
                "path": "images/no_label_layout.png",
                "sha256": digests["no_label_layout"],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "amount": AMOUNT,
                    "date_time": DATE_TIME,
                    "beneficiary_name": BENEFICIARY,
                    "destination_cbu": VALID_CBU,
                    "cuit": CUIT,
                },
                "expected_signals": [],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "expected_classification": "LOW_RISK",
                "notes": (
                    "generic-receipt-field-extraction: values only, zero labels, plus a"
                    " decoy 9-digit operation id and a phone number that must never be"
                    " mistaken for a core field."
                ),
            },
            {
                "id": "two_party_labeled",
                "path": "images/two_party_labeled.png",
                "sha256": digests["two_party_labeled"],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "beneficiary_name": BENEFICIARY,
                    "destination_cbu": VALID_CBU,
                    "cuit": CUIT,
                    "origin_cbu": ORIGIN_CBU,
                    "origin_cuit": ORIGIN_CUIT,
                },
                "expected_signals": [],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "expected_classification": "LOW_RISK",
                "notes": (
                    "generic-receipt-field-extraction: origin block ('Cuenta origen' /"
                    " 'Titular') then destination block ('Destino' / 'Beneficiario'),"
                    " both CBU/CUIT pairs checksum-valid -- proves keyword-proximity"
                    " selection, not checksum validity, picks the destination pair."
                ),
            },
            {
                "id": "two_party_no_labels",
                "path": "images/two_party_no_labels.png",
                "sha256": digests["two_party_no_labels"],
                "provenance": {
                    "origin": "synthetic",
                    "authored_by": "samples/generate.py",
                    "contains_real_data": False,
                    "bank_template": "fabricated",
                },
                "declared_fields": {
                    "beneficiary_name": BENEFICIARY,
                    "destination_cbu": VALID_CBU,
                    "cuit": CUIT,
                    "origin_cbu": ORIGIN_CBU,
                    "origin_cuit": ORIGIN_CUIT,
                },
                "expected_signals": [],
                "expected_analyzer_statuses": {
                    "ocr": "completed",
                    "metadata": "completed",
                    "provenance": "completed",
                    "vision": "completed",
                },
                "expected_classification": "LOW_RISK",
                "notes": (
                    "generic-receipt-field-extraction: same two checksum-valid pairs as"
                    " two_party_labeled, with no keyword text anywhere -- proves the"
                    " positional fallback (second-appearing pair = destination)."
                ),
            },
            *_reference_fixture_entries(digests),
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify committed images/manifest match a fresh render; do not write anything.",
    )
    args = parser.parse_args(argv)

    if args.check:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            original_images_dir = globals()["IMAGES_DIR"]
            globals()["IMAGES_DIR"] = tmp_path
            try:
                digests = generate()
            finally:
                globals()["IMAGES_DIR"] = original_images_dir
            committed_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            committed_digests = {f["id"]: f["sha256"] for f in committed_manifest["fixtures"]}
            if digests != committed_digests:
                print("Fixture drift detected:", file=sys.stderr)
                for fixture_id, expected in committed_digests.items():
                    actual = digests.get(fixture_id)
                    if actual != expected:
                        print(f"  {fixture_id}: expected {expected}, got {actual}", file=sys.stderr)
                return 1
            print("All fixtures match committed bytes.")
            return 0

    digests = generate()
    manifest = _build_manifest(digests)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(digests)} fixture images and {MANIFEST_PATH.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
