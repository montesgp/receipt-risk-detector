"""Engine-output -> `ExtractedField` parsing for the OCR adapter (slice 3b).

Adapter-only per `docs/ARCHITECTURE.md` §5: this module knows the shape of
a RapidOCR-style detection row (`[box_points, text, score]`) and the fixed
label vocabulary rendered by `samples/generate.py`, but never imports the
OCR engine itself — that stays in `adapters/ocr/paddle_onnx.py`.

Traces to spec.md "Field extracted with confidence" (FR-005): a field is
returned with its raw text, a normalized value (or `None` when it cannot be
normalized), and the engine's confidence for the value box.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from receipt_risk.domain.analysis import ExtractedField
from receipt_risk.domain.financial.money import normalize_amount

# The four core fields the coverage formula in design.md is computed over:
# "coverage = core fields with conf >= 0.60, / 4".
CORE_FIELD_NAMES: tuple[str, ...] = ("amount", "destination_cbu", "cuit", "date_time")

# Labels rendered by samples/generate.py's ROWS tuple, lower-cased.
_LABEL_TO_FIELD: dict[str, str] = {
    "monto": "amount",
    "fecha y hora": "date_time",
    "cbu destino": "destination_cbu",
    "cuit": "cuit",
}

# A label's value is expected immediately below it; anything farther than
# this is not the same label/value row (fixed constant, no tuning knob).
_MAX_LABEL_VALUE_GAP_PX = 80.0


@dataclass(frozen=True, slots=True)
class RawTextBox:
    """An engine-agnostic detected text box: text, confidence, and the
    top-left corner of its bounding box (used only for label/value
    proximity pairing, never persisted)."""

    text: str
    confidence: Decimal
    top: float
    left: float


def boxes_from_engine_output(raw_result: Sequence[object] | None) -> list[RawTextBox]:
    """Convert a RapidOCR-shaped result (`[[points, text, score], ...]`)
    into `RawTextBox` records. Never raises: a malformed row is dropped,
    never propagated as an exception (the adapter's bounded-retry state
    machine must stay purely a function of coverage, not of parser
    exceptions)."""
    boxes: list[RawTextBox] = []
    for row in raw_result or []:
        try:
            points, text, score = row  # type: ignore[misc]
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            boxes.append(
                RawTextBox(
                    text=str(text).strip(),
                    confidence=Decimal(str(score)).quantize(Decimal("0.01")),
                    top=min(ys),
                    left=min(xs),
                )
            )
        except (TypeError, ValueError, IndexError):
            continue
    return boxes


def _normalize_digits_of_length(text: str, length: int) -> str | None:
    digits = "".join(char for char in text if char.isdigit())
    return digits if len(digits) == length else None


def _normalize_date(text: str) -> str | None:
    stripped = text.strip()
    try:
        datetime.fromisoformat(stripped)
    except ValueError:
        return None
    return stripped


def _nearest_value_below(ordered: Sequence[RawTextBox], label_index: int) -> RawTextBox | None:
    label = ordered[label_index]
    for candidate in ordered[label_index + 1 :]:
        gap = candidate.top - label.top
        if gap <= 0:
            continue
        return candidate if gap <= _MAX_LABEL_VALUE_GAP_PX else None
    return None


def extract_core_fields(boxes: Sequence[RawTextBox]) -> tuple[ExtractedField, ...]:
    """Pair each recognized label box with its nearest value box below and
    normalize per field type. A field whose label is absent, or whose
    value fails normalization, is simply omitted — its absence is what the
    coverage formula in design.md counts against, not an exception."""
    ordered = sorted(boxes, key=lambda box: (box.top, box.left))
    fields: list[ExtractedField] = []

    for index, box in enumerate(ordered):
        field_name = _LABEL_TO_FIELD.get(box.text.strip().lower())
        if field_name is None:
            continue
        value_box = _nearest_value_below(ordered, index)
        if value_box is None:
            continue

        if field_name == "amount":
            amount = normalize_amount(value_box.text)
            normalized = str(amount) if amount is not None else None
        elif field_name in ("destination_cbu", "cuit"):
            length = 22 if field_name == "destination_cbu" else 11
            normalized = _normalize_digits_of_length(value_box.text, length)
        else:  # date_time
            normalized = _normalize_date(value_box.text)

        fields.append(
            ExtractedField(
                name=field_name,
                raw_text=value_box.text,
                normalized=normalized,
                confidence=value_box.confidence,
            )
        )

    return tuple(fields)
