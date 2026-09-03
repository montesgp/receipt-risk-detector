/**
 * DESIGN.md §7 "Reconciliation checklist": present amount, approximate
 * date, originator, beneficiary and operation ID as a checklist for
 * comparing against the beneficiary account. Must render items even when a
 * field is absent — the checklist is guidance, not a data-completeness
 * report.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ReconciliationChecklist from '../../src/lib/components/ReconciliationChecklist.svelte';
import type { ExtractedFieldModel } from '../../src/lib/api/types';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderChecklist(data: Record<string, ExtractedFieldModel>, locale: 'es' | 'en' = 'es') {
  return render(ReconciliationChecklist, {
    props: { data },
    context: new Map([[I18N_CONTEXT_KEY, new I18n(locale)]])
  });
}

describe('ReconciliationChecklist', () => {
  it('renders a checklist item for the amount when present', () => {
    const data: Record<string, ExtractedFieldModel> = {
      amount: { value: '125000.00', confidence: 0.97 }
    };

    renderChecklist(data);

    expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0);
    expect(screen.getByText(es['result.checklist.amount'])).toBeTruthy();
    expect(screen.getByText(es['result.checklist.present'])).toBeTruthy();
  });

  it('renders checklist labels in English when locale is en', () => {
    renderChecklist({}, 'en');

    expect(screen.getByText(en['result.checklist.amount'])).toBeTruthy();
    expect(screen.getAllByText(en['result.checklist.missing']).length).toBeGreaterThan(0);
  });

  it('still renders the full checklist even when every field is absent', () => {
    expect(() => renderChecklist({})).not.toThrow();
    expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0);
    expect(screen.getAllByText(es['result.checklist.missing']).length).toBeGreaterThan(0);
  });

  it('never implies that viewing the screenshot alone is reconciliation', () => {
    renderChecklist({});
    const text = document.body.textContent ?? '';
    expect(text).not.toMatch(/ya conciliad|reconciliado autom/i);
  });
});
