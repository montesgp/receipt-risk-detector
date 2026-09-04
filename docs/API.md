# Public API contract — MVP 1

## 1. Contract principles

- Versioned under `/v1`.
- JSON field names use `snake_case`.
- Analysis accepts standard `multipart/form-data`.
- No access token in MVP 1.
- No cookies or browser session required.
- Errors follow `application/problem+json`.
- OpenAPI is the executable source of truth once implementation begins.

## 2. Endpoints

### `GET /health`

Liveness only. It must not run OCR or expensive dependency checks.

### `GET /ready`

Reports whether required analyzers are initialized and the service can accept work.

### `GET /version`

Example:

```json
{
  "engine_version": "0.1.0",
  "ruleset_version": "2026-09-04",
  "analyzers": {
    "ocr": "paddleocr-adapter/0.1.0",
    "metadata": "exiftool-adapter/0.1.0",
    "provenance": "c2pa-adapter/0.1.0",
    "vision": "mobilenetv3-embedding/1.0.0"
  }
}
```

`/ready`'s `analyzers` map has the same four-entry shape (`ocr`, `metadata`,
`provenance`, `vision`).

### `POST /v1/receipts/analyze`

Request:

```http
Content-Type: multipart/form-data
Accept: application/json
```

Fields:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `file` | binary | Yes | JPEG, PNG or WebP; maximum 10 MB initially |

MVP 1 deliberately excludes base64 JSON and remote image URLs. Binary multipart works with browsers and n8n without increasing payload size unnecessarily.

## 3. Response model

```json
{
  "analysis_id": "sha256:4f4a...",
  "engine_version": "0.1.0",
  "ruleset_version": "2026-09-04",
  "classification": "SUSPICIOUS",
  "risk_score": 74,
  "confidence_score": 86,
  "recommended_action": "PRIORITY_MANUAL_RECONCILIATION",
  "signals": [
    {
      "code": "INVALID_CBU_CHECK_DIGIT",
      "category": "financial_consistency",
      "severity": "high",
      "confidence": 0.98,
      "description": "The extracted CBU does not pass its check-digit validation.",
      "evidence": {
        "field": "destination_cbu",
        "masked_value": "**************5678"
      },
      "score_contribution": 25
    }
  ],
  "extracted_data": {
    "amount": {
      "value": "125000.00",
      "confidence": 0.97
    },
    "date_time": {
      "value": "2026-09-01T14:43:00-03:00",
      "confidence": 0.88
    },
    "destination_cbu": {
      "masked_value": "**************5678",
      "confidence": 0.94
    },
    "cuit": {
      "masked_value": "*******4321",
      "confidence": 0.9
    }
  },
  "analyzer_statuses": [
    {
      "analyzer": "ocr",
      "status": "completed",
      "duration_ms": 1840
    }
  ],
  "limitations": [
    "This assessment analyzes the submitted artifact and does not confirm that a bank transfer exists or was credited."
  ],
  "duration_ms": 2310
}
```

`extracted_data` is a map of generic field objects (`value`, `masked_value`,
`confidence`, `is_checksum_valid`); there is no per-field schema and no
`currency`, `beneficiary_name`, or `operation_id` field — those are not
extracted in MVP 1. `is_checksum_valid` is part of the model but is not
currently populated by any analyzer; clients MUST treat it as optional and
never assume its presence alongside a masked identifier.

## 4. Enumerations

```text
classification:
  LOW_RISK
  REVIEW_RECOMMENDED
  SUSPICIOUS
  HIGH_RISK
  INCONCLUSIVE

recommended_action:
  STANDARD_MANUAL_RECONCILIATION
  PRIORITY_MANUAL_RECONCILIATION
  DO_NOT_RELY_ON_RECEIPT

severity:
  info
  low
  medium
  high
  critical

analyzer status:
  completed
  partial
  failed
  timed_out

signal category:
  metadata
  provenance
  financial_consistency
  data_quality
  visual
```

### Signal codes (selected)

| Code | Category | Typical severity | Meaning |
| --- | --- | --- | --- |
| `VALID_AI_GENERATED_CLAIM` | `provenance` | critical | A valid C2PA manifest declares algorithmic generation. |
| `PROVENANCE_VALIDATION_FAILED` | `provenance` | medium | A C2PA manifest is present but fails validation. |
| `INVALID_CBU_CHECK_DIGIT` / `INVALID_CUIT_CHECK_DIGIT` | `financial_consistency` | high | An extracted identifier fails its check-digit validation. |
| `CORE_FIELD_EXTRACTION_FAILED` | `data_quality` | medium | OCR could not reliably extract one or more core fields. |
| `ANALYZER_UNAVAILABLE` | `data_quality` | info | An analyzer did not run or did not complete (never a response status; see §5). |
| `VISUAL_ANOMALY_DETECTED` | `visual` | low or medium | The receipt's MobileNetV3 embedding is a cosine-distance outlier relative to the bundled reference set of legitimate receipt renders. This is a distributional-outlier finding only — it never claims the image is AI-generated (that wording is exclusive to `VALID_AI_GENERATED_CLAIM`) and never forces `classification` on its own. |

