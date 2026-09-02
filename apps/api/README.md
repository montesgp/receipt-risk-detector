# receipt-risk-api

FastAPI service for the Transfer Receipt Risk Engine. See the repository
[README](../../README.md) and [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) for product
scope and boundaries.

## Layout

```text
src/receipt_risk/
├── domain/        # Pure business rules. No framework imports.
├── application/   # Use cases / orchestration. No framework imports.
├── adapters/      # Framework- and tool-specific implementations.
│   ├── api/         # FastAPI routers and schemas.
│   ├── metadata/     # EXIF / creator-software inspection.
│   ├── provenance/   # C2PA / Content Credentials inspection.
│   └── ocr/          # OCR engine adapters.
└── bootstrap/     # App wiring and startup (FastAPI app instance).
```

`domain/` and `application/` must not import `fastapi`, `starlette`, `cv2`, `paddleocr` or `PIL`.
This is enforced by `ruff`'s `flake8-tidy-imports` banned-api rule in `pyproject.toml`.

## Local development

```bash
uv sync --all-extras --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
