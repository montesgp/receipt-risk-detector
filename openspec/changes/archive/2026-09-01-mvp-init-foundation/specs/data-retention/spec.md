# Data Retention Specification

## Purpose

No persistence of images, OCR output, or results beyond the request lifecycle in MVP1; log minimization (PRD FR-011; SECURITY.md; AGENTS.md privacy invariants).

## Requirements

### Requirement: No durable storage of receipts or results
The system MUST NOT retain uploaded images, OCR output, or analysis results beyond the request lifecycle in MVP1 (FR-011).

#### Scenario: No database write occurs
- GIVEN a completed analysis request
- WHEN the response is returned to the client
- THEN no image bytes, OCR text, or result payload are written to any database or durable store

#### Scenario: Temp files deleted after processing
- GIVEN an uploaded image processed through preprocessing and analysis
- WHEN the request lifecycle ends, whether success or failure
- THEN all temporary files created for that request are deleted (FR-002)

### Requirement: Minimal, non-sensitive operational logs
Infrastructure request logs MAY retain minimal operational metadata (request ID, duration, status code, engine version) but MUST NOT log raw financial content or sensitive extracted fields (FR-011, NFR-005).

#### Scenario: Sensitive fields masked in logs
- GIVEN an analysis request that extracts a CBU/CVU or CUIT/CUIL
- WHEN the request is logged
- THEN the log entry contains only request ID, duration, status code, and engine version, and no raw CBU/CVU, CUIT/CUIL, amount, or name

#### Scenario: Raw file content never logged
- GIVEN any uploaded image, valid or malformed
- WHEN the system logs the request
- THEN raw file bytes or decoded pixel content never appear in log output (FR-002)

## Key Learnings

1. FR-011 and FR-002's temp-cleanup requirement together define the full retention boundary: nothing outlives the single request.
2. Log-masking rules apply to structured/extracted data (CBU, CUIT, amounts), not only to raw file bytes.
