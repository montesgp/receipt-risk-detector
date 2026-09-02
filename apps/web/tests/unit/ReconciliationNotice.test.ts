import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ReconciliationNotice from '../../src/lib/components/ReconciliationNotice.svelte';

afterEach(() => cleanup());

describe('ReconciliationNotice', () => {
  it('renders the DESIGN.md §5 mandatory limitation sentence unconditionally', () => {
    render(ReconciliationNotice);

    expect(
      screen.getByText(/Confirmá la acreditación en la cuenta beneficiaria/i)
    ).toBeTruthy();
  });

  it('never contains forbidden authenticity language', () => {
    render(ReconciliationNotice);

    const text = document.body.textContent ?? '';
    expect(text).not.toMatch(/\breal\b/i);
    expect(text).not.toMatch(/\bfake\b/i);
    expect(text).not.toMatch(/aut[eé]ntic[oa]/i);
    expect(text).not.toMatch(/transferencia verificada/i);
  });
});
