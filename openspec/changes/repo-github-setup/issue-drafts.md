# Issue Drafts (orchestrator-published, one per capability spec)

Per user decision 4 (design T8): title + short summary + spec link + labels. **No copied
Given/When/Then** — each `openspec/specs/{slug}/spec.md` is the single source of requirements;
copying it here would guarantee drift. These are drafts for `mcp__github__create_issue`, run by
the orchestrator after human review (D4) — no issue was created while writing this file.

### Draft 1 — Receipt Analysis

- **Title**: `feat(receipt-analysis): implement receipt analysis pipeline`
- **Labels**: `type:feature`, `capability:receipt-analysis`, `area:api`, `mvp1`, `status:needs-triage`
- **Body**:

  ```markdown
  ## Summary

  Delivers the core receipt-analysis pipeline: file validation, hashing, metadata/provenance
  inspection, OCR extraction and deterministic financial-data validation. This is the central
  MVP 1 capability that every other capability composes with.

  ## Specification

  Authoritative requirements and acceptance scenarios:
  [`openspec/specs/receipt-analysis/spec.md`](https://github.com/montesgp/receipt-risk-detector/blob/main/openspec/specs/receipt-analysis/spec.md)

  This issue intentionally does not restate the requirements. Implement against the spec file.

  ## Definition of done

  - [ ] Every requirement in the linked spec has a passing test
  - [ ] Layering respected: no framework imports in `domain/` or `application/`
  - [ ] `docs/` updated if the public contract or architecture changed
  ```

### Draft 2 — Public API Contract

- **Title**: `feat(public-api-contract): implement the public analyze endpoint contract`
- **Labels**: `type:feature`, `capability:public-api-contract`, `area:api`, `mvp1`, `status:needs-triage`
- **Body**:

  ```markdown
  ## Summary

  Delivers the public `POST /v1/receipts/analyze` contract: request/response schemas, error
  shapes and OpenAPI documentation, so the web client, n8n and bot integrations have a stable,
  versioned integration surface.

  ## Specification

  Authoritative requirements and acceptance scenarios:
  [`openspec/specs/public-api-contract/spec.md`](https://github.com/montesgp/receipt-risk-detector/blob/main/openspec/specs/public-api-contract/spec.md)

  This issue intentionally does not restate the requirements. Implement against the spec file.

  ## Definition of done

  - [ ] Every requirement in the linked spec has a passing test
  - [ ] Layering respected: no framework imports in `domain/` or `application/`
  - [ ] `docs/` updated if the public contract or architecture changed
  ```

### Draft 3 — API Rate Limiting

- **Title**: `feat(api-rate-limiting): implement request limits and abuse controls`
- **Labels**: `type:feature`, `capability:api-rate-limiting`, `area:api`, `mvp1`, `status:needs-triage`
- **Body**:

  ```markdown
  ## Summary

  Delivers request-size limits, timeouts and rate limiting for the public API, since MVP 1 ships
  without an access token and must still be safe to expose publicly.

  ## Specification

  Authoritative requirements and acceptance scenarios:
  [`openspec/specs/api-rate-limiting/spec.md`](https://github.com/montesgp/receipt-risk-detector/blob/main/openspec/specs/api-rate-limiting/spec.md)

  This issue intentionally does not restate the requirements. Implement against the spec file.

  ## Definition of done

  - [ ] Every requirement in the linked spec has a passing test
  - [ ] Layering respected: no framework imports in `domain/` or `application/`
  - [ ] `docs/` updated if the public contract or architecture changed
  ```

### Draft 4 — Data Retention

- **Title**: `feat(data-retention): implement ephemeral upload handling and retention guarantees`
- **Labels**: `type:feature`, `capability:data-retention`, `area:api`, `mvp1`, `status:needs-triage`
- **Body**:

  ```markdown
  ## Summary

  Delivers ephemeral handling of uploaded receipts: no persistence, private temporary files only
  when required, and guaranteed cleanup, per MVP 1's no-database, no-durable-storage invariant.

  ## Specification

  Authoritative requirements and acceptance scenarios:
  [`openspec/specs/data-retention/spec.md`](https://github.com/montesgp/receipt-risk-detector/blob/main/openspec/specs/data-retention/spec.md)

  This issue intentionally does not restate the requirements. Implement against the spec file.

  ## Definition of done

  - [ ] Every requirement in the linked spec has a passing test
  - [ ] Layering respected: no framework imports in `domain/` or `application/`
  - [ ] `docs/` updated if the public contract or architecture changed
  ```

### Draft 5 — UI Localization and Theming

- **Title**: `feat(ui-localization-and-theming): implement web localization and theming`
- **Labels**: `type:feature`, `capability:ui-localization-and-theming`, `area:web`, `mvp1`, `status:needs-triage`
- **Body**:

  ```markdown
  ## Summary

  Delivers localization and theming for the SvelteKit web client, so the MVP 1 UI is usable in
  its target locale(s) and presentation is consistent with `docs/DESIGN.md`.

  ## Specification

  Authoritative requirements and acceptance scenarios:
  [`openspec/specs/ui-localization-and-theming/spec.md`](https://github.com/montesgp/receipt-risk-detector/blob/main/openspec/specs/ui-localization-and-theming/spec.md)

  This issue intentionally does not restate the requirements. Implement against the spec file.

  ## Definition of done

  - [ ] Every requirement in the linked spec has a passing test
  - [ ] Layering respected: no framework imports in `domain/` or `application/`
  - [ ] `docs/` updated if the public contract or architecture changed
  ```

### Draft 6 — Architecture Documentation

- **Title**: `docs(architecture-documentation): keep architecture documentation in sync`
- **Labels**: `type:docs`, `capability:architecture-documentation`, `area:docs`, `mvp1`, `status:needs-triage`
- **Body**:

  ```markdown
  ## Summary

  Keeps `docs/ARCHITECTURE.md` and related ADRs in sync as the modular-monolith boundaries and
  dependency rules are implemented, so the documented architecture never drifts from the code.

  ## Specification

  Authoritative requirements and acceptance scenarios:
  [`openspec/specs/architecture-documentation/spec.md`](https://github.com/montesgp/receipt-risk-detector/blob/main/openspec/specs/architecture-documentation/spec.md)

  This issue intentionally does not restate the requirements. Implement against the spec file.

  ## Definition of done

  - [ ] Every requirement in the linked spec has a passing test
  - [ ] Layering respected: no framework imports in `domain/` or `application/`
  - [ ] `docs/` updated if the public contract or architecture changed
  ```
