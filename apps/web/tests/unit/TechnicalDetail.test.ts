/**
 * DESIGN.md §4.4 result priority item 6 "Analyzer and version details".
 * Spec "Full result renders from the live response": analyzer/version
 * detail (`engine_version`, `ruleset_version`) are shown.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import TechnicalDetail from '../../src/lib/components/TechnicalDetail.svelte';

afterEach(() => cleanup());

describe('TechnicalDetail', () => {
  it('shows engine_version, ruleset_version and every analyzer status', () => {
    render(TechnicalDetail, {
      props: {
        engineVersion: '2026.09.01',
        rulesetVersion: 'v2026_09_01',
        analyzerStatuses: [
          { analyzer: 'metadata', status: 'ok', duration_ms: 120 },
          { analyzer: 'ocr', status: 'degraded', duration_ms: 4500 }
        ]
      }
    });

    expect(screen.getByText(/2026\.09\.01/)).toBeTruthy();
    expect(screen.getByText(/v2026_09_01/)).toBeTruthy();
    expect(screen.getByText(/metadata/i)).toBeTruthy();
    expect(screen.getByText(/ocr/i)).toBeTruthy();
    expect(screen.getByText(/degraded/i)).toBeTruthy();
  });

  it('renders without throwing when analyzerStatuses is empty', () => {
    expect(() =>
      render(TechnicalDetail, {
        props: { engineVersion: '1.0.0', rulesetVersion: 'v1', analyzerStatuses: [] }
      })
    ).not.toThrow();
  });
});
