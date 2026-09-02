# Design: Receipt Analysis Implementation

> Size note: this design intentionally exceeds the default 800-word artifact budget. The
> orchestrator explicitly required literal signatures, Dockerfile/YAML snippets, the fixture
> manifest schema, and per-slice file lists so `sdd-tasks` can emit ordered tasks without
> re-deriving architecture. Prose is kept minimal; the bulk is code and tables.

## Technical Approach

Ports-and-adapters exactly as `docs/ARCHITECTURE.md` §5 defines it. Pure, I/O-free logic
(check digits, signals, ruleset, scoring) in `domain/`. Orchestration, ports, time budgets and
cleanup in `application/`. Every library that touches the outside world (Pillow, OpenCV, ONNX,
ExifTool subprocess, `c2pa`, FastAPI) lives in `adapters/`, which ruff `TID251` already enforces
via the existing `per-file-ignores`. Delivery is the 4 chained PRs the proposal locked in;
§"Slice Boundaries" below is the authoritative file-to-slice mapping.

## Architecture Decisions

### Decision: Versioned ruleset as a frozen declarative data module, not a JSON file

| Option | Tradeoff |
|---|---|
| JSON/TOML in `domain/rulesets/*.json` loaded at import | Domain performs filesystem I/O; needs a loader, schema validation and error paths; weights become untyped |
| **Frozen dataclass data module + version registry (chosen)** | Zero I/O in domain, type-checked, still a reviewable one-file diff; version string is the lookup key |
| Constants inline in the scoring functions | Explicitly forbidden by the proposal (no hardcoded weights in logic) |

**Rationale**: the proposal's requirement is "versioned ruleset config, not hardcoded weights in
Python logic" — separation of *data from logic*, not a specific file format. `ScoringRuleset` is a
frozen dataclass in `domain/ruleset.py`; concrete versions live in `domain/rulesets/v2026_09_01.py`
and register into `RULESETS: dict[str, ScoringRuleset]`. `score()` receives the ruleset as a
parameter and never reads a module global, so a file-backed loader can be added later behind
`RULESETS` without touching the engine. Determinism is structural: same inputs + same version
object → same output.

### Decision: `/v1/receipts/analyze` is NOT registered until slice 4 (404), rather than a 501 stub

| Option | Tradeoff |
|---|---|
| Register the route early, return `501` | The route *is* exposed: it appears in `/openapi.json`, `/docs`, the `analyze` rate-limit bucket and CORS preflight. Contract tests must assert a `501` that is deleted in slice 4 — throwaway tests on a public surface |
| **Router module absent until slice 4 (chosen)** | Zero public surface, zero OpenAPI leak, no throwaway contract test; slices 1–3 are reachable only from unit/integration tests |

**Rationale**: the locked product decision is "one credible launch, not incremental partial
answers". A registered `501` is still a published endpoint and would force `docs/API.md` and the
OpenAPI contract out of sync with reality for three PRs. Concretely: `adapters/api/router.py` does
not exist in slices 1–3; `bootstrap/app.py` is untouched until slice 4. FastAPI's default 404
handler answers the path, which is the honest "not implemented yet" state. Slices 1–3 are proven
by direct construction of the services/adapters in tests, not by HTTP.

### Decision: analyzer ports are `async`, adapters offload blocking work to a worker thread

**Choice**: ports are `async def`; each adapter wraps its blocking call in
`anyio.to_thread.run_sync`. Orchestration uses `anyio` task groups + `anyio.Semaphore` for bounded
concurrency and `anyio.fail_after` for per-analyzer and whole-request budgets.
**Alternatives considered**: sync ports called via `run_in_threadpool` from the router (pushes
budget logic into the adapter layer, violating "application owns time budgets"); raw `asyncio`
(Starlette already runs on anyio; mixing gives worse cancellation semantics).
**Rationale**: `anyio` is a concurrency primitive, not a framework or a tool adapter, so
`application/` may import it — it is deliberately NOT added to the ruff banned-api list. Cancellation
via `fail_after` propagates into the thread boundary cleanly and keeps cleanup in `finally`.

### Decision: a failed analyzer produces a signal, never an aborted request

**Choice**: the use case wraps every port call in a guard that converts *any* exception or timeout
into `AnalyzerResult(status="failed" | "timed_out", signals=[...], error_code=...)`. The only abort
path is a HARD ingestion failure (decode/size/dimension), which returns `4xx` before any analyzer
runs. Whole-request budget exhaustion returns `504 ANALYSIS_TIMEOUT`.
**Rationale**: `docs/ARCHITECTURE.md` §9 and the locked product decision — an unreadable receipt is
itself suspicious, never a silent no-op.

### Decision: `INCONCLUSIVE` is a whole-request evidence-coverage threshold

**Choice**: one weighted coverage number across ALL analyzers; no per-analyzer override exists
anywhere in the code.
**Alternative rejected**: `if ocr.status != "completed": return INCONCLUSIVE` — exactly the bug the
product owner locked out.

### Decision: fixtures are committed PNG/JPEG bytes plus a regeneration script

