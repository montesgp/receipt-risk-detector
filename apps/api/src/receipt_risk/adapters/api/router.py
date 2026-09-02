"""`POST /v1/receipts/analyze` — the first public exposure of the analysis
pipeline (design.md: router module absent until slice 4). Reads the `file`
multipart part, calls `AnalyzeReceiptUseCase.execute`, and maps
`IngestionError`/`AnalysisTimeoutError` to the documented `problem+json`
status per `docs/API.md` §5. Domain objects never leak past `mappers.py`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse

from receipt_risk.adapters.api.dependencies import get_use_case
from receipt_risk.adapters.api.errors import (
    problem_details_for_code,
    problem_details_for_ingestion_error,
)
from receipt_risk.adapters.api.mappers import assessment_to_response
from receipt_risk.application.analyze_receipt import AnalysisTimeoutError, AnalyzeReceiptUseCase
from receipt_risk.application.errors import IngestionError, IngestionErrorCode

router = APIRouter()


def _problem_response(problem, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(),
        media_type="application/problem+json",
    )


@router.post("/v1/receipts/analyze")
async def analyze_receipt(
    request: Request,
    file: UploadFile | None = File(default=None),  # noqa: B008 -- FastAPI idiom
    use_case: AnalyzeReceiptUseCase = Depends(get_use_case),  # noqa: B008 -- FastAPI idiom
) -> JSONResponse:
    instance = str(request.url.path)

    if file is None:
        error = IngestionError(IngestionErrorCode.MISSING_FILE, "No file part was provided.")
        problem = problem_details_for_ingestion_error(error, instance=instance)
        return _problem_response(problem, problem.status)

    data = await file.read()
    try:
        assessment = await use_case.execute(data, declared_filename=file.filename)
    except IngestionError as exc:
        problem = problem_details_for_ingestion_error(exc, instance=instance)
        return _problem_response(problem, problem.status)
    except AnalysisTimeoutError:
        problem = problem_details_for_code(
            "ANALYSIS_TIMEOUT",
            status=504,
            detail="The analysis did not complete within the whole-request time budget.",
            instance=instance,
        )
        return _problem_response(problem, 504)

    response = assessment_to_response(assessment)
    return JSONResponse(status_code=200, content=response.model_dump())
