/**
 * DD4/DD5 (design.md), DESIGN.md §13: cross-cutting locale state, provided
 * through Svelte context (mirrors `lib/theme/theme.svelte.ts`'s pattern) so
 * any component can call `t()` without prop drilling.
 *
 * Both message catalogs are bundled eagerly (DD4 — they're ~5 KB each and
 * locale switching must be synchronous, no loading state). Switching locale
 * only changes which catalog `t()` reads from; it never re-fetches or
 * re-uploads anything (design.md "Result re-render on locale switch").
 *
 * Fallback chain (DD5): active locale → 'es' → the raw key itself, never an
 * empty string. `console.warn` on a missing key only fires in dev builds.
 */

import { getContext, setContext } from 'svelte';
import es from './messages/es.json';
import en from './messages/en.json';
import { persistLocale, queryLocaleOverride, resolveLocale, type Locale } from './resolve';

type Messages = Record<string, string>;

const CATALOGS: Record<Locale, Messages> = { es, en };
const FALLBACK_LOCALE: Locale = 'es';

export const I18N_CONTEXT_KEY = Symbol('i18n');

export class I18n {
  locale = $state<Locale>(FALLBACK_LOCALE);

  constructor(initialLocale?: Locale) {
    if (initialLocale) {
      this.locale = initialLocale;
      return;
    }

    if (typeof window === 'undefined') return;

    const search = new URLSearchParams(window.location.search);
    this.locale = resolveLocale({
      search,
      storage: window.localStorage,
      languages: navigator.languages
    });

    // DESIGN.md §13 "Persistence": `?lang=` overrides for one visit and is
    // then persisted, which makes bilingual links shareable.
    const override = queryLocaleOverride(search);
    if (override) persistLocale(override, window.localStorage);
  }

  setLocale(locale: Locale): void {
    this.locale = locale;
    if (typeof window !== 'undefined') {
      persistLocale(locale, window.localStorage);
    }
  }

  t = (key: string, params?: Record<string, string | number>): string => {
    const catalog = CATALOGS[this.locale];
    const fallbackCatalog = CATALOGS[FALLBACK_LOCALE];
    const value = catalog?.[key] ?? fallbackCatalog?.[key];

    if (value === undefined && import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.warn(`[i18n] missing message key: "${key}"`);
    }

    return interpolate(value ?? key, params);
  };
}

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    name in params ? String(params[name]) : match
  );
}

export function setI18nContext(i18n: I18n): I18n {
  return setContext(I18N_CONTEXT_KEY, i18n);
}

export function getI18nContext(): I18n {
  return getContext<I18n>(I18N_CONTEXT_KEY);
}
