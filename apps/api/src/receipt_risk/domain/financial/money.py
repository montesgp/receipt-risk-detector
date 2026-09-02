"""ARS monetary amount normalization.

Accepts already-extracted OCR text for the `amount` field in either
AR-locale format (`.` groups thousands, `,` is the decimal separator) or
plain/US format (`,` groups thousands, `.` is the decimal separator), and
returns a comparable `Decimal`. Pure, I/O-free per `docs/ARCHITECTURE.md`
§5.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_NON_AMOUNT_CHARS: re.Pattern[str] = re.compile(r"[^\d.,-]")
_DECIMAL_COMMA_PATTERN: re.Pattern[str] = re.compile(r",\d{2}$")
_DECIMAL_DOT_PATTERN: re.Pattern[str] = re.compile(r"\.\d{2}$")


def normalize_amount(raw: str) -> Decimal | None:
    """Normalize a raw extracted amount string to a `Decimal`.

    Returns `None` when the text cannot be parsed as a monetary amount
    (never raises — a failed extraction is handled by the caller as a
    signal, not an exception, per design.md's "failed analyzer" pattern).
    """
    cleaned = _NON_AMOUNT_CHARS.sub("", raw.strip())
    if not cleaned:
        return None

    has_comma = "," in cleaned
    has_dot = "." in cleaned

    if has_comma and has_dot:
        if cleaned.rfind(",") > cleaned.rfind("."):
            # AR locale: '.' thousands, ',' decimal.
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # Plain/US: ',' thousands, '.' decimal.
            cleaned = cleaned.replace(",", "")
    elif has_comma:
        if _DECIMAL_COMMA_PATTERN.search(cleaned):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif has_dot:
        if not _DECIMAL_DOT_PATTERN.search(cleaned) and cleaned.count(".") >= 1:
            # Multiple/non-2dp dots are thousands separators, not a decimal.
            if cleaned.count(".") > 1 or len(cleaned.rsplit(".", 1)[-1]) == 3:
                cleaned = cleaned.replace(".", "")

    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