## 5. Error format

```json
{
  "type": "https://project.example/problems/unsupported-image",
  "title": "Unsupported image",
  "status": 415,
  "detail": "The uploaded content could not be decoded as JPEG, PNG or WebP.",
  "instance": "/v1/receipts/analyze",
  "request_id": "req_01...",
  "code": "UNSUPPORTED_IMAGE"
}
```

Expected errors:

| Status | Code |
| ---: | --- |
| 400 | `MISSING_FILE` |
| 413 | `FILE_TOO_LARGE` |
| 415 | `UNSUPPORTED_IMAGE` |
| 422 | `IMAGE_DIMENSIONS_EXCEEDED` |
| 429 | `RATE_LIMITED` |
| 504 | `ANALYSIS_TIMEOUT` |

**`ANALYZER_UNAVAILABLE` is not a response status.** A failed or unavailable
analyzer (e.g. OCR models missing, ExifTool binary absent) never aborts the
request — per the locked "never abort, always signal" decision, it surfaces
as a `CORE_FIELD_EXTRACTION_FAILED`-style `ValidationSignal` inside a normal
`200` `FraudAssessment`, contributing to `risk_score`, and can push
`classification` to `INCONCLUSIVE` if overall evidence coverage falls below
threshold (see `openspec/specs/receipt-analysis/spec.md`). `ANALYZER_UNAVAILABLE`
only appears internally as an `AnalyzerResult.error_code`, never on the wire.

## 5b. Rate limiting

Implements NFR-003 and proposal decision D2. Full mechanism, algorithm and buckets are specified in
`openspec/changes/mvp-init-foundation/specs/api-rate-limiting/spec.md` and
`openspec/changes/mvp-init-foundation/design.md` (DD5, DD6); this section documents the client-facing
contract.

**Limits** (env-configurable, defaults):

| Bucket | Default limit | Applies to |
| --- | --- | --- |
| `default` | 30 requests/minute | Every non-exempt route |
| `analyze` | 10 requests/minute | `POST /v1/receipts/analyze` |

Exempt paths: `OPTIONS` preflights, `GET /health`, `GET /ready`, `GET /version`.

**`429` response body** (`application/problem+json`):

```json
{
  "type": "https://project.example/problems/rate-limited",
  "title": "Too many requests",
  "status": 429,
  "detail": "Rate limit exceeded for this client. Retry after the indicated interval.",
  "instance": "/v1/receipts/analyze",
  "request_id": "req_01...",
  "code": "RATE_LIMITED"
}
```

**Headers on every response** (limited or not):

| Header | Meaning |
| --- | --- |
| `RateLimit-Limit` | Bucket capacity for the matched route |
| `RateLimit-Remaining` | Tokens remaining after this request |
| `RateLimit-Reset` | Seconds until the bucket is fully refilled |
| `Retry-After` | Present only on `429`; integer seconds, ceiling of the time to the next available token |

CORS headers (`Access-Control-Allow-Origin`, etc.) are present on `429` responses for allowlisted
origins, because the rate limiter runs inside the CORS middleware, not in front of it.

**Documented MVP1 limitation**: the token bucket is in-process and non-persistent. It resets on every
restart/redeploy and is not shared across multiple running instances — horizontal scaling multiplies
the effective limit by the instance count. This is abuse damping, not a distributed rate-limiting
guarantee. See `docs/ARCHITECTURE.md` §11 for the architectural framing and
`docs/adr/0003-rate-limit-token-bucket.md` for the algorithm decision. Shared-store limiting is
deferred to the authentication phase (`docs/ROADMAP.md` Phase 4).

## 6. n8n flow

```mermaid
flowchart LR
    A["WhatsApp or Telegram trigger"] --> B["Download binary image"]
    B --> C["HTTP Request node"]
    C -->|"POST multipart file"| D["/v1/receipts/analyze"]
    D --> E["Switch on classification"]
    E --> F["Send concise assessment"]
```

HTTP Request node requirements:

- Method: `POST`.
- Body content type: `multipart/form-data`.
- Parameter name: `file`.
- Parameter type: n8n binary file.
- Response: JSON.
- Client timeout: greater than the documented API analysis timeout.

Bots should communicate the classification, score, strongest signals and the need for bank reconciliation. They must not tell the user that the transfer is definitively real or fake.

## 7. Compatibility policy

- Additive response fields may appear within `v1`.
- Existing fields, enum meanings and error codes are not removed or repurposed within `v1`.
- New mandatory request fields require a new API version.
- Every scoring response exposes ruleset and engine versions.
