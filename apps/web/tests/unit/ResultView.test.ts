/**
 * ResultView composes all slice 1b components for the full result screen.
 * Spec "Full result renders from the live response": every documented
 * section is shown, and `limitations[]` always renders. Spec "No forbidden
 * authenticity language appears": no "real"/"fake"/"authentic"/"verified
 * transfer" copy anywhere in the rendered output.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ResultView from '../../src/lib/components/ResultView.svelte';
import type { AnalyzeResponse } from '../../src/lib/api/types';

afterEach(() => cleanup());

function buildResponse(overrides: Partial<AnalyzeResponse> = {}): AnalyzeResponse {
  return {
    analysis_id: 'sha256:abc',
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
        description: 'Se encontró una señal de procedencia asociada a IA',
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
      'Este análisis evalúa el comprobante presentado. Confirmá la acreditación en la cuenta beneficiaria antes de entregar productos o servicios.'
    ],
    duration_ms: 850,
    ...overrides
  };
}

describe('ResultView', () => {
  it('renders classification/risk, evidence, extracted data, checklist and technical detail from a live response', () => {
    render(ResultView, { props: { result: buildResponse() } });

    expect(screen.getByText(/Sospechoso/i)).toBeTruthy();
    expect(screen.getByText('74 / 100')).toBeTruthy();
    expect(screen.getByText(/Se encontró una señal de procedencia asociada a IA/)).toBeTruthy();
    expect(screen.getByText('******************5678')).toBeTruthy();
    expect(screen.getByText(/2026\.09\.01/)).toBeTruthy();
  });

  it('always renders the limitations disclaimer from the response', () => {
    render(ResultView, {
      props: { result: buildResponse({ limitations: ['Aviso de límite personalizado del servidor.'] }) }
    });

    expect(screen.getByText(/Aviso de límite personalizado del servidor\./)).toBeTruthy();
  });

  it('renders a fallback limitation sentence if limitations[] is empty', () => {
    render(ResultView, { props: { result: buildResponse({ limitations: [] }) } });

    expect(screen.getByText(/Confirmá la acreditación/i)).toBeTruthy();
  });

  it('contains no forbidden authenticity language, regardless of classification', () => {
    for (const classification of ['LOW_RISK', 'REVIEW_RECOMMENDED', 'SUSPICIOUS', 'HIGH_RISK', 'INCONCLUSIVE']) {
      const { unmount, container } = render(ResultView, {
        props: { result: buildResponse({ classification }) }
      });

      const text = container.textContent ?? '';
      expect(text).not.toMatch(/\breal\b/i);
      expect(text).not.toMatch(/\bfake\b/i);
      expect(text).not.toMatch(/aut[eé]ntic/i);
      expect(text).not.toMatch(/transferencia verificada|verified transfer/i);

      unmount();
    }
  });
});
