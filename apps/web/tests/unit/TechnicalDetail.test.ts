/**
 * DESIGN.md §4.4 result priority item 6 "Analyzer and version details".
 * Spec "Full result renders from the live response": analyzer/version
 * detail (`engine_version`, `ruleset_version`) are shown.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import TechnicalDetail from '../../src/lib/components/TechnicalDetail.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderDetail(
  props: {
    engineVersion: string;
    rulesetVersion: string;
    analyzerStatuses: { analyzer: string; status: string; duration_ms: number }[];
  },
  locale: 'es' | 'en' = 'es'
) {
  return render(TechnicalDetail, {
    props,
    context: new Map([[I18N_CONTEXT_KEY, new I18n(locale)]])
  });
}

describe('TechnicalDetail', () => {
  it('shows engine_version, ruleset_version and every analyzer status', () => {
    renderDetail({
      engineVersion: '2026.09.01',
      rulesetVersion: 'v2026_09_01',
      analyzerStatuses: [
        { analyzer: 'metadata', status: 'ok', duration_ms: 120 },
        { analyzer: 'ocr', status: 'degraded', duration_ms: 4500 }
      ]
    });

    expect(screen.getByText(/2026\.09\.01/)).toBeTruthy();
    expect(screen.getByText(/v2026_09_01/)).toBeTruthy();
    expect(screen.getByText(/metadata/i)).toBeTruthy();
    expect(screen.getByText(/ocr/i)).toBeTruthy();
    expect(screen.getByText(/degraded/i)).toBeTruthy();
    expect(screen.getByText(es['result.technical.summary'])).toBeTruthy();
  });

  it('shows the technical detail summary label in English when locale is en', () => {
    renderDetail(
      {
        engineVersion: '2026.09.01',
        rulesetVersion: 'v2026_09_01',
        analyzerStatuses: []
      },
      'en'
    );

    expect(screen.getByText(en['result.technical.summary'])).toBeTruthy();
    expect(screen.getByText(en['result.technical.engineVersion'])).toBeTruthy();
  });

  it('renders without throwing when analyzerStatuses is empty', () => {
    expect(() =>
      renderDetail({ engineVersion: '1.0.0', rulesetVersion: 'v1', analyzerStatuses: [] })
    ).not.toThrow();
  });

  it('shows a help tooltip for a known analyzer, describing what it checks (issue #34)', () => {
    renderDetail({
      engineVersion: '1.0.0',
      rulesetVersion: 'v1',
      analyzerStatuses: [{ analyzer: 'c2pa', status: 'completed', duration_ms: 5 }]
    });

    expect(screen.getByText(es['result.technical.help.c2pa'])).toBeTruthy();
  });

  it('shows no help tooltip for an unknown/future analyzer name', () => {
    renderDetail({
      engineVersion: '1.0.0',
      rulesetVersion: 'v1',
      analyzerStatuses: [{ analyzer: 'some-future-analyzer', status: 'completed', duration_ms: 5 }]
    });

    expect(screen.queryByRole('tooltip')).toBeNull();
  });
});
