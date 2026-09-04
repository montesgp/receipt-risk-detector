/**
 * DESIGN.md §7 "Score summary": classification as text first, risk shown as
 * `74 / 100` (never a percentage framing), confidence shown separately, and
 * — critically — no forced risk-tier color for `INCONCLUSIVE` (spec
 * "INCONCLUSIVE result does not force a risk color").
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ScoreSummary from '../../src/lib/components/ScoreSummary.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderSummary(
  props: {
    classification: string;
    riskScore: number;
    confidenceScore: number;
    recommendedAction: string;
  },
  locale: 'es' | 'en' = 'es'
) {
  return render(ScoreSummary, {
    props,
    context: new Map([[I18N_CONTEXT_KEY, new I18n(locale)]])
  });
}

describe('ScoreSummary', () => {
  it('shows classification text first and risk as "N / 100", not a percentage', () => {
    renderSummary({
      classification: 'LOW_RISK',
      riskScore: 12,
      confidenceScore: 91,
      recommendedAction: 'STANDARD_MANUAL_RECONCILIATION'
    });

    expect(screen.getByText(es['result.classification.LOW_RISK'])).toBeTruthy();
    // The risk score itself must be framed as "N / 100", never a percentage
    // (confidence is separately allowed to use "%").
    const riskEl = screen.getByText('12 / 100');
    expect(riskEl.textContent).not.toMatch(/%/);
  });

  it('shows classification text first in English when locale is en', () => {
    renderSummary(
      {
        classification: 'LOW_RISK',
        riskScore: 12,
        confidenceScore: 91,
        recommendedAction: 'STANDARD_MANUAL_RECONCILIATION'
      },
      'en'
    );

    expect(screen.getByText(en['result.classification.LOW_RISK'])).toBeTruthy();
    expect(screen.getByText('12 / 100')).toBeTruthy();
  });

  it('shows confidence separately from risk', () => {
    renderSummary({
      classification: 'SUSPICIOUS',
      riskScore: 74,
      confidenceScore: 63,
      recommendedAction: 'PRIORITY_MANUAL_RECONCILIATION'
    });

    expect(screen.getByText('74 / 100')).toBeTruthy();
    expect(screen.getByText(/63/)).toBeTruthy();
  });

  it('applies a risk-tier color class for a scored classification like HIGH_RISK', () => {
    const { container } = renderSummary({
      classification: 'HIGH_RISK',
      riskScore: 91,
      confidenceScore: 88,
      recommendedAction: 'DO_NOT_RELY_ON_RECEIPT'
    });

    const summary = container.querySelector('.score-summary');
    expect(summary?.className).toMatch(/score-summary--high/);
  });

  it('does NOT force a risk-tier color when classification is INCONCLUSIVE', () => {
    const { container } = renderSummary({
      classification: 'INCONCLUSIVE',
      riskScore: 50,
      confidenceScore: 21,
      recommendedAction: 'PRIORITY_MANUAL_RECONCILIATION'
    });

    const summary = container.querySelector('.score-summary');
    expect(summary?.className).not.toMatch(/score-summary--(low|review|high)/);
    // Confidence and missing-evidence context should dominate instead.
    expect(screen.getAllByText(/confianza/i).length).toBeGreaterThan(0);
  });

  it('does NOT force a risk-tier color when classification is INCONCLUSIVE (en)', () => {
    const { container } = renderSummary(
      {
        classification: 'INCONCLUSIVE',
        riskScore: 50,
        confidenceScore: 21,
        recommendedAction: 'PRIORITY_MANUAL_RECONCILIATION'
      },
      'en'
    );

    const summary = container.querySelector('.score-summary');
    expect(summary?.className).not.toMatch(/score-summary--(low|review|high)/);
    expect(screen.getAllByText(/confidence/i).length).toBeGreaterThan(0);
  });
});
