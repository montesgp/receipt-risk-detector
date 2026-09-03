// Spec "Switchers are keyboard-operable with visible focus" and "State
// change is announced and not color-only": binary `aria-checked`,
// keyboard-operable (native `<button>` + arrow-key roving), and the new
// state announced via an ARIA live region (`role="status"`).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import ThemeSwitcher from '../../src/lib/components/ThemeSwitcher.svelte';
import { THEME_CONTEXT_KEY, ThemeController } from '../../src/lib/theme/theme.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => {
  cleanup();
  window.localStorage.clear();
});

function stubMatchMedia(matches = false) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: () => true
  }));
}

function renderSwitcher(locale: 'es' | 'en' = 'es') {
  stubMatchMedia();
  const controller = new ThemeController();
  render(ThemeSwitcher, {
    context: new Map<unknown, unknown>([
      [THEME_CONTEXT_KEY, controller],
      [I18N_CONTEXT_KEY, new I18n(locale)]
    ])
  });
  return controller;
}

describe('ThemeSwitcher', () => {
  it('exposes a binary radiogroup with aria-checked reflecting the resolved theme', () => {
    renderSwitcher();

    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(2);
    const checked = radios.find((radio) => radio.getAttribute('aria-checked') === 'true');
    expect(checked?.textContent).toMatch(new RegExp(es['theme.light'], 'i'));
  });

  it('exposes a binary radiogroup in English when locale is en', () => {
    renderSwitcher('en');

    const radios = screen.getAllByRole('radio');
    const checked = radios.find((radio) => radio.getAttribute('aria-checked') === 'true');
    expect(checked?.textContent).toMatch(new RegExp(en['theme.light'], 'i'));
  });

  it('selects a theme on click and reflects it in aria-checked', async () => {
    const controller = renderSwitcher();

    const darkRadio = screen.getByRole('radio', { name: new RegExp(es['theme.dark'], 'i') });
    await fireEvent.click(darkRadio);

    expect(controller.mode).toBe('dark');
    expect(darkRadio.getAttribute('aria-checked')).toBe('true');
  });

  it('announces the new state through an ARIA live region, not color alone', async () => {
    renderSwitcher();

    await fireEvent.click(screen.getByRole('radio', { name: new RegExp(es['theme.dark'], 'i') }));

    const status = screen.getByRole('status');
    expect(status.textContent).toMatch(new RegExp(es['theme.dark'], 'i'));
  });

  it('is keyboard-operable: ArrowRight moves selection without a pointer device', async () => {
    const controller = renderSwitcher();

    const lightRadio = screen.getByRole('radio', { name: new RegExp(es['theme.light'], 'i') });
    lightRadio.focus();
    await fireEvent.keyDown(lightRadio, { key: 'ArrowRight' });

    expect(controller.mode).toBe('dark');
  });

  // DESIGN.md §12 "Control": segmented control (>=768px) and cycling icon
  // button (<768px) both exist in the DOM at all times, toggled purely by a
  // CSS media query (verified for real layout in the Playwright viewport
  // spec, tests/e2e/theme-persistence.spec.ts — jsdom does not apply
  // stylesheet media queries to computed style, so structural presence is
  // what a Vitest unit test can reliably assert here).
  it('renders both the segmented control and the cycling icon button variants', () => {
    const { container } = render(ThemeSwitcher, {
      context: (() => {
        stubMatchMedia();
        return new Map<unknown, unknown>([
          [THEME_CONTEXT_KEY, new ThemeController()],
          [I18N_CONTEXT_KEY, new I18n('es')]
        ]);
      })()
    });

    expect(container.querySelector('.theme-switcher__segmented')).toBeTruthy();
    expect(container.querySelector('.theme-switcher__cycle')).toBeTruthy();
  });

  // jsdom does not apply stylesheet rules to `getComputedStyle`/layout, so a
  // real pixel measurement of the >=44x44px touch target (DESIGN.md §12) is
  // asserted in Playwright (tests/e2e/theme-persistence.spec.ts), which
  // renders in a real browser engine. This unit test only proves the class
  // that carries the min-width/min-height:44px rule (see the `<style>`
  // block in ThemeSwitcher.svelte) is present on both interactive elements.
  it('the cycling icon button and each segmented option carry the 44px-touch-target class', () => {
    const { container } = render(ThemeSwitcher, {
      context: (() => {
        stubMatchMedia();
        return new Map<unknown, unknown>([
          [THEME_CONTEXT_KEY, new ThemeController()],
          [I18N_CONTEXT_KEY, new I18n('es')]
        ]);
      })()
    });

    expect(container.querySelector('.theme-switcher__cycle')).toBeTruthy();
    expect(container.querySelectorAll('.theme-switcher__segmented button')).toHaveLength(2);
  });

  it('the cycling button advances mode on click (light -> dark -> light)', async () => {
    const controller = renderSwitcher();

    const cycleButton = screen.getByRole('button', { name: /Cambiar tema/i });
    await fireEvent.click(cycleButton);
    expect(controller.mode).toBe('dark');

    await fireEvent.click(cycleButton);
    expect(controller.mode).toBe('light');
  });

  // design.md "Decision: binary switcher keys off `controller.resolved`":
  // `mode` stays 'system' until the first explicit choice (ThemeController is
  // untouched), so a checked-state derived from `mode` would incorrectly show
  // "Light" on a dark-first-paint. This proves the bug is fixed by deriving
  // the checked state from `controller.resolved` instead.
  it('a dark system preference shows Dark checked before any explicit choice', () => {
    stubMatchMedia(true);
    const controller = new ThemeController();
    render(ThemeSwitcher, {
      context: new Map<unknown, unknown>([
        [THEME_CONTEXT_KEY, controller],
        [I18N_CONTEXT_KEY, new I18n('es')]
      ])
    });

    expect(controller.mode).toBe('system');
    expect(controller.resolved).toBe('dark');

    const radios = screen.getAllByRole('radio');
    const checked = radios.find((radio) => radio.getAttribute('aria-checked') === 'true');
    expect(checked?.textContent).toMatch(new RegExp(es['theme.dark'], 'i'));
  });
});
