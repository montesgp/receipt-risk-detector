import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ProcessingStages from '../../src/lib/components/ProcessingStages.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderStages(locale: 'es' | 'en' = 'es') {
  const i18n = new I18n(locale);
  render(ProcessingStages, { context: new Map([[I18N_CONTEXT_KEY, i18n]]) });
  return i18n;
}

describe('ProcessingStages', () => {
  it('exposes an ARIA live region announcing the processing state', () => {
    renderStages();

    const region = screen.getByRole('status');
    expect(region.getAttribute('aria-live')).toBe('polite');
  });

  it('never renders a fabricated percentage', () => {
    renderStages();

    expect(screen.queryByText(/%/)).toBeNull();
  });

  it('shows coarse honest stage copy in es', () => {
    renderStages();

    expect(screen.getByText(es['processing.label'])).toBeTruthy();
  });

  it('shows coarse honest stage copy in en', () => {
    renderStages('en');

    expect(screen.getByText(en['processing.label'])).toBeTruthy();
  });
});