| Option | Tradeoff |
|---|---|
| Render receipts at test time with Pillow | Pillow/font version drift changes rendered glyphs → OCR assertions flake across machines and CI |
| Photo-like assets (camera captures, real templates) | Forbidden: no real bank templates, no real receipts (AGENTS.md fixture policy) |
| **Committed bytes + `samples/generate.py --update` + sha256 in the manifest (chosen)** | Deterministic for OCR, drift is detectable, regeneration is a deliberate reviewable diff |

## Data Flow

```text
POST /v1/receipts/analyze (slice 4 only)
        │
   adapters/api/router.py ── Pydantic request/response, problem+json errors
        │
   application/analyze_receipt.py ── AnalyzeReceiptUseCase.execute()
        │
        ├─ 1. IngestionService.ingest()  ── HARD gate: type/size/decode/dimensions/pixels
        │       └─ adapters/image/pillow_decoder.py → SafeImageRef(path, sha256, w, h)
        │
        ├─ 2. bounded-concurrency fan-out (anyio task group, semaphore=2)
        │       ├─ OcrPort.extract()        ─ budget 6.0 s
        │       ├─ MetadataPort.inspect()   ─ budget 2.0 s
        │       └─ ProvenancePort.inspect() ─ budget 2.0 s
        │            (each guarded → AnalyzerResult, never raises)
        │
        ├─ 3. domain financial validators over ocr.extracted_fields  (pure, sequential)
        │       └─ → list[ValidationSignal]
        │
        ├─ 4. domain.scoring.score(signals, statuses, ruleset) → FraudAssessment
        │
        └─ finally: TempFileGuard.cleanup()  ── runs on success, error, timeout, cancellation
```

## Interfaces / Contracts

### Domain — signals (`domain/signals.py`, slice 1; codes extended in 2/3/4)

```python
class SignalCategory(StrEnum):
    METADATA = "metadata"
    PROVENANCE = "provenance"
    FINANCIAL_CONSISTENCY = "financial_consistency"
    DATA_QUALITY = "data_quality"          # new category, per locked decision

class Severity(StrEnum):
    INFO = "info"; LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

class SignalCode(StrEnum):
    # slice 2
    METADATA_EDITOR_SOFTWARE = "METADATA_EDITOR_SOFTWARE"
    VALID_AI_GENERATED_CLAIM = "VALID_AI_GENERATED_CLAIM"
    # slice 3
    INVALID_CBU_CHECK_DIGIT = "INVALID_CBU_CHECK_DIGIT"
    INVALID_CUIT_CHECK_DIGIT = "INVALID_CUIT_CHECK_DIGIT"
    AMOUNT_DATE_CONTRADICTION = "AMOUNT_DATE_CONTRADICTION"
    DATE_OUT_OF_BOUNDS = "DATE_OUT_OF_BOUNDS"
    CORE_FIELD_EXTRACTION_FAILED = "CORE_FIELD_EXTRACTION_FAILED"   # category DATA_QUALITY
    # slice 4
    ANALYZER_UNAVAILABLE = "ANALYZER_UNAVAILABLE"

class ExtractionFailureReason(StrEnum):
    LOW_CONFIDENCE = "low_confidence"
    NO_TEXT_DETECTED = "no_text_detected"
    TIMEOUT = "timeout"

@dataclass(frozen=True, slots=True)
class ValidationSignal:
    code: SignalCode
    category: SignalCategory
    severity: Severity
    confidence: Decimal              # 0..1, quantized to 2dp for determinism
    description: str
    evidence: Mapping[str, str]      # masked values only — never raw CBU/CUIT/amount
    score_contribution: int = 0      # filled by the scorer, not by adapters
```

`evidence` is `Mapping[str, str]` by construction so no adapter can smuggle raw bytes or unmasked
financial data into a signal (`data-retention` spec, log-masking scenario).

### Domain — analyzer result (`domain/analysis.py`, slice 1)

```python
AnalyzerStatus = Literal["completed", "partial", "failed", "timed_out"]

@dataclass(frozen=True, slots=True)
class ExtractedField:
    name: str                  # "amount" | "date_time" | "destination_cbu" | ...
    raw_text: str
    normalized: str | None
    confidence: Decimal

@dataclass(frozen=True, slots=True)
class AnalyzerResult:
    analyzer: str
    version: str
    status: AnalyzerStatus
    signals: tuple[ValidationSignal, ...] = ()
    extracted_fields: tuple[ExtractedField, ...] = ()
    duration_ms: int = 0
    error_code: str | None = None
```

### Domain — CBU/CVU validator (`domain/financial/cbu.py`, slice 3)

```python
CBU_BLOCK1_WEIGHTS: Final[tuple[int, ...]] = (7, 1, 3, 9, 7, 1, 3)
CBU_BLOCK2_WEIGHTS: Final[tuple[int, ...]] = (3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3)

class ChecksumFailure(StrEnum):
    NON_NUMERIC = "non_numeric"
    BAD_LENGTH = "bad_length"
    BLOCK1_CHECK_DIGIT = "block1_check_digit"
    BLOCK2_CHECK_DIGIT = "block2_check_digit"
    CHECK_DIGIT = "check_digit"

@dataclass(frozen=True, slots=True)
class ChecksumResult:
    is_valid: bool
    normalized: str | None = None
    failure: ChecksumFailure | None = None

def mod10_check_digit(digits: Sequence[int], weights: Sequence[int]) -> int:
    """DV = (10 - sum(d*w) % 10) % 10."""
    return (10 - sum(d * w for d, w in zip(digits, weights, strict=True)) % 10) % 10

def validate_cbu(raw: str) -> ChecksumResult:
    """22 digits: block1 = d[0:7] + DV d[7]; block2 = d[8:21] + DV d[21]. Accepts CBU and CVU."""
```

