/**
 * Mirrors `apps/api/src/receipt_risk/adapters/api/schemas.py` field-for-field.
 * This is the real wire contract — NOT `docs/API.md`'s illustrative example,
 * which historically drifted (see the docs/API.md correction in this same slice).
 */

export interface SignalModel {
  code: string;
  category: string;
  severity: string;
  confidence: number;
  description: string;
  evidence: Record<string, string>;
  score_contribution: number;
}

export interface AnalyzerStatusModel {
  analyzer: string;
  status: string;
  duration_ms: number;
}

export interface ExtractedFieldModel {
  value?: string | null;
  masked_value?: string | null;
  confidence: number;
  /**
   * `mappers.py` never populates this field today — always treat it as
   * optional/absent, never assume it accompanies masked identifiers.
   */
  is_checksum_valid?: boolean | null;
}

export interface AnalyzeResponse {
  analysis_id: string;
  engine_version: string;
  ruleset_version: string;
  classification: string;
  risk_score: number;
  /** 0-100 integer, same scale as `risk_score` — NOT a 0-1 float (`schemas.py` types both as `int`). */
  confidence_score: number;
  recommended_action: string;
  signals: SignalModel[];
  extracted_data: Record<string, ExtractedFieldModel>;
  analyzer_statuses: AnalyzerStatusModel[];
  limitations: string[];
  duration_ms: number;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  request_id: string;
  code: string;
}
