import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ReconciliationNotice from '../../src/lib/components/ReconciliationNotice.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderNotice(locale: 'es' | 'en' = 'es') {
  const i18n = new I18n(locale);
  render(ReconciliationNotice, { context: new Map([[I18N_CONTEXT_KEY, i18n]]) });
  return i18n;
}

describe('ReconciliationNotice', () => {
  it('renders the DESIGN.md §5 mandatory limitation sentence (es)', () => {
    renderNotice('es');

    expect(screen.getByText(es['legal.disclaimer'])).toBeTruthy();
  });

  it('renders the mandatory limitation sentence (en)', () => {
    renderNotice('en');

    expect(screen.getByText(en['legal.disclaimer'])).toBeTruthy();
  });

  it('never contains forbidden authenticity language in either locale', () => {
    renderNotice('es');
    let text = document.body.textContent ?? '';
    expect(text).not.toMatch(/\breal\b/i);
    expect(text).not.toMatch(/\bfake\b/i);
    expect(text).not.toMatch(/aut[eé]ntic[oa]/i);
    expect(text).not.toMatch(/transferencia verificada/i);

    cleanup();

    renderNotice('en');
    text = document.body.textContent ?? '';
    expect(text).not.toMatch(/\breal\b/i);
    expect(text).not.toMatch(/\bfake\b/i);
    expect(text).not.toMatch(/authentic/i);
    expect(text).not.toMatch(/verified transfer/i);
  });
});