Known-answer tests (literal, slice 3 RED tests):

```python
def test_cbu_known_answer_block_digits() -> None:
    digits = [int(c) for c in "2850590940090418135201"]
    assert mod10_check_digit(digits[0:7], CBU_BLOCK1_WEIGHTS) == 9   # equals digits[7]
    assert mod10_check_digit(digits[8:21], CBU_BLOCK2_WEIGHTS) == 1  # equals digits[21]

def test_validate_cbu_accepts_known_valid() -> None:
    assert validate_cbu("2850590940090418135201") == ChecksumResult(
        is_valid=True, normalized="2850590940090418135201"
    )

def test_validate_cbu_rejects_mutated_block2_check_digit() -> None:
    result = validate_cbu("2850590940090418135202")
    assert result.is_valid is False
    assert result.failure is ChecksumFailure.BLOCK2_CHECK_DIGIT
```

### Domain — CUIT/CUIL validator (`domain/financial/cuit.py`, slice 3)

```python
CUIT_WEIGHTS: Final[tuple[int, ...]] = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)

def validate_cuit(raw: str) -> ChecksumResult:
    """11 digits (hyphens/spaces stripped). dv = 11 - sum(d*w) % 11; 11 -> 0; 10 -> invalid."""
```

```python
def test_validate_cuit_known_answer() -> None:
    # sum = 136; 136 % 11 == 4; 11 - 4 == 7 == declared check digit
    assert validate_cuit("20-17254359-7").is_valid is True
    assert validate_cuit("20172543597").normalized == "20172543597"

def test_validate_cuit_rejects_wrong_check_digit() -> None:
    result = validate_cuit("20-17254359-8")
    assert result.is_valid is False
    assert result.failure is ChecksumFailure.CHECK_DIGIT
```

### Domain — ruleset and scoring (`domain/ruleset.py`, `domain/scoring.py`, slice 4)

```python
@dataclass(frozen=True, slots=True)
class ScoringRuleset:
    version: str                                   # "2026-09-01"
    weights: Mapping[SignalCode, int]              # base points per signal code
    severity_multiplier: Mapping[Severity, Decimal]
    critical_floor: Mapping[SignalCode, int]       # e.g. VALID_AI_GENERATED_CLAIM -> 85
    analyzer_evidence_weights: Mapping[str, Decimal]  # ocr .50, metadata .20, provenance .30
    status_quality: Mapping[AnalyzerStatus, Decimal]  # completed 1.0, partial .5, failed/timed_out 0
    inconclusive_coverage_threshold: Decimal       # 0.35
    bands: tuple[tuple[int, Classification], ...]  # (24,LOW),(49,REVIEW),(74,SUSPICIOUS),(100,HIGH)

RULESETS: Final[Mapping[str, ScoringRuleset]] = {RULESET_2026_09_01.version: RULESET_2026_09_01}
```

```python
def score(
    signals: Sequence[ValidationSignal],
    statuses: Sequence[AnalyzerResult],
    ruleset: ScoringRuleset,
) -> ScoreBreakdown: ...
```

Risk score (all arithmetic in `Decimal`, never float, then `int()` truncation — reproducible):

```text
contribution(s) = int(ruleset.weights[s.code] * ruleset.severity_multiplier[s.severity] * s.confidence)
risk_score      = min(100, sum(contribution(s) for s in signals))
risk_score      = max(risk_score, max(critical_floor[s.code] for critical signals present))
```

Confidence and `INCONCLUSIVE` — one number across ALL analyzers, never per analyzer:

```text
completeness(ocr)        = extracted core fields / 4          # amount, cbu/cvu, cuit/cuil, date
completeness(metadata)   = 1 if status == completed else 0    # absent metadata is a COMPLETE,
completeness(provenance) = 1 if status == completed else 0    # neutral observation, not missing evidence

evidence_coverage = Σ_a  analyzer_evidence_weights[a] * status_quality[status_a] * completeness(a)
confidence_score  = int(100 * evidence_coverage)              # independent of risk_score
classification    = INCONCLUSIVE if evidence_coverage < 0.35 else band_for(risk_score)
```

Locked-decision check: OCR fails completely, metadata + provenance complete →
coverage `0.20 + 0.30 = 0.50 ≥ 0.35` → NOT `INCONCLUSIVE`; `risk_score` still rises via
`CORE_FIELD_EXTRACTION_FAILED`; `confidence_score` drops to 50. All three failing → `0.0` →
`INCONCLUSIVE`. `recommended_action`: LOW/REVIEW → `STANDARD_MANUAL_RECONCILIATION`; SUSPICIOUS and
INCONCLUSIVE → `PRIORITY_MANUAL_RECONCILIATION`; HIGH_RISK → `DO_NOT_RELY_ON_RECEIPT`.

