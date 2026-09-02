# Minimal production image for the receipt-risk-detector API.
#
# Ships only the bootstrap liveness endpoint (see src/receipt_risk/bootstrap/app.py) —
# no business logic exists yet (tracked as GitHub issue #1, receipt-analysis capability).
# This Dockerfile exists so railway.json's DOCKERFILE builder has something real to
# build; it is intentionally not optimized for image size or build cache until the
# real analyzer dependencies (OpenCV, PaddleOCR, ExifTool) land.
#
# Build context is the REPO ROOT, not apps/api. Railway's top-level `build` object
# has no `dockerContext` property (confirmed against railway.schema.json — it only
# exists per-service inside a multi-service `services[]` array, which this single-
# service repo does not use), so it always builds from root regardless of
# `dockerfilePath`. Paths below are relative to the repo root accordingly.

FROM python:3.12-slim

# slice 2: ExifTool binary for the metadata adapter (adapters/metadata/exiftool.py).
RUN apt-get update \
 && apt-get install --no-install-recommends -y libimage-exiftool-perl \
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

# Invoke uvicorn directly from the synced venv instead of `uv run` — `uv run` re-
# resolves dependency groups (including `dev`) on every container start, which is
# slow and pulls dev-only tools like ruff into the runtime image unnecessarily.
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "receipt_risk.bootstrap.app:app", "--host", "0.0.0.0", "--port", "8000"]
