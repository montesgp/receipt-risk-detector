/**
 * Integration-level proof (per slice 3b apply verification checklist) that
 * switching language via `LanguageSwitcher` re-renders the FULL result
 * screen — `ScoreSummary`, `EvidenceList`, and `ExtractedDataTable` together
 * — from the shared held `I18n` state, not just each component in
 * isolation. Mirrors the real `+layout.svelte` (owns `I18n` +
 * `LanguageSwitcher`) / `+page.svelte` (renders `ResultView`) composition
 * via a test-only host component.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import LocaleIntegrationHost from './support/LocaleIntegrationHost.svelte';
import type { AnalyzeResponse } from '../../src/lib/api/types';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function buildResponse(): AnalyzeResponse {
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
      destination_cbu: { masked_value: '******************5678', confidence: 0.94 }
    },
    analyzer_statuses: [{ analyzer: 'metadata', status: 'ok', duration_ms: 120 }],
    limitations: [],
    duration_ms: 850
  };
}

describe('locale switch integration (LanguageSwitcher + full result screen)', () => {
  it('re-renders ScoreSummary, EvidenceList, and ExtractedDataTable together when the language switches', async () => {
    render(LocaleIntegrationHost, { props: { result: buildResponse() } });

    // Starts in Spanish across all three composed components.
    expect(screen.getByText(es['result.classification.SUSPICIOUS'])).toBeTruthy();
    expect(screen.getByText(es['evidence.severity.high'])).toBeTruthy();
    expect(screen.getByText(es['result.field.amount'])).toBeTruthy();

    const switchToEn = screen.getByRole('button', { name: es['header.language.switchToEn'] });
    await fireEvent.click(switchToEn);

    // A single click flips ALL THREE components at once, from shared state
    // — no per-component re-fetch, no stale Spanish text left behind.
    expect(screen.getByText(en['result.classification.SUSPICIOUS'])).toBeTruthy();
    expect(screen.getByText(en['evidence.severity.high'])).toBeTruthy();
    expect(screen.getByText(en['result.field.amount'])).toBeTruthy();
    expect(screen.queryByText(es['result.classification.SUSPICIOUS'])).toBeNull();
    expect(screen.queryByText(es['evidence.severity.high'])).toBeNull();
    expect(screen.queryByText(es['result.field.amount'])).toBeNull();

    // Switching back to Spanish restores every component again.
    const switchToEs = screen.getByRole('button', { name: en['header.language.switchToEs'] });
    await fireEvent.click(switchToEs);

    expect(screen.getByText(es['result.classification.SUSPICIOUS'])).toBeTruthy();
    expect(screen.getByText(es['evidence.severity.high'])).toBeTruthy();
    expect(screen.getByText(es['result.field.amount'])).toBeTruthy();
  });
});
