/**
 * DESIGN.md §7 "Evidence list": order by severity then score impact. Each
 * item shows severity, plain-language title, what was observed, why it
 * matters, confidence, and score contribution.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import EvidenceList from '../../src/lib/components/EvidenceList.svelte';
import type { SignalModel } from '../../src/lib/api/types';

afterEach(() => cleanup());

function signal(overrides: Partial<SignalModel>): SignalModel {
  return {
    code: 'SOME_CODE',
    category: 'metadata',
    severity: 'low',
    confidence: 0.5,
    description: 'Descripción de la señal.',
    evidence: {},
    score_contribution: 5,
    ...overrides
  };
}

describe('EvidenceList', () => {
  it('sorts signals by severity (critical first) then score_contribution desc', () => {
    const signals = [
      signal({ code: 'A', severity: 'low', score_contribution: 50 }),
      signal({ code: 'B', severity: 'critical', score_contribution: 10 }),
      signal({ code: 'C', severity: 'high', score_contribution: 30 }),
      signal({ code: 'D', severity: 'high', score_contribution: 40 })
    ];

    render(EvidenceList, { props: { signals } });

    const items = screen.getAllByRole('listitem');
    const codes = items.map((item) => item.getAttribute('data-code'));
    expect(codes).toEqual(['B', 'D', 'C', 'A']);
  });

  it('renders description, confidence, and score contribution for each item', () => {
    render(EvidenceList, {
      props: {
        signals: [
          signal({
            code: 'AI_PROVENANCE',
            severity: 'high',
            confidence: 0.82,
            description: 'Se encontró una señal de procedencia asociada a IA',
            score_contribution: 25
          })
        ]
      }
    });

    expect(screen.getByText(/Se encontró una señal de procedencia asociada a IA/)).toBeTruthy();
    expect(screen.getByText(/82/)).toBeTruthy();
    expect(screen.getByText(/25/)).toBeTruthy();
  });

  it('renders nothing misleading when there are no signals', () => {
    render(EvidenceList, { props: { signals: [] } });
    expect(screen.queryAllByRole('listitem').length).toBe(0);
  });
});
