/**
 * DESIGN.md §7 "Evidence list": order by severity then score impact. Each
 * item shows severity, plain-language title, what was observed, why it
 * matters, confidence, and score contribution.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import EvidenceList from '../../src/lib/components/EvidenceList.svelte';
import type { SignalModel } from '../../src/lib/api/types';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

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

function renderList(signals: SignalModel[], locale: 'es' | 'en' = 'es') {
  return render(EvidenceList, {
    props: { signals },
    context: new Map([[I18N_CONTEXT_KEY, new I18n(locale)]])
  });
}

describe('EvidenceList', () => {
  it('sorts signals by severity (critical first) then score_contribution desc', () => {
    const signals = [
      signal({ code: 'A', severity: 'low', score_contribution: 50 }),
      signal({ code: 'B', severity: 'critical', score_contribution: 10 }),
      signal({ code: 'C', severity: 'high', score_contribution: 30 }),
      signal({ code: 'D', severity: 'high', score_contribution: 40 })
    ];

    renderList(signals);

    const items = screen.getAllByRole('listitem');
    const codes = items.map((item) => item.getAttribute('data-code'));
    expect(codes).toEqual(['B', 'D', 'C', 'A']);
  });

  it('renders description, confidence, and score contribution for each item', () => {
    renderList([
      signal({
        code: 'AI_PROVENANCE',
        severity: 'high',
        confidence: 0.82,
        description: 'Se encontró una señal de procedencia asociada a IA',
        score_contribution: 25
      })
    ]);

    expect(screen.getByText(/Se encontró una señal de procedencia asociada a IA/)).toBeTruthy();
    expect(screen.getByText(es['evidence.severity.high'])).toBeTruthy();
    expect(screen.getByText(/82/)).toBeTruthy();
    expect(screen.getByText(/25/)).toBeTruthy();
  });

  it('renders the severity label in English when locale is en', () => {
    renderList(
      [signal({ code: 'AI_PROVENANCE', severity: 'high', confidence: 0.82, score_contribution: 25 })],
      'en'
    );

    expect(screen.getByText(en['evidence.severity.high'])).toBeTruthy();
  });

  it('renders nothing misleading when there are no signals', () => {
    renderList([]);
    expect(screen.queryAllByRole('listitem').length).toBe(0);
    expect(screen.getByText(es['evidence.empty'])).toBeTruthy();
  });

  it('renders a VISUAL_ANOMALY_DETECTED finding as an outlier, never as an AI-generated claim', () => {
    renderList([
      signal({
        code: 'VISUAL_ANOMALY_DETECTED',
        category: 'visual',
        severity: 'medium',
        confidence: 0.7,
        description:
          "This receipt's visual appearance is an outlier relative to the bundled set of known-legitimate receipt renders.",
        evidence: { cosine_distance: '0.52', threshold: '0.45' },
        score_contribution: 14
      })
    ]);

    const text = document.body.textContent ?? '';
    expect(text).toMatch(/outlier/i);
    expect(text).not.toMatch(/AI-generated/i);
    expect(text).not.toMatch(/\bfake\b/i);
  });
});
