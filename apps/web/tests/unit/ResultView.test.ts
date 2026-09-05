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
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderResult(result: AnalyzeResponse, locale: 'es' | 'en' = 'es') {
  return render(ResultView, {
    props: { result },
    context: new Map([[I18N_CONTEXT_KEY, new I18n(locale)]])
  });
}

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
    renderResult(buildResponse());

    expect(screen.getByText(es['result.classification.SUSPICIOUS'])).toBeTruthy();
    expect(screen.getByText('74 / 100')).toBeTruthy();
    expect(screen.getByText(/Se encontró una señal de procedencia asociada a IA/)).toBeTruthy();
    expect(screen.getByText('******************5678')).toBeTruthy();
    expect(screen.getByText(/2026\.09\.01/)).toBeTruthy();
    expect(screen.getByText(es['result.heading'])).toBeTruthy();
  });

  it('renders the full result screen in English when locale is en', () => {
    renderResult(buildResponse(), 'en');

    expect(screen.getByText(en['result.classification.SUSPICIOUS'])).toBeTruthy();
    expect(screen.getByText(en['result.heading'])).toBeTruthy();
    expect(screen.getByText(en['result.evidenceHeading'])).toBeTruthy();
    expect(screen.getByText(en['result.checklistHeading'])).toBeTruthy();
    expect(screen.getByText(en['result.extractedHeading'])).toBeTruthy();
    expect(screen.getByText(en['legal.disclaimer'])).toBeTruthy();
  });

  it('always renders the client-owned limitation disclaimer, ignoring the raw server limitations[]', () => {
    // Locale fix (slice 3a): `apps/api`'s LIMITATION_STATEMENT is a hardcoded
    // English constant, so the client must never echo `limitations[]`
    // verbatim — only its own (t()-ified in slice 3b) disclaimer copy,
    // regardless of what the server sends.
    renderResult(buildResponse({ limitations: ['This is the raw English server limitation text.'] }));

    expect(screen.getByText(es['legal.disclaimer'])).toBeTruthy();
    expect(screen.queryByText(/This is the raw English server limitation text\./)).toBeNull();
  });

  it('still renders the disclaimer when limitations[] is empty', () => {
    renderResult(buildResponse({ limitations: [] }));

    expect(screen.getByText(es['legal.disclaimer'])).toBeTruthy();
  });

  it('moves focus to the result heading when it renders (focus management, slice 4)', async () => {
    // Batch instructions: "after an action completes (upload -> result...),
    // focus should move sensibly ... rather than staying on a now-irrelevant
    // element". `+page.svelte` mounts a fresh `ResultView` per successful
    // analysis, so mount-time focus is the correct hook.
    renderResult(buildResponse());
    await Promise.resolve();

    const heading = screen.getByRole('heading', { name: es['result.heading'] });
    expect(document.activeElement).toBe(heading);
  });

  it('contains no forbidden authenticity language, regardless of classification', () => {
    for (const classification of ['LOW_RISK', 'REVIEW_RECOMMENDED', 'SUSPICIOUS', 'HIGH_RISK', 'INCONCLUSIVE']) {
      const { unmount, container } = renderResult(buildResponse({ classification }));

      const text = container.textContent ?? '';
      expect(text).not.toMatch(/\breal\b/i);
      expect(text).not.toMatch(/\bfake\b/i);
      expect(text).not.toMatch(/aut[eé]ntic/i);
      expect(text).not.toMatch(/transferencia verificada|verified transfer/i);

      unmount();
    }
  });

  it('derives noTextDetected and shows the hedged copy when CORE_FIELD_EXTRACTION_FAILED/no_text_detected is signaled', () => {
    renderResult(
      buildResponse({
        classification: 'INCONCLUSIVE',
        risk_score: 0,
        confidence_score: 32,
        recommended_action: 'PRIORITY_MANUAL_RECONCILIATION',
        signals: [
          {
            code: 'CORE_FIELD_EXTRACTION_FAILED',
            category: 'data_quality',
            severity: 'medium',
            confidence: 1,
            description: 'OCR extraction did not complete for this request.',
            evidence: { reason: 'no_text_detected' },
            score_contribution: 0
          }
        ]
      })
    );

    expect(
      screen.getByText(es['result.inconclusiveNoTextNote'].replace('{confidence}', '32'))
    ).toBeTruthy();
  });

  it('does not show the hedged no-text copy when the signal reason is different', () => {
    renderResult(
      buildResponse({
        classification: 'INCONCLUSIVE',
        risk_score: 0,
        confidence_score: 32,
        recommended_action: 'PRIORITY_MANUAL_RECONCILIATION',
        signals: [
          {
            code: 'CORE_FIELD_EXTRACTION_FAILED',
            category: 'data_quality',
            severity: 'medium',
            confidence: 1,
            description: 'OCR extraction did not complete for this request.',
            evidence: { reason: 'low_confidence' },
            score_contribution: 0
          }
        ]
      })
    );

    expect(
      screen.queryByText(es['result.inconclusiveNoTextNote'].replace('{confidence}', '32'))
    ).toBeNull();
    expect(
      screen.getByText(es['result.inconclusiveNote'].replace('{confidence}', '32'))
    ).toBeTruthy();
  });
});
