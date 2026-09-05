"""ASGI application entrypoint.

Wires adapters into a FastAPI app. This module is the only place allowed to
import both the framework and the application/domain layers directly (see
AGENTS.md's architecture rules and the `bootstrap/` layering exception in
pyproject.toml).

`POST /v1/receipts/analyze` is registered here for the first time (slice 4
of `receipt-analysis-implementation`) — design.md's "router module absent
until slice 4" decision means slices 1-3 never touched this file.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from receipt_risk.adapters.api.cors_config import allowed_origins
from receipt_risk.adapters.api.dependencies import get_use_case
from receipt_risk.adapters.api.middleware.rate_limit import RateLimitMiddleware
from receipt_risk.adapters.api.router import router
from receipt_risk.adapters.api.schemas import ReadyResponse, VersionResponse
from receipt_risk.adapters.image.pillow_decoder import PillowImageDecoder
from receipt_risk.adapters.metadata.exiftool import ExifToolMetadataAdapter
from receipt_risk.adapters.ocr.paddle_onnx import PaddleOnnxOcrAdapter
from receipt_risk.adapters.provenance.c2pa_reader import C2paProvenanceAdapter
from receipt_risk.adapters.vision.mobilenet_embedder import MobileNetV3VisionAdapter
from receipt_risk.application.analyze_receipt import ENGINE_VERSION, AnalyzeReceiptUseCase
from receipt_risk.application.ingestion import IngestionService
from receipt_risk.domain.rulesets.v2026_09_05 import RULESET_2026_09_05

# Local-dev convenience only: loads apps/api/.env (never committed -- see
# .gitignore) into os.environ before any adapter below reads
# RECEIPT_RISK_*. Never overrides an already-set env var, so this is a
# silent no-op in Docker/Railway/CI, where real env vars are exported by
# the platform. `uv run uvicorn receipt_risk.bootstrap.app:app --reload`
# then just works without exporting anything by hand.
load_dotenv()

# Local-dev convenience only: loads apps/api/.env (never committed -- see
# .gitignore) into os.environ before any adapter below reads
# RECEIPT_RISK_*. Never overrides an already-set env var, so this is a
# silent no-op in Docker/Railway/CI, where real env vars are exported by
# the platform. `uv run uvicorn receipt_risk.bootstrap.app:app --reload`
# then just works without exporting anything by hand.
load_dotenv()

app = FastAPI(title="Transfer Receipt Risk Engine")
app.include_router(router)
# Registration order matters: Starlette applies middleware in REVERSE
# registration order, so the one added LAST becomes OUTERMOST. Rate limiter
# first, CORS last -> CORS wraps the rate limiter, so an allowlisted origin
# gets Access-Control-Allow-Origin even on a 429 (docs/API.md §5's
# documented contract: "the rate limiter runs inside the CORS middleware,
# not in front of it"). Server-side clients (n8n, bots) are unaffected by
# CORS either way -- it is a browser-only enforcement mechanism. An empty
# allowlist (the default; see cors_config.py) means no browser origin can
# read the response until RECEIPT_RISK_CORS_ALLOWED_ORIGINS is configured.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_temp_dir = Path(tempfile.gettempdir()) / "receipt-risk-uploads"
_ocr = PaddleOnnxOcrAdapter()
_metadata = ExifToolMetadataAdapter()
_provenance = C2paProvenanceAdapter()
_vision = MobileNetV3VisionAdapter()
_ingestion = IngestionService(temp_dir=_temp_dir, decoder=PillowImageDecoder())

_use_case = AnalyzeReceiptUseCase(
    ocr=_ocr,
    metadata=_metadata,
    provenance=_provenance,
    vision=_vision,
    ingestion=_ingestion,
    ruleset=RULESET_2026_09_05,
)

app.dependency_overrides[get_use_case] = lambda: _use_case


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by Railway's healthcheck (see railway.json).
    Never runs OCR or expensive dependency checks (docs/API.md §2)."""
    return {"status": "ok"}


@app.get("/ready", response_model=ReadyResponse)
def ready() -> ReadyResponse:
    """Reports whether required analyzers are initialized and the service
    can accept work (docs/API.md §2)."""
    return ReadyResponse(
        status="ok",
        analyzers={
            "ocr": f"{_ocr.name}/{_ocr.version}",
            "metadata": f"{_metadata.name}/{_metadata.version}",
            "provenance": f"{_provenance.name}/{_provenance.version}",
            "vision": f"{_vision.name}/{_vision.version}",
        },
    )


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    """Per docs/API.md §2 example."""
    return VersionResponse(
        engine_version=ENGINE_VERSION,
        ruleset_version=RULESET_2026_09_05.version,
        analyzers={
            "ocr": f"{_ocr.name}/{_ocr.version}",
            "metadata": f"{_metadata.name}/{_metadata.version}",
            "provenance": f"{_provenance.name}/{_provenance.version}",
            "vision": f"{_vision.name}/{_vision.version}",
        },
    )
