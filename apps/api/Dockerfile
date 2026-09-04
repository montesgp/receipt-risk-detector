# syntax=docker/dockerfile:1
#
# Production image for the receipt-risk-detector API. No business logic exists
# yet beyond the /health bootstrap and the receipt-analysis pipeline's adapters
# (tracked as GitHub issue #1). Build context is the REPO ROOT, not apps/api:
# Railway's top-level `build` object has no `dockerContext` property (confirmed
# against railway.schema.json — it only exists per-service inside a
# multi-service `services[]` array, which this single-service repo does not
# use), so it always builds from root regardless of `dockerfilePath`. Paths
# below are relative to the repo root accordingly.

# ---- slice 3: OCR model pre-baking (no network access at container start) ----
FROM python:3.12-slim AS ocr-models
RUN pip install --no-cache-dir uv
WORKDIR /build
COPY apps/api/scripts/fetch_ocr_models.py ./
# Pinned model set + sha256 verification live inside the script so the pin is reviewable.
RUN pip install --no-cache-dir "requests==2.32.3" \
 && python fetch_ocr_models.py --dest /opt/ocr-models --verify

# ---- vision model pre-baking (independent cache key from OCR's stage,
# so an OCR pin bump does not invalidate the vision cache and vice versa;
# design.md "Weight distribution") ----
FROM python:3.12-slim AS vision-model
RUN pip install --no-cache-dir uv
WORKDIR /build
COPY apps/api/scripts/fetch_vision_model.py ./
RUN pip install --no-cache-dir "requests==2.32.3" \
 && python fetch_vision_model.py --dest /opt/vision-model --verify

# ---- runtime ----
FROM python:3.12-slim

# slice 2: ExifTool binary. libglib2.0-0 is required by opencv-python-headless
# (slice 3); libgl1 is deliberately NOT installed because the headless wheel
# does not link libGL.
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      libimage-exiftool-perl \
      libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

# `src/` must be present before `uv sync`: hatchling's editable-install build
# enumerates the package's files at build time, so syncing against an empty/missing
# `src/` silently produces a dist-info with no importable module (confirmed by a
# local `docker run` smoke test raising `ModuleNotFoundError: No module named
# 'receipt_risk'`). This trades away a dependency-only cache layer for correctness.
COPY apps/api/pyproject.toml apps/api/uv.lock apps/api/README.md ./
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev --extra server

# slice 3: baked models; the OCR adapter must never download at request or
# startup time (see the "zero outbound network connections" threat-matrix test).
COPY --from=ocr-models /opt/ocr-models /opt/ocr-models
# slice: baked vision weights; the vision adapter must never download at
# request or startup time either (mirrors the OCR fail-closed contract).
COPY --from=vision-model /opt/vision-model /opt/vision-model
ENV RECEIPT_RISK_OCR_MODEL_DIR=/opt/ocr-models \
    RECEIPT_RISK_VISION_MODEL_DIR=/opt/vision-model \
    HF_HUB_OFFLINE=1 \
    OMP_NUM_THREADS=2

# Invoke uvicorn directly from the synced venv instead of `uv run` — `uv run` re-
# resolves dependency groups (including `dev`) on every container start, which is
# slow and pulls dev-only tools like ruff into the runtime image unnecessarily.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "receipt_risk.bootstrap.app:app", "--host", "0.0.0.0", "--port", "8000"]
