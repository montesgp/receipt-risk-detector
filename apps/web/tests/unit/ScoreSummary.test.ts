/**
 * DESIGN.md §7 "Score summary": classification as text first, risk shown as
 * `74 / 100` (never a percentage framing), confidence shown separately, and
 * — critically — no forced risk-tier color for `INCONCLUSIVE` (spec
 * "INCONCLUSIVE result does not force a risk color").
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ScoreSummary from '../../src/lib/components/ScoreSummary.svelte';

afterEach(() => cleanup());

describe('ScoreSummary', () => {
  it('shows classification text first and risk as "N / 100", not a percentage', () => {
    render(ScoreSummary, {
      props: {
        classification: 'LOW_RISK',
        riskScore: 12,
        confidenceScore: 91,
        recommendedAction: 'STANDARD_MANUAL_RECONCILIATION'
      }
    });

    expect(screen.getByText(/Riesgo bajo/i)).toBeTruthy();
    // The risk score itself must be framed as "N / 100", never a percentage
    // (confidence is separately allowed to use "%").
    const riskEl = screen.getByText('12 / 100');
    expect(riskEl.textContent).not.toMatch(/%/);
  });

  it('shows confidence separately from risk', () => {
    render(ScoreSummary, {
      props: {
        classification: 'SUSPICIOUS',
        riskScore: 74,
        confidenceScore: 63,
        recommendedAction: 'PRIORITY_MANUAL_RECONCILIATION'
      }
    });

    expect(screen.getByText('74 / 100')).toBeTruthy();
    expect(screen.getByText(/63/)).toBeTruthy();
  });

  it('applies a risk-tier color class for a scored classification like HIGH_RISK', () => {
    const { container } = render(ScoreSummary, {
      props: {
        classification: 'HIGH_RISK',
        riskScore: 91,
        confidenceScore: 88,
        recommendedAction: 'DO_NOT_RELY_ON_RECEIPT'
      }
    });

    const summary = container.querySelector('.score-summary');
    expect(summary?.className).toMatch(/score-summary--high/);
  });

  it('does NOT force a risk-tier color when classification is INCONCLUSIVE', () => {
    const { container } = render(ScoreSummary, {
      props: {
        classification: 'INCONCLUSIVE',
        riskScore: 50,
        confidenceScore: 21,
        recommendedAction: 'PRIORITY_MANUAL_RECONCILIATION'
      }
    });

    const summary = container.querySelector('.score-summary');
    expect(summary?.className).not.toMatch(/score-summary--(low|review|high)/);
    // Confidence and missing-evidence context should dominate instead.
    expect(screen.getAllByText(/confianza/i).length).toBeGreaterThan(0);
  });
});
