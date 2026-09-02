"""Application-layer error vocabulary.

`IngestionError.code` maps 1:1 to the documented `docs/API.md` error codes
that guard ingestion (§3, "Expected errors"). Adapters translate this into
an HTTP `problem+json` response; this module has zero framework imports.
"""

from __future__ import annotations

from enum import StrEnum


class IngestionErrorCode(StrEnum):
    MISSING_FILE = "MISSING_FILE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    IMAGE_DIMENSIONS_EXCEEDED = "IMAGE_DIMENSIONS_EXCEEDED"


_STATUS_BY_CODE: dict[IngestionErrorCode, int] = {
    IngestionErrorCode.MISSING_FILE: 400,
    IngestionErrorCode.FILE_TOO_LARGE: 413,
    IngestionErrorCode.UNSUPPORTED_IMAGE: 415,
    IngestionErrorCode.IMAGE_DIMENSIONS_EXCEEDED: 422,
}


class IngestionError(Exception):
    """Raised by `IngestionService.ingest` for any documented rejection.

    This is a HARD gate failure: no analyzer runs once this is raised
    (design.md "a failed analyzer produces a signal, never an aborted
    request" — that rule applies only after ingestion succeeds).
    """

    def __init__(self, code: IngestionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = _STATUS_BY_CODE[code]
