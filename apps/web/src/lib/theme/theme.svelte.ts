/**
 * DD3 (design.md) / DESIGN.md §12: cross-cutting theme state, provided
 * through Svelte context (per design.md's "lib/theme ... provided through
 * Svelte context" note) so any component in the tree can read/toggle it
 * without prop drilling.
 *
 * `mode` is the user's stored preference (`system` | `light` | `dark`).
 * `resolved` is the concrete theme actually applied to the DOM — for
 * `system` it follows `prefers-color-scheme` live via a `matchMedia`
 * listener. Only an explicit `light`/`dark` choice is persisted to
 * `localStorage['rrd.theme']`; `system` clears the stored key so the OS
 * preference keeps being the source of truth (DESIGN.md §12 "Persistence").
 */

import { getContext, setContext } from 'svelte';

export type ThemeMode = 'system' | 'light' | 'dark';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'rrd.theme';
const DARK_QUERY = '(prefers-color-scheme: dark)';
const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';
export const THEME_CONTEXT_KEY = Symbol('theme');

export class ThemeController {
  mode = $state<ThemeMode>('system');
  systemPrefersDark = $state(false);

  resolved: ResolvedTheme = $derived(
    this.mode === 'system' ? (this.systemPrefersDark ? 'dark' : 'light') : this.mode
  );

  private mediaQuery: MediaQueryList | null = null;

  constructor() {
    if (typeof window === 'undefined') return;

    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') {
      this.mode = stored;
    }

    this.mediaQuery = window.matchMedia(DARK_QUERY);
    this.systemPrefersDark = this.mediaQuery.matches;
    this.mediaQuery.addEventListener('change', this.handleSystemChange);

    this.apply();
  }

  private handleSystemChange = (event: MediaQueryListEvent): void => {
    this.systemPrefersDark = event.matches;
    this.apply();
  };

  setTheme(mode: ThemeMode): void {
    this.mode = mode;
    if (typeof window !== 'undefined') {
      if (mode === 'system') {
        window.localStorage.removeItem(STORAGE_KEY);
      } else {
        window.localStorage.setItem(STORAGE_KEY, mode);
      }
    }
    this.apply();
  }

  /** Detach the `matchMedia` listener; call when the owning component unmounts. */
  destroy(): void {
    this.mediaQuery?.removeEventListener('change', this.handleSystemChange);
  }

  private apply(): void {
    if (typeof document === 'undefined') return;

    const root = document.documentElement;
    const resolved = this.resolved;
    const reducedMotion =
      typeof window !== 'undefined' && window.matchMedia(REDUCED_MOTION_QUERY).matches;

    if (!reducedMotion) {
      root.classList.add('theme-transition');
      root.addEventListener(
        'transitionend',
        () => root.classList.remove('theme-transition'),
        { once: true }
      );
    }

    root.dataset.theme = resolved;
    root.style.colorScheme = resolved;
  }
}

export function setThemeContext(controller: ThemeController): ThemeController {
  return setContext(THEME_CONTEXT_KEY, controller);
}

export function getThemeContext(): ThemeController {
  return getContext<ThemeController>(THEME_CONTEXT_KEY);
}
