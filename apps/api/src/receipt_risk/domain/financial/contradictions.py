"""Internal contradiction detection between extracted fields.

When OCR extracts multiple occurrences of the same logical field (e.g. an
amount printed both as a headline figure and an itemized total) and their
normalized values disagree, that disagreement is itself a suspicious
signal — never silently averaged, deduplicated, or discarded. Pure,
I/O-free per `docs/ARCHITECTURE.md` §5.
"""

from __future__ import annotations

from collections.abc import Sequence

from receipt_risk.domain.analysis import ExtractedField


def detect_contradictions(fields: Sequence[ExtractedField]) -> list[str]:
    """Return the field names for which two or more occurrences carry
    disagreeing normalized values. Fields with `normalized is None` (a
    failed extraction) are ignored — that is a `CORE_FIELD_EXTRACTION_FAILED`
    concern (slice 3b), not a contradiction."""
    normalized_by_name: dict[str, set[str]] = {}
    for extracted_field in fields:
        if extracted_field.normalized is None:
            continue
        normalized_by_name.setdefault(extracted_field.name, set()).add(extracted_field.normalized)

    return [name for name, values in normalized_by_name.items() if len(values) > 1]
