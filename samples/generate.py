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

    return digests


def _jpeg_bytes(image: Image.Image) -> bytes:
    import io

    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


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
