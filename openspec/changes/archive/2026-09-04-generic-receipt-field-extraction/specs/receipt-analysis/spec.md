# Delta for Receipt Analysis

## MODIFIED Requirements

### Requirement: Local OCR extraction
The system SHALL run OCR locally, without paid per-request model tokens, extracting amount, date, names, CBU/CVU, CUIT/CUIL, institution, and operation ID when visible (FR-005).

The system MUST detect and normalize the four core financial fields — `amount`, `destination_cbu`, `cuit`, `date_time` — by validating candidate values against each field's domain-specific shape/checksum, independent of the issuing bank or wallet's label wording, whether a label is present at all, or the label's layout relative to the value (above, inline, or absent). Detection MUST NOT depend on matching a fixed label vocabulary:
- `amount`: any currency-pattern substring (AR `.`/`,` and US `,`/`.` separator conventions), normalized via `normalize_amount`.
- `destination_cbu` / `cuit`: any boundary-anchored 22-digit / 11-digit digit run, shape-checked via `validate_cbu` / `validate_cuit`.
- `date_time`: any recognizable date/time text — numeric with common separators, day-month-name in Spanish or English, ISO 8601, 12h/24h clock, with or without seconds/timezone, tolerant of single-character OCR digit-for-letter typos in month names — normalized to an ISO 8601 string, backstopped by the existing plausibility-bounds check.

When a receipt contains two structurally valid CUIT/CBU candidates (an origin and a destination), the system MUST collapse them to exactly one `ExtractedField` per field name, chosen by: (1) proximity to a destination/beneficiary-style keyword when any candidate has one nearby; else (2) positional order, treating the first-appearing candidate as origin and the second as destination. The system MUST NOT emit two `ExtractedField` entries sharing the same name for the same field slot.

When a field slot has exactly one structurally valid candidate, the system MUST surface it (populate `normalized`) regardless of whether its checksum passes. Checksum validity MUST gate selection only when disambiguating among multiple candidates for the same slot, never a lone candidate — checksum-failure signaling stays the Financial validation requirement's job.

#### Scenario: Field extracted with confidence
- GIVEN a receipt image with a visible amount field
- WHEN OCR completes
- THEN the amount is returned with raw text, normalized value, and extraction confidence

#### Scenario: Same field extracted despite different label wording
- GIVEN two receipts encoding the same destination CBU value, one labeled "CBU Destino", the other labeled "CVU", and a third with no label at all
- WHEN core-field extraction runs on each
- THEN all three produce an equivalent `destination_cbu` field with the same `normalized` value

#### Scenario: Inline label:value on a single line
- GIVEN an OCR text box containing `"CUIT: 20-12345678-9"` on one line rather than a label box paired with a value box below it
- WHEN core-field extraction runs
- THEN the `cuit` field is extracted with `normalized` populated

#### Scenario: Two CUIT/CBU pairs disambiguated by keyword proximity
- GIVEN a receipt with two valid CBU candidates, one near the text "origen"/"remitente" and the other near "destino"/"beneficiario"
- WHEN core-field extraction runs
- THEN exactly one `destination_cbu` field is returned, matching the candidate near the destination-style keyword

#### Scenario: Two CUIT/CBU pairs disambiguated by position when no keyword exists
- GIVEN a receipt with two valid CBU candidates and no destination/origin keyword near either
- WHEN core-field extraction runs
- THEN exactly one `destination_cbu` field is returned, matching the second-appearing (lower-on-page) candidate

#### Scenario: Sole checksum-failing candidate is still surfaced
- GIVEN a receipt with exactly one 22-digit CBU-shaped candidate whose check digit is deliberately wrong, and no other CBU-shaped candidate
- WHEN core-field extraction runs
- THEN `destination_cbu.normalized` is populated with that candidate's value (checksum failure detection remains the Financial validation requirement's job, producing `INVALID_CBU_CHECK_DIGIT` unchanged)

#### Scenario: Stray digit run ignored when a better candidate exists
- GIVEN a receipt with one valid 11-digit CUIT candidate and one unrelated 11-digit number (e.g. an order/reference ID) that fails the CUIT checksum
- WHEN core-field extraction runs
- THEN the `cuit` field's `normalized` value is the checksum-valid candidate, never the failing one

#### Scenario: Wide date/time format coverage including an OCR-typo month name
- GIVEN OCR text boxes with dates in varied formats — `"15/03/2026 14:30"`, `"15 de marzo de 2026"`, `"2026-03-15T14:30:00"`, and `"15 de mar20 de 2026"` (digit-for-letter typo in "marzo")
- WHEN core-field extraction runs on each
- THEN each produces a `date_time` field normalized to the same ISO 8601 instant, provided it falls within the plausibility-bounds window
