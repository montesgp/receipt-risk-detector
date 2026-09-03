// DD3 (design.md): 'system' resolves from `prefers-color-scheme` via
// `matchMedia`; an explicit choice persists to `localStorage['rrd.theme']`
// and overrides `system`; `prefers-reduced-motion` skips the
// `.theme-transition` class per DESIGN.md §12 "Reduced motion".
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ThemeController } from '../../src/lib/theme/theme.svelte';

function stubMatchMedia({ dark = false, reducedMotion = false } = {}) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => {
    const matches = query.includes('prefers-color-scheme')
      ? dark
      : query.includes('prefers-reduced-motion')
        ? reducedMotion
        : false;
    return {
      matches,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: () => true
    };
  });
}

beforeEach(() => {
  window.localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
  document.documentElement.classList.remove('theme-transition');
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ThemeController', () => {
  it('resolves system mode from matchMedia prefers-color-scheme (dark)', () => {
    stubMatchMedia({ dark: true });
    const controller = new ThemeController();

    expect(controller.mode).toBe('system');
    expect(controller.resolved).toBe('dark');
    expect(document.documentElement.dataset.theme).toBe('dark');
  });

  it('resolves system mode from matchMedia prefers-color-scheme (light)', () => {
    stubMatchMedia({ dark: false });
    const controller = new ThemeController();

    expect(controller.resolved).toBe('light');
    expect(document.documentElement.dataset.theme).toBe('light');
  });

  it('restores a previously persisted explicit choice on construction', () => {
    stubMatchMedia({ dark: false });
    window.localStorage.setItem('rrd.theme', 'dark');

    const controller = new ThemeController();

    expect(controller.mode).toBe('dark');
    expect(controller.resolved).toBe('dark');
  });

  it('persists an explicit choice to localStorage and applies it immediately', () => {
    stubMatchMedia({ dark: false });
    const controller = new ThemeController();

    controller.setTheme('dark');

    expect(window.localStorage.getItem('rrd.theme')).toBe('dark');
    expect(controller.resolved).toBe('dark');
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(document.documentElement.style.colorScheme).toBe('dark');
  });

  it('clears the stored key when switching back to system', () => {
    stubMatchMedia({ dark: false });
    const controller = new ThemeController();

    controller.setTheme('dark');
    controller.setTheme('system');

    expect(window.localStorage.getItem('rrd.theme')).toBeNull();
    expect(controller.resolved).toBe('light');
  });

  it('skips the transition class under prefers-reduced-motion', () => {
    stubMatchMedia({ dark: false, reducedMotion: true });
    const controller = new ThemeController();

    controller.setTheme('dark');

    expect(document.documentElement.classList.contains('theme-transition')).toBe(false);
  });

  it('applies the transition class when motion is not reduced', () => {
    stubMatchMedia({ dark: false, reducedMotion: false });
    const controller = new ThemeController();

    controller.setTheme('dark');

    expect(document.documentElement.classList.contains('theme-transition')).toBe(true);
  });
});
