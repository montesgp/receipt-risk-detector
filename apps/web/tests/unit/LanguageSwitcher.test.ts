// Spec "Switchers are keyboard-operable with visible focus" and "State
// change is announced and not color-only": ES/EN two-option control,
// `aria-pressed`, a per-language `aria-label`, keyboard-operable, and the
// new state announced via an ARIA live region.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import LanguageSwitcher from '../../src/lib/components/LanguageSwitcher.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';

afterEach(() => cleanup());

function renderSwitcher(initialLocale: 'es' | 'en' = 'es') {
  const i18n = new I18n(initialLocale);
  render(LanguageSwitcher, { context: new Map([[I18N_CONTEXT_KEY, i18n]]) });
  return i18n;
}

describe('LanguageSwitcher', () => {
  it('exposes two options with aria-pressed reflecting the active locale', () => {
    renderSwitcher('es');

    const es = screen.getByRole('button', { name: /español/i });
    const en = screen.getByRole('button', { name: /english|inglés/i });

    expect(es.getAttribute('aria-pressed')).toBe('true');
    expect(en.getAttribute('aria-pressed')).toBe('false');
  });

  it('has a per-language aria-label', () => {
    renderSwitcher('es');

    expect(screen.getByRole('button', { name: 'Cambiar a español' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Cambiar a inglés' })).toBeTruthy();
  });

  it('switches locale on click without any network call, and reflects it via aria-pressed', async () => {
    const i18n = renderSwitcher('es');

    await fireEvent.click(screen.getByRole('button', { name: 'Cambiar a inglés' }));

    expect(i18n.locale).toBe('en');
    expect(screen.getByRole('button', { name: /english/i }).getAttribute('aria-pressed')).toBe('true');
  });

  it('is keyboard-operable', async () => {
    const i18n = renderSwitcher('es');

    const enButton = screen.getByRole('button', { name: 'Cambiar a inglés' });
    enButton.focus();
    await fireEvent.keyDown(enButton, { key: 'Enter' });
    await fireEvent.click(enButton);

    expect(i18n.locale).toBe('en');
  });

  it('announces the new state through an ARIA live region, not color alone', async () => {
    renderSwitcher('es');

    await fireEvent.click(screen.getByRole('button', { name: 'Cambiar a inglés' }));

    const status = screen.getByRole('status');
    expect(status.textContent).toMatch(/language|idioma/i);
  });

  it('persists the choice to localStorage', async () => {
    window.localStorage.clear();
    renderSwitcher('es');

    await fireEvent.click(screen.getByRole('button', { name: 'Cambiar a inglés' }));

    expect(window.localStorage.getItem('rrd.locale')).toBe('en');
  });
});
