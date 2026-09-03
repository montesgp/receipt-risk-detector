// Spec "Switchers are keyboard-operable with visible focus" and "State
// change is announced and not color-only": tri-state `aria-checked`,
// keyboard-operable (native `<button>` + arrow-key roving), and the new
// state announced via an ARIA live region (`role="status"`).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/svelte';
import ThemeSwitcher from '../../src/lib/components/ThemeSwitcher.svelte';
import { THEME_CONTEXT_KEY, ThemeController } from '../../src/lib/theme/theme.svelte';

afterEach(() => cleanup());

function stubMatchMedia() {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: () => true
  }));
}

function renderSwitcher() {
  stubMatchMedia();
  const controller = new ThemeController();
  render(ThemeSwitcher, { context: new Map([[THEME_CONTEXT_KEY, controller]]) });
  return controller;
}

describe('ThemeSwitcher', () => {
  it('exposes a tri-state radiogroup with aria-checked reflecting the current mode', () => {
    renderSwitcher();

    const radios = screen.getAllByRole('radio');
    expect(radios).toHaveLength(3);
    const checked = radios.find((radio) => radio.getAttribute('aria-checked') === 'true');
    expect(checked?.textContent).toMatch(/Sistema/i);
  });

  it('selects a theme on click and reflects it in aria-checked', async () => {
    const controller = renderSwitcher();

    const darkRadio = screen.getByRole('radio', { name: /Oscuro/i });
    await fireEvent.click(darkRadio);

    expect(controller.mode).toBe('dark');
    expect(darkRadio.getAttribute('aria-checked')).toBe('true');
  });

  it('announces the new state through an ARIA live region, not color alone', async () => {
    renderSwitcher();

    await fireEvent.click(screen.getByRole('radio', { name: /Oscuro/i }));

    const status = screen.getByRole('status');
    expect(status.textContent).toMatch(/Oscuro/i);
  });

  it('is keyboard-operable: ArrowRight moves selection without a pointer device', async () => {
    const controller = renderSwitcher();

    const systemRadio = screen.getByRole('radio', { name: /Sistema/i });
    systemRadio.focus();
    await fireEvent.keyDown(systemRadio, { key: 'ArrowRight' });

    expect(controller.mode).toBe('light');
  });
});
