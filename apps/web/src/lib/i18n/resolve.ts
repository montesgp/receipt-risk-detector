/**
 * DD4 (design.md) / DESIGN.md §13 "Resolution order":
 *   ?lang= → localStorage['rrd.locale'] → navigator.languages → 'es'
 *
 * `?lang=` is validated against the supported locale set; an unsupported
 * value (e.g. `?lang=zz`) is ignored and resolution falls through to the
 * next source, per DESIGN.md §13 and the "Full bilingual ES/EN UI copy"
 * spec area.
 */

export type Locale = 'es' | 'en';

export const SUPPORTED_LOCALES: readonly Locale[] = ['es', 'en'];
export const LOCALE_STORAGE_KEY = 'rrd.locale';
const FALLBACK_LOCALE: Locale = 'es';

function isSupportedLocale(value: string | null | undefined): value is Locale {
  return value === 'es' || value === 'en';
}

export interface ResolveLocaleOptions {
  search?: URLSearchParams;
  storage?: Pick<Storage, 'getItem'>;
  languages?: readonly string[];
}

export function resolveLocale(options: ResolveLocaleOptions = {}): Locale {
  const search =
    options.search ??
    (typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : undefined);
  const fromQuery = search?.get('lang');
  if (isSupportedLocale(fromQuery)) return fromQuery;

  const storage = options.storage ?? (typeof window !== 'undefined' ? window.localStorage : undefined);
  const stored = storage?.getItem(LOCALE_STORAGE_KEY);
  if (isSupportedLocale(stored)) return stored;

  const languages =
    options.languages ?? (typeof navigator !== 'undefined' ? navigator.languages : undefined);
  if (languages) {
    for (const language of languages) {
      const primary = language.slice(0, 2).toLowerCase();
      if (isSupportedLocale(primary)) return primary;
    }
  }

  return FALLBACK_LOCALE;
}

/** Returns the `?lang=` value from `search` only if it is a supported locale, else `undefined`. */
export function queryLocaleOverride(search: URLSearchParams): Locale | undefined {
  const value = search.get('lang');
  return isSupportedLocale(value) ? value : undefined;
}

export function persistLocale(locale: Locale, storage: Pick<Storage, 'setItem'> = window.localStorage): void {
  storage.setItem(LOCALE_STORAGE_KEY, locale);
}
