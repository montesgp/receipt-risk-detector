"""`IngestionError` / `AnalysisTimeoutError` -> documented `problem+json`
mapping (`docs/API.md` §5). One-directional: domain/application exceptions
in, `ProblemDetails` transport model out. Never the reverse.
"""

from __future__ import annotations

from receipt_risk.adapters.api.schemas import ProblemDetails
from receipt_risk.application.errors import IngestionError

_TITLES: dict[str, str] = {
    "MISSING_FILE": "Missing file",
    "FILE_TOO_LARGE": "File too large",
    "UNSUPPORTED_IMAGE": "Unsupported image",
    "IMAGE_DIMENSIONS_EXCEEDED": "Image dimensions exceeded",
    "RATE_LIMITED": "Too many requests",
    "ANALYZER_UNAVAILABLE": "Analyzer unavailable",
    "ANALYSIS_TIMEOUT": "Analysis timeout",
}


def _problem_type(code: str) -> str:
    return f"https://project.example/problems/{code.lower().replace('_', '-')}"


def problem_details_for_ingestion_error(
    error: IngestionError, *, instance: str, request_id: str = "req_00000000"
) -> ProblemDetails:
    return ProblemDetails(
        type=_problem_type(error.code.value),
        title=_TITLES[error.code.value],
        status=error.status_code,
        detail=error.message,
        instance=instance,
        request_id=request_id,
        code=error.code.value,
    )


def problem_details_for_code(
    code: str, *, status: int, detail: str, instance: str, request_id: str = "req_00000000"
) -> ProblemDetails:
    return ProblemDetails(
        type=_problem_type(code),
        title=_TITLES.get(code, code.replace("_", " ").capitalize()),
        status=status,
        detail=detail,
        instance=instance,
        request_id=request_id,
        code=code,
    )
