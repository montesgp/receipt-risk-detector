# Delta for Receipt Analysis

> Note on requirement selection: the main `receipt-analysis` spec has no existing
> requirement named for analyzer availability/lifecycle or "parallel analyzer
> fan-out" (that requirement, `Vision analyzer graceful degradation`, lives only
> in the not-yet-archived `visual-anomaly-detection` change and is not part of
> the merged main spec yet). Per fallback guidance, this delta MODIFIES
> `Analysis latency budget` — the closest merged requirement governing when
> analyzer cost is paid relative to a request — since eager warmup changes
> *when* model-loading cost is incurred (container startup vs. first request)
> without touching the budget values themselves.

## MODIFIED Requirements

### Requirement: Analysis latency budget
The system MUST complete the end-to-end upload → validate → preprocess → analyze → score → respond flow within the documented latency targets on the reference CPU and fixture set (NFR-001).

The system MUST warm the OCR and vision models during application startup, before the ASGI server accepts any inbound connection, so that the first real request after a process start is subject to the same per-analyzer time budgets as request N (`TimeBudget.ocr_s`, `TimeBudget.vision_s`, `TimeBudget.whole_request_s`, `TimeBudget.max_concurrent_analyzers` remain unchanged and are not part of this delta). Startup warmup MUST run the OCR and vision warmup steps concurrently, not sequentially, so the added startup delay is bounded by the slower of the two rather than their sum. Startup warmup MUST NOT raise or abort application startup when a required model directory is missing or misconfigured: the affected analyzer's warmup step MUST fail silently (logged, not raised), the application MUST still start and become reachable, and the existing per-request `ANALYZER_UNAVAILABLE` degradation contract for that analyzer MUST apply unchanged to the first and every subsequent real request. This requirement change does not alter `/health` behavior, `TimeBudget` values, or any per-request analyzer-availability contract.
(Previously: OCR and vision models loaded lazily on first use with no startup warmup step, so the first request after any process start paid full model-load latency inside its own per-analyzer time budget with no startup-time mitigation.)

#### Scenario: Typical request meets p50 target
- GIVEN a supported receipt image submitted on the documented reference CPU and fixture set
- WHEN the request follows the normal upload-to-response flow
- THEN the median (p50) end-to-end analysis time is under 4 seconds (NFR-001)

#### Scenario: Slow request still meets p95 target and shows processing state
- GIVEN a supported receipt image whose analysis exceeds the p50 target
- WHEN the request runs past 300 ms without a response
- THEN the client shows a processing state, and the response still completes within the p95 target of 10 seconds (NFR-001)

#### Scenario: First request after a fresh process start meets the same budgets as request N
- GIVEN a freshly started application process with both `RECEIPT_RISK_OCR_MODEL_DIR` and `RECEIPT_RISK_VISION_MODEL_DIR` correctly configured
- WHEN the very first inbound connection is accepted and a receipt is analyzed
- THEN OCR and vision analyzers meet their configured per-analyzer time budgets on this first request, identically to any later request

#### Scenario: Connection acceptance is gated on warmup completion
- GIVEN an application process starting up with both model directories configured
- WHEN the process is starting
- THEN the ASGI server does not accept any inbound connection until both the OCR and vision warmup steps have finished (successfully or by failing closed), so no request can observe a partially warmed process

#### Scenario: OCR and vision warmup run concurrently, not sequentially
- GIVEN an application process starting up with both model directories configured
- WHEN startup warmup executes
- THEN the total added startup latency is bounded by the slower of the OCR and vision warmup durations, not their sum

#### Scenario: Missing OCR model directory fails warmup closed without blocking startup
- GIVEN `RECEIPT_RISK_OCR_MODEL_DIR` is unset or points to a missing/misconfigured location
- WHEN the application starts
- THEN OCR warmup fails silently and is logged, the application still starts and becomes reachable, and the first real request needing OCR still receives the existing `ANALYZER_UNAVAILABLE` degradation, unchanged from pre-warmup behavior

#### Scenario: Missing vision model directory fails warmup closed without blocking startup
- GIVEN `RECEIPT_RISK_VISION_MODEL_DIR` is unset or points to a missing/misconfigured location
- WHEN the application starts
- THEN vision warmup fails silently and is logged, the application still starts and becomes reachable, and the first real request needing vision still receives the existing `ANALYZER_UNAVAILABLE` degradation, unchanged from pre-warmup behavior

#### Scenario: Non-regression of health, budgets, and the availability contract
- GIVEN this warmup change is deployed
- WHEN `/health` is polled, `TimeBudget` configuration is inspected, or an analyzer becomes unavailable at request time for any reason
- THEN `/health` behavior, `TimeBudget` values (`ocr_s`, `vision_s`, `whole_request_s`, `max_concurrent_analyzers`), and the per-request `ANALYZER_UNAVAILABLE` contract are all byte-for-byte identical to pre-change behavior

## Key Learnings

1. Eager warmup is expressed as MODIFIED on `Analysis latency budget`, the closest merged requirement, because no merged analyzer-availability/lifecycle requirement exists yet in the main spec.
2. Fail-closed parity is the non-negotiable core of this delta: warmup failure must never raise during startup, only defer to the existing per-request `ANALYZER_UNAVAILABLE` path.
3. Concurrency of OCR and vision warmup is a testable latency property (`max`, not `sum`), not merely an implementation detail.
