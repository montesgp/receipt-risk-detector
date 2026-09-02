"""Pydantic request/response models mirroring `docs/API.md` §3/§5
field-for-field, in `snake_case`. Domain objects never carry Pydantic
types — `mappers.py` is the sole one-directional translation point.
"""

from __future__ import annotations

from pydantic import BaseModel


class SignalModel(BaseModel):
    code: str
    category: str
    severity: str
    confidence: float
    description: str
    evidence: dict[str, str] = {}
    score_contribution: int


class AnalyzerStatusModel(BaseModel):
    analyzer: str
    status: str
    duration_ms: int


class ExtractedFieldModel(BaseModel):
    value: str | None = None
    masked_value: str | None = None
    confidence: float
    is_checksum_valid: bool | None = None


class AnalyzeResponse(BaseModel):
    analysis_id: str
    engine_version: str
    ruleset_version: str
    classification: str
    risk_score: int
    confidence_score: int
    recommended_action: str
    signals: list[SignalModel]
    extracted_data: dict[str, ExtractedFieldModel]
    analyzer_statuses: list[AnalyzerStatusModel]
    limitations: list[str]
    duration_ms: int


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str
    code: str


class VersionResponse(BaseModel):
    engine_version: str
    ruleset_version: str
    analyzers: dict[str, str]


class ReadyResponse(BaseModel):
    status: str
    analyzers: dict[str, str]
