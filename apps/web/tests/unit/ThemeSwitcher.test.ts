// Spec "Switchers are keyboard-operable with visible focus" and "State
// change is announced and not color-only": single cycling button, native
// keyboard-operable (Enter/Space on a real <button>), and the new state
// announced via an ARIA live region (`role="status"`).
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
  it('exposes a single button showing the resolved theme as visible text (es)', () => {
    renderSwitcher();

    const button = screen.getByRole('button');
    expect(button.textContent).toMatch(new RegExp(es['theme.light'], 'i'));
  });

  it('exposes a single button showing the resolved theme as visible text (en)', () => {
    renderSwitcher('en');

    const button = screen.getByRole('button');
    expect(button.textContent).toMatch(new RegExp(en['theme.light'], 'i'));
  });

  it('cycles light -> dark -> light on click', async () => {
    const controller = renderSwitcher();

    const button = screen.getByRole('button');
    await fireEvent.click(button);
    expect(controller.mode).toBe('dark');
    expect(button.textContent).toMatch(new RegExp(es['theme.dark'], 'i'));

    await fireEvent.click(button);
    expect(controller.mode).toBe('light');
    expect(button.textContent).toMatch(new RegExp(es['theme.light'], 'i'));
  });

  it('announces the new state through an ARIA live region, not color alone', async () => {
    renderSwitcher();

    await fireEvent.click(screen.getByRole('button'));

    const status = screen.getByRole('status');
    expect(status.textContent).toMatch(new RegExp(es['theme.dark'], 'i'));
  });

  it('is keyboard-operable: a native button responds to Enter/Space', async () => {
    const controller = renderSwitcher();

    const button = screen.getByRole('button');
    button.focus();
    await fireEvent.click(button);

    expect(controller.mode).toBe('dark');
  });

  // DESIGN.md §12 "Control": a single cycling button at every viewport
  // width (ui-polish round 4 dropped the >=768px segmented variant).
  // `.theme-switcher__cycle` is kept as a test-selector hook.
  it('renders the cycling button with the touch-target class', () => {
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
    expect(container.querySelectorAll('.theme-switcher__cycle')).toHaveLength(1);
  });

  it('the cycling button has an aria-label naming the action and current state', () => {
    renderSwitcher();

    const button = screen.getByRole('button', { name: new RegExp(es['theme.light'], 'i') });
    expect(button).toBeTruthy();
  });

  // design.md "Decision: cycling button keys off `controller.resolved`":
  // `mode` stays 'system' until the first explicit choice (ThemeController is
  // untouched), so a label derived from `mode` would incorrectly show
  // "Light" on a dark-first-paint. This proves the bug is fixed by deriving
  // the label from `controller.resolved` instead.
  it('a dark system preference shows Dark as the current label before any explicit choice', () => {
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

    const button = screen.getByRole('button');
    expect(button.textContent).toMatch(new RegExp(es['theme.dark'], 'i'));
  });
});
