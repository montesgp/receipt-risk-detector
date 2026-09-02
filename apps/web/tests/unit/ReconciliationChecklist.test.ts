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

afterEach(() => cleanup());

describe('ReconciliationChecklist', () => {
  it('renders a checklist item for the amount when present', () => {
    const data: Record<string, ExtractedFieldModel> = {
      amount: { value: '125000.00', confidence: 0.97 }
    };

    render(ReconciliationChecklist, { props: { data } });

    expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0);
    expect(screen.getByText(/monto/i)).toBeTruthy();
  });

  it('still renders the full checklist even when every field is absent', () => {
    expect(() => render(ReconciliationChecklist, { props: { data: {} } })).not.toThrow();
    expect(screen.getAllByRole('listitem').length).toBeGreaterThan(0);
  });

  it('never implies that viewing the screenshot alone is reconciliation', () => {
    render(ReconciliationChecklist, { props: { data: {} } });
    const text = document.body.textContent ?? '';
    expect(text).not.toMatch(/ya conciliad|reconciliado autom/i);
  });
});