### Application — ports (`application/ports.py`)

```python
@runtime_checkable
class ImageDecoderPort(Protocol):                                       # slice 1
    def probe(self, data: bytes) -> DecodedImageInfo: ...               # media_type, w, h, pixels

@runtime_checkable
class MetadataPort(Protocol):                                           # slice 2
    name: str
    version: str
    async def inspect(self, image: SafeImageRef) -> AnalyzerResult: ...

@runtime_checkable
class ProvenancePort(Protocol):                                         # slice 2
    name: str
    version: str
    async def inspect(self, image: SafeImageRef) -> AnalyzerResult: ...

@runtime_checkable
class OcrPort(Protocol):                                                # slice 3
    name: str
    version: str
    async def extract(self, image: SafeImageRef) -> AnalyzerResult: ...
```

Every port returns `AnalyzerResult` — a domain type. No port signature mentions `dict`, JSON, a
subprocess handle, a Pillow image, or any tool-specific type, so raw tool output can never cross
the boundary.

### Application — request models and use case

```python
@dataclass(frozen=True, slots=True)
class SafeImageRef:
    path: Path; sha256: str; media_type: str; width: int; height: int; byte_size: int

@dataclass(frozen=True, slots=True)
class TimeBudget:
    whole_request_s: float = 10.0     # NFR-001 p95
    ocr_s: float = 6.0                # includes the single preprocessing retry
    metadata_s: float = 2.0
    provenance_s: float = 2.0
    max_concurrent_analyzers: int = 2

class AnalyzeReceiptUseCase:
    def __init__(self, *, ocr: OcrPort, metadata: MetadataPort, provenance: ProvenancePort,
                 ingestion: IngestionService, ruleset: ScoringRuleset,
                 budget: TimeBudget, clock: Clock) -> None: ...

    async def execute(self, upload: UploadRequest) -> FraudAssessment:
        safe = self.ingestion.ingest(upload)          # HARD gate; raises IngestionError -> 4xx
        try:
            with anyio.fail_after(self.budget.whole_request_s):
                results = await self._run_analyzers(safe)
            signals = [*chain.from_iterable(r.signals for r in results)]
            signals += validate_financials(ocr_result_of(results).extracted_fields)
            return assemble(safe, results, signals, self.ruleset)
        finally:
            self.ingestion.cleanup(safe)              # success, error, timeout, cancellation
```

`_run_analyzers` guard (this is the "failure becomes a signal" contract):

```python
async def _guarded(self, port, run, budget_s: float, name: str) -> AnalyzerResult:
    started = self.clock.monotonic_ms()
    try:
        with anyio.fail_after(budget_s):
            return await run(port)
    except TimeoutError:
        return AnalyzerResult(name, port.version, "timed_out",
                              signals=timeout_signals(name), error_code="ANALYZER_TIMEOUT",
                              duration_ms=self.clock.monotonic_ms() - started)
    except Exception:                                  # never leaks a tool exception upward
        log.warning("analyzer_failed", extra={"analyzer": name})   # no payload, no raw text
        return AnalyzerResult(name, port.version, "failed",
                              signals=failure_signals(name), error_code="ANALYZER_FAILED",
                              duration_ms=self.clock.monotonic_ms() - started)
```

For `ocr`, `timeout_signals`/`failure_signals` emit `CORE_FIELD_EXTRACTION_FAILED` with
`reason=timeout` / the adapter's reason; for metadata/provenance they emit
`ANALYZER_UNAVAILABLE` at `info` severity with weight `0` (a tool outage is not evidence of fraud —
it only lowers `confidence_score` through `status_quality`).

### OCR adapter — bounded single retry (`adapters/ocr/paddle_onnx.py`, slice 3)

```text
attempt 1  raw decode → engine.recognize(image)
           boxes == 0                                   → reason = NO_TEXT_DETECTED
           coverage = core fields with conf >= 0.60, / 4
           coverage >= 0.75                             → status="completed", return
                                    ↓ below threshold
retry gate remaining_budget_ms >= est_attempt_ms (measured from attempt 1)?
           no                                           → reason = TIMEOUT, stop
           yes ↓
attempt 2  preprocess(image): deskew (min-area rect over the binarized text mask, |angle| <= 15°)
                              → CLAHE contrast normalization → unsharp mask
                              (fixed parameters, no randomness — determinism requirement)
           engine.recognize(preprocessed)
           keep the better result by (coverage, mean_confidence) — attempt 2 never loses data
           coverage >= 0.75                             → status="completed"
           else                                         → status="partial",
                signals=[CORE_FIELD_EXTRACTION_FAILED(reason=LOW_CONFIDENCE|NO_TEXT_DETECTED,
                         severity=medium,
                         evidence={"retry_count": "1", "core_field_coverage": "0.25"})]
```

Exactly one retry. No second OCR engine in the request path (Tesseract stays a benchmark
comparator only). The extraction-failure signal is emitted by the adapter as a domain
`ValidationSignal` — it is never a silent gap and it never forces `INCONCLUSIVE` by itself.

### Metadata adapter — safe subprocess (`adapters/metadata/exiftool.py`, slice 2)

