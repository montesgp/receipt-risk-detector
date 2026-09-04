/**
 * Shared mocked `AnalyzeResponse` fixture for the Playwright e2e suite.
 * design.md "Playwright slice 4 sketch": route-intercept
 * `**\/v1/receipts/analyze`, assert the result heading, `74 / 100`, at least
 * one evidence item, a masked CBU matching `/^\*+\d{4}$/`, and the
 * limitation sentence.
 */
export const MOCK_ANALYZE_RESPONSE = {
  analysis_id: 'sha256:e2e-fixture',
  engine_version: '2026.09.01',
  ruleset_version: 'v2026_09_01',
  classification: 'SUSPICIOUS',
  risk_score: 74,
  confidence_score: 81,
  recommended_action: 'PRIORITY_MANUAL_RECONCILIATION',
  signals: [
    {
      code: 'AI_PROVENANCE',
      category: 'provenance',
      severity: 'high',
      confidence: 0.82,
      description: 'A signal consistent with AI-generated content was found.',
      evidence: {},
      score_contribution: 25
    }
  ],
  extracted_data: {
    amount: { value: '125000.00', confidence: 0.97 },
    destination_cbu: { masked_value: '******************5678', confidence: 0.94 },
    cuit: { masked_value: '*******4321', confidence: 0.9 },
    date_time: { value: '2026-09-01T14:43:00-03:00', confidence: 0.88 }
  },
  analyzer_statuses: [{ analyzer: 'metadata', status: 'ok', duration_ms: 120 }],
  limitations: [
    'This is the raw server limitation text and must never be shown verbatim by the client.'
  ],
  duration_ms: 850
};

export function problemDetails(status: number, code: string) {
  return {
    type: `https://project.example/problems/${code.toLowerCase()}`,
    title: code,
    status,
    detail: `${code} happened`,
    instance: '/v1/receipts/analyze',
    request_id: 'req_e2e_01',
    code
  };
}
