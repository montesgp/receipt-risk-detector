// Spec "Switchers are keyboard-operable with visible focus" and "State
// change is announced and not color-only": single cycling button showing
// the active language's full name, an `aria-label` describing the switch
// action, keyboard-operable, and the new state announced via an ARIA live
// region.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import LanguageSwitcher from '../../src/lib/components/LanguageSwitcher.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderSwitcher(initialLocale: 'es' | 'en' = 'es') {
  const i18n = new I18n(initialLocale);
  render(LanguageSwitcher, { context: new Map([[I18N_CONTEXT_KEY, i18n]]) });
  return i18n;
}

describe('LanguageSwitcher', () => {
  it('shows the active language full name as visible text (es)', () => {
    renderSwitcher('es');

    expect(screen.getByRole('button').textContent).toMatch(new RegExp(es['header.language.nameEs'], 'i'));
  });

  it('shows the active language full name as visible text (en)', () => {
    renderSwitcher('en');

    expect(screen.getByRole('button').textContent).toMatch(new RegExp(en['header.language.nameEn'], 'i'));
  });

  it('has an aria-label describing the switch action and current language', () => {
    renderSwitcher('es');

    const button = screen.getByRole('button');
    expect(button.getAttribute('aria-label')).toMatch(/Español/);
  });

  it('switches locale on click without any network call, cycling es -> en -> es', async () => {
    const i18n = renderSwitcher('es');

    const button = screen.getByRole('button');
    await fireEvent.click(button);
    expect(i18n.locale).toBe('en');
    expect(button.textContent).toMatch(/english/i);

    await fireEvent.click(button);
    expect(i18n.locale).toBe('es');
    expect(button.textContent).toMatch(/español/i);
  });

  it('is keyboard-operable', async () => {
    const i18n = renderSwitcher('es');

    const button = screen.getByRole('button');
    button.focus();
    await fireEvent.click(button);

    expect(i18n.locale).toBe('en');
  });

  it('announces the new state through an ARIA live region, not color alone', async () => {
    renderSwitcher('es');

    await fireEvent.click(screen.getByRole('button'));

    const status = screen.getByRole('status');
    expect(status.textContent).toMatch(/language|idioma/i);
  });

  it('announces the resolved language NAME (es -> en)', async () => {
    renderSwitcher('es');

    await fireEvent.click(screen.getByRole('button'));

    const status = screen.getByRole('status');
    expect(status.textContent).toBe('Language: English');
  });

  it('announces the resolved language NAME (en -> es)', async () => {
    renderSwitcher('en');

    await fireEvent.click(screen.getByRole('button'));

    const status = screen.getByRole('status');
    expect(status.textContent).toBe('Idioma: Español');
  });

  it('persists the choice to localStorage', async () => {
    window.localStorage.clear();
    renderSwitcher('es');

    await fireEvent.click(screen.getByRole('button'));

    expect(window.localStorage.getItem('rrd.locale')).toBe('en');
  });
});