```python
_EXIFTOOL: Final[str | None] = shutil.which("exiftool")   # absolute path resolved once (ruff S607)

def _run_exiftool(path: Path, timeout_s: float) -> str:
    if _EXIFTOOL is None:
        raise ExifToolUnavailable
    completed = subprocess.run(                            # noqa: S603 — fixed argv, shell=False
        [_EXIFTOOL, "-json", "-n", "-charset", "utf8", "-fast2", "--", str(path)],
        capture_output=True, text=True, timeout=timeout_s,
        shell=False, check=False, env={"PATH": os.defpath, "LANG": "C"},
    )
    return completed.stdout
```

Injection surface is closed structurally: fixed argv list, `shell=False`, `--` end-of-options, and
`path` is always a server-generated temp path — the client-supplied filename is discarded at
ingestion and never reaches argv. `timeout` bounds a hung binary; a `TimeoutExpired` becomes
`status="timed_out"` at the port boundary. Absence of metadata → `status="completed"` with zero
signals (never risk-reducing, per the spec's "missing metadata is neutral" scenario).

### Provenance adapter — `c2pa-python` Reader only (`adapters/provenance/c2pa_reader.py`, slice 2)

```python
from c2pa import Reader          # Reader only; no Builder, no signer, no CLI subprocess

def _read_manifest(path: Path) -> dict[str, Any] | None:
    try:
        with Reader(str(path)) as reader:
            return json.loads(reader.json())
    except Exception:            # no manifest / unsupported format — neutral, not an error
        return None
```

`VALID_AI_GENERATED_CLAIM` (severity `critical`) is emitted only when the active manifest has an
empty `validation_status` (claim verified) AND an assertion whose `digitalSourceType` indicates
algorithmic media. A manifest that fails validation emits a separate lower-severity signal; a
missing manifest emits nothing.

### API adapter (`adapters/api/`, slice 4 only)

`schemas.py` mirrors `docs/API.md` §3 field-for-field in `snake_case`: `AnalyzeResponse`
(`analysis_id`, `engine_version`, `ruleset_version`, `classification`, `risk_score`,
`confidence_score`, `recommended_action`, `signals[]`, `extracted_data`, `analyzer_statuses[]`,
`limitations[]`, `duration_ms`), `SignalModel`, `ExtractedDataModel`, `AnalyzerStatusModel`, and
`ProblemDetails` (`type`, `title`, `status`, `detail`, `instance`, `request_id`, `code`) for the
seven documented error codes. `router.py` holds one `POST /v1/receipts/analyze` handler that reads
the `file` part, calls `AnalyzeReceiptUseCase.execute`, and maps `IngestionError.code` → the
documented status. Domain→transport mapping is one-directional in `mappers.py`; domain objects
never carry Pydantic types.

## File Changes

| File | Action | Slice |
|---|---|---|
| `apps/api/src/receipt_risk/domain/__init__.py` | Create | 1 |
| `apps/api/src/receipt_risk/domain/signals.py` | Create / extend in 2,3,4 | 1 |
| `apps/api/src/receipt_risk/domain/analysis.py` | Create | 1 |
| `apps/api/src/receipt_risk/application/models.py` | Create | 1 |
| `apps/api/src/receipt_risk/application/errors.py` | Create | 1 |
| `apps/api/src/receipt_risk/application/ingestion.py` | Create | 1 |
| `apps/api/src/receipt_risk/application/ports.py` | Create / extend in 2,3 | 1 |
| `apps/api/src/receipt_risk/adapters/image/pillow_decoder.py` | Create | 1 |
| `samples/generate.py`, `samples/fonts/DejaVuSans.ttf`, `samples/images/*`, `samples/manifest.json` | Create | 1 |
| `apps/api/tests/conftest.py`, `tests/unit/test_ingestion.py`, `tests/fixtures/test_manifest_integrity.py` | Create | 1 |
| `apps/api/tests/test_placeholder.py` | Delete | 1 |
| `apps/api/pyproject.toml` | Modify (Pillow, bandit rules, banned-api) | 1, 2, 3 |
| `apps/api/src/receipt_risk/adapters/metadata/exiftool.py` | Create | 2 |
| `apps/api/src/receipt_risk/adapters/provenance/c2pa_reader.py` | Create | 2 |
| `apps/api/Dockerfile` | Modify (exiftool apt layer) | 2 |
| `.github/workflows/ci.yml` | Modify (system-dependency step) | 2 |
| `apps/api/src/receipt_risk/domain/financial/{cbu,cuit,money,dates,contradictions}.py` | Create | 3 |
| `apps/api/src/receipt_risk/application/financial_validation.py` | Create | 3 |
| `apps/api/src/receipt_risk/adapters/ocr/{paddle_onnx,preprocess,field_parsers}.py` | Create | 3 |
| `apps/api/scripts/fetch_ocr_models.py` | Create | 3 |
| `apps/api/Dockerfile` | Modify (OCR model-baking stage) | 3 |
| `.github/workflows/ci.yml` | Modify (model cache + fetch) | 3 |
| `apps/api/src/receipt_risk/domain/{ruleset,scoring,assessment}.py`, `domain/rulesets/v2026_09_01.py` | Create | 4 |
| `apps/api/src/receipt_risk/application/analyze_receipt.py` | Create | 4 |
| `apps/api/src/receipt_risk/adapters/api/{router,schemas,mappers,errors,dependencies}.py` | Create | 4 |
| `apps/api/src/receipt_risk/bootstrap/app.py` | Modify (register router, `/ready`, `/version`) | 4 |
| `docs/features/receipt-analysis/{SDD,TDD,RDD}.md` | Create (mirror, per `config.yaml` `rules.design`) | 4 |

### `pyproject.toml` — exact additions

```toml
# [project] dependencies
"Pillow>=11.0",                    # slice 1
"c2pa-python>=0.7",                # slice 2
"onnxruntime>=1.20",               # slice 3
"opencv-python-headless>=4.10",    # slice 3
"rapidocr-onnxruntime>=1.4",       # slice 3 — PaddleOCR PP-OCRv4 models on ONNX Runtime

[tool.ruff.lint]
# S602/S604/S605/S607 have NO per-file-ignore on purpose: adapters/** is exempt from TID251
# but must still never reach a shell or a partial-path executable.
select = ["E", "F", "I", "UP", "B", "TID", "S602", "S604", "S605", "S607"]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"subprocess".msg = "Subprocess execution is adapter-only; fixed argv, shell=False, always a timeout."
"c2pa".msg = "C2PA is an adapter-only dependency."
"onnxruntime".msg = "ONNX Runtime is an adapter-only dependency."
"rapidocr_onnxruntime".msg = "The OCR engine is an adapter-only dependency."
```

`per-file-ignores` stays exactly as it is today (`adapters/**`, `bootstrap/**`, `tests/**` ignore
`TID251`); `anyio` is deliberately NOT banned because `application/` owns time budgets and bounded
concurrency.

### `apps/api/Dockerfile` — exact additions

Slice 2 adds the runtime system package; slice 3 prepends the model stage and the model env vars.

```dockerfile
# syntax=docker/dockerfile:1

# ---- slice 3: OCR model pre-baking (no network access at container start) ----
FROM python:3.12-slim AS ocr-models
RUN pip install --no-cache-dir uv
WORKDIR /build
COPY apps/api/scripts/fetch_ocr_models.py ./
# Pinned model set + sha256 verification live inside the script so the pin is reviewable.
RUN pip install --no-cache-dir "requests==2.32.3" \
 && python fetch_ocr_models.py --dest /opt/ocr-models --verify

# ---- runtime ----
FROM python:3.12-slim

# slice 2: ExifTool binary. libglib2.0-0 is required by opencv-python-headless (slice 3);
# libgl1 is deliberately NOT installed because the headless wheel does not link libGL.
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      libimage-exiftool-perl \
      libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv
WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev --extra server

# slice 3: baked models; the OCR adapter must never download at request or startup time.
COPY --from=ocr-models /opt/ocr-models /opt/ocr-models
ENV RECEIPT_RISK_OCR_MODEL_DIR=/opt/ocr-models \
    HF_HUB_OFFLINE=1 \
    OMP_NUM_THREADS=2

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "receipt_risk.bootstrap.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `.github/workflows/ci.yml` — exact additions

Insert immediately after `- uses: actions/checkout@v4` (slice 2):

```yaml
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install --no-install-recommends -y libimage-exiftool-perl libglib2.0-0
          exiftool -ver
```

Insert after `Sync dependencies` (slice 3):

```yaml
      - name: Cache OCR models
        uses: actions/cache@v4
        with:
          path: ~/.cache/receipt-risk/ocr-models
          key: ocr-models-${{ hashFiles('apps/api/scripts/fetch_ocr_models.py') }}

      - name: Fetch OCR models
        run: uv run python scripts/fetch_ocr_models.py --dest ~/.cache/receipt-risk/ocr-models --verify

      - name: Test
        env:
          RECEIPT_RISK_OCR_MODEL_DIR: ~/.cache/receipt-risk/ocr-models
        run: uv run pytest
```

(The existing `Test` step is replaced by the env-carrying version above; `working-directory:
apps/api` already applies to all of these.)

## Fixture Design

```text
samples/
├── manifest.json              # sidecar manifest (AGENTS.md fixture policy)
├── fonts/DejaVuSans.ttf       # vendored, license-permissive; pins glyph rendering
├── generate.py                # deterministic renderer; `python generate.py --update` rewrites bytes
└── images/
    ├── clean_valid_transfer.png
    ├── invalid_cbu_check_digit.png
    ├── low_quality_skewed.jpg      # exercises the single OCR preprocessing retry
    └── corrupted_truncated.jpg     # byte-truncated; must fail decode
```

**How a synthetic receipt image is created**: `samples/generate.py` draws a fabricated
mobile-banking receipt with Pillow — a fixed 1080x1920 white `Image.new("RGB", ...)`, a fabricated
institution name ("Banco Ejemplo", no real bank template, logo or layout), and label/value rows
(`Monto`, `Fecha y hora`, `Destinatario`, `CBU destino`, `CUIT`, `N° de operación`) rendered with
`ImageDraw.text` using the vendored `DejaVuSans.ttf` at pinned sizes. Every parameter is a literal
constant — no RNG, no system font lookup, no timestamp — so a regeneration on any machine
reproduces identical bytes. Degraded variants apply deterministic post-passes with fixed
parameters: `Image.rotate(-3.2, resample=BICUBIC, expand=True)` for skew,
`ImageEnhance.Contrast(img).enhance(0.55)`, `img.filter(GaussianBlur(1.4))`, then
`save(..., format="JPEG", quality=45)`. `corrupted_truncated.jpg` is produced by writing the first
2 KB of a valid JPEG. The rendered bytes are committed; tests never render at runtime.

**Manifest schema** (`samples/manifest.json`):

```json
{
  "schema_version": 1,
  "generator": {
    "script": "samples/generate.py",
    "pillow": "11.0.0",
    "font": "samples/fonts/DejaVuSans.ttf"
  },
  "fixtures": [
    {
      "id": "clean_valid_transfer",
      "path": "images/clean_valid_transfer.png",
      "sha256": "<64 hex>",
      "provenance": {
        "origin": "synthetic",
        "authored_by": "samples/generate.py",
        "contains_real_data": false,
        "bank_template": "fabricated"
      },
      "declared_fields": {
        "amount": "125000.00",
        "currency": "ARS",
        "date_time": "2026-09-01T14:43:00-03:00",
        "beneficiary_name": "PATRICIO EJEMPLO",
        "destination_cbu": "2850590940090418135201",
        "cuit": "20-17254359-7",
        "operation_id": "483927183"
      },
      "expected_signals": [],
      "expected_analyzer_statuses": { "ocr": "completed", "metadata": "completed", "provenance": "completed" },
      "expected_classification": "LOW_RISK",
      "notes": "Baseline: all core fields legible, valid check digits, no provenance claim."
    },
    {
      "id": "invalid_cbu_check_digit",
      "path": "images/invalid_cbu_check_digit.png",
      "sha256": "<64 hex>",
      "provenance": { "origin": "synthetic", "authored_by": "samples/generate.py",
                      "contains_real_data": false, "bank_template": "fabricated" },
      "declared_fields": { "destination_cbu": "2850590940090418135202", "amount": "125000.00" },
      "expected_signals": [
        { "code": "INVALID_CBU_CHECK_DIGIT", "category": "financial_consistency", "severity": "high" }
      ],
      "expected_analyzer_statuses": { "ocr": "completed", "metadata": "completed", "provenance": "completed" },
      "expected_classification": "REVIEW_RECOMMENDED",
      "notes": "Identical render to the baseline with only the block-2 check digit mutated 1 -> 2."
    },
    {
      "id": "corrupted_truncated",
      "path": "images/corrupted_truncated.jpg",
      "sha256": "<64 hex>",
      "provenance": { "origin": "synthetic", "authored_by": "samples/generate.py",
                      "contains_real_data": false, "bank_template": "n/a" },
      "declared_fields": {},
      "expected_signals": [],
      "expected_error": { "status": 415, "code": "UNSUPPORTED_IMAGE" },
      "notes": "First 2 KB of a valid JPEG; must be rejected at ingestion before any analyzer runs."
    }
  ]
}
```

`tests/conftest.py` loads the manifest, verifies each `sha256` (drift detection), and exposes a
`fixture("id")` helper. `expected_signals` is asserted as a subset by `code` + `severity`;
`expected_classification` is asserted as a band. Exact scorer inputs are pinned separately in the
determinism test (AGENTS.md: "keep exact scorer inputs in tests").

## Slice Boundaries

| Slice | Deliverable | Creates | Modifies | Verification |
|---|---|---|---|---|
| 1 | Ingestion + fixtures | `domain/{signals,analysis}.py`, `application/{models,errors,ingestion,ports}.py`, `adapters/image/pillow_decoder.py`, all of `samples/`, `tests/conftest.py` + ingestion/manifest tests | `pyproject.toml` (Pillow, bandit rules), delete `tests/test_placeholder.py` | Unit: size/type/decode/dimension/pixel rejection, sha256 stability, cleanup on every path, manifest sha256 integrity |
| 2 | Metadata + C2PA | `adapters/metadata/exiftool.py`, `adapters/provenance/c2pa_reader.py`, subprocess-safety tests, adapter integration tests | `application/ports.py`, `domain/signals.py`, `pyproject.toml`, `Dockerfile`, `.github/workflows/ci.yml` | Integration against `samples/`; "missing metadata is neutral"; argv/no-shell/timeout tests |
| 3 | OCR + financial validators | `domain/financial/*`, `application/financial_validation.py`, `adapters/ocr/*`, `scripts/fetch_ocr_models.py`, validator + retry tests | `application/ports.py`, `domain/signals.py`, `pyproject.toml`, `Dockerfile`, `ci.yml` | Known-answer CBU/CUIT tests; retry-path test asserting exactly one preprocessing attempt; `CORE_FIELD_EXTRACTION_FAILED` reason enum coverage |
| 4 | Risk engine + endpoint | `domain/{ruleset,scoring,assessment}.py`, `domain/rulesets/v2026_09_01.py`, `application/analyze_receipt.py`, `adapters/api/*`, `docs/features/receipt-analysis/*` | `bootstrap/app.py` (first registration of the router) | Contract test vs `docs/API.md`; determinism test; INCONCLUSIVE coverage test (OCR fails, others succeed → non-INCONCLUSIVE); forbidden-verdict-vocabulary test; log-masking privacy test |

Slice 3 is the review-budget risk: if the forecast exceeds 400 changed lines, split into 3a
(`domain/financial/*` + validator tests, no new dependency) and 3b (OCR adapter, models, infra).

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Check digits, money/date normalization, contradiction rules, scoring, coverage/`INCONCLUSIVE` | Pure functions, table-driven, known-answer fixtures from the proposal |
| Unit | Ingestion gates and cleanup | In-memory bytes + `tmp_path`; assert temp dir empty in `finally` for success/error/timeout |
| Integration | ExifTool, C2PA, OCR adapters | Real binaries against committed `samples/`; skip-marked when the binary is absent locally, required in CI |
| Contract | Response/problem+json shape vs `docs/API.md` | `TestClient` + schema assertions on every documented error code |
| E2E | Upload → assessment | `TestClient` multipart with each manifest fixture, asserting the manifest's `expected_*` |
| Privacy | No raw bytes / no unmasked CBU-CUIT-amount in logs | `caplog` scan across success and every failure path |
| Determinism | Same input + ruleset → same triple | Run `score()` twice on pinned inputs; assert exact equality of all three numbers |

## Threat Matrix

| Boundary | Minimum adversarial cases | Applicability | Design response | Planned RED tests |
|---|---|---|---|---|
| Documentation-like paths | `requirements.txt`, executable Markdown, `README.sh` | N/A: no file is classified or executed by content type; only decoded image bytes are processed | — | — |
| Git repository selection | `git -C`, relative/absolute paths | N/A: the change performs no VCS automation | — | — |
| Commit state | staged, `commit -a`, empty index | N/A: no VCS automation | — | — |
| Push state | tracking branch, first push, refspec | N/A: no VCS automation | — | — |
| PR commands | `--head`, env prefix, composed commands | N/A: no PR automation | — | — |
| **Subprocess invocation (ExifTool)** | shell metacharacters in filename, leading-`-` filename, path traversal, hung binary, missing binary | **Applicable** | Fixed argv list, `shell=False`, `--` end-of-options, server-generated temp path only (client filename discarded at ingestion), mandatory `timeout`, `shutil.which` absolute path, ruff `S602/S604/S605/S607` with no per-file ignore | (a) upload named `; rm -rf /.jpg` → argv contains the temp path, never the client name; (b) upload named `-ver.jpg` → `--` guard, no option injection; (c) stub binary that hangs → `status="timed_out"`, no orphan process; (d) `exiftool` absent → `status="failed"`, request still returns 200 |
| **Process integration (OCR model loading)** | model dir missing, network attempted at runtime | **Applicable** | Models baked into the image and located by `RECEIPT_RISK_OCR_MODEL_DIR`; the adapter never issues a network call | Adapter constructed with a bogus model dir → `ANALYZER_UNAVAILABLE`, no download attempt; a socket-blocking test asserts zero outbound connections during analysis |

## Migration / Rollout

No data migration (no persistence exists). Rollout is the 4-PR chain into `dev`, each PR merged and
CI-green before the next starts. Slices 1–3 add no public surface, so any of them reverts as pure
dead-code removal; reverting slice 4 restores the current API surface exactly (only
`bootstrap/app.py`'s router registration is removed). Infra changes are isolated to `Dockerfile`
and `ci.yml` commits and revert independently.

## Open Questions

- [ ] Producing a genuinely C2PA-signed synthetic asset for the `VALID_AI_GENERATED_CLAIM`
      integration test may require `c2pa-python` test certificates. Slice 2 fallback: unit-test the
      adapter against a captured manifest JSON string with a stubbed `Reader`, and mark the
      signed-asset integration test `skipif` until a signed fixture exists.
- [ ] `analyzer_evidence_weights` (ocr .50 / metadata .20 / provenance .30) and the `0.35`
      `INCONCLUSIVE` threshold are reasoned defaults, not benchmarked values — pinned in the
      versioned ruleset and revisited after the first real-world sampling (PRD §13 stays open).
- [ ] The NFR-001 per-analyzer split (ocr 6.0 s / metadata 2.0 s / provenance 2.0 s) is unvalidated
      until slice 3 can benchmark on the reference CPU; the whole-request 10.0 s p95 cap is fixed.

## Key Learnings

1. Not registering the analyze router until slice 4 keeps the endpoint out of OpenAPI, the rate-limit bucket and CORS preflight, which a `501` stub would not.
2. Computing `INCONCLUSIVE` from one weighted coverage number across all analyzers structurally prevents the per-analyzer override the product owner locked out.
3. Committing rendered fixture bytes with a `--update` regeneration script avoids OCR flakiness caused by Pillow and font version drift.
4. Adding ruff `S602/S604/S605/S607` without a per-file ignore restores shell-safety enforcement inside `adapters/**`, which is exempt from `TID251`.
5. Returning `AnalyzerResult` from every port makes "raw tool output never crosses the boundary" a type-level guarantee rather than a review convention.
