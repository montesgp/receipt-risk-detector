// design.md DD4/DD5, DESIGN.md §13 "Resolution order": ?lang= →
// localStorage['rrd.locale'] → navigator.languages → 'es'. Unknown ?lang=
// values are ignored. Missing keys fall back active locale → es → raw key,
// never an empty string.
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { resolveLocale } from '../../src/lib/i18n/resolve';
import { I18n } from '../../src/lib/i18n/i18n.svelte';

function fakeStorage(initial: Record<string, string> = {}): Storage {
  const store = new Map(Object.entries(initial));
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
    removeItem: (key: string) => void store.delete(key),
    clear: () => store.clear(),
    key: (index: number) => [...store.keys()][index] ?? null,
    get length() {
      return store.size;
    }
  } as Storage;
}

describe('resolveLocale', () => {
  it('prefers ?lang= when it is a supported locale', () => {
    const locale = resolveLocale({
      search: new URLSearchParams('lang=en'),
      storage: fakeStorage({ 'rrd.locale': 'es' }),
      languages: ['es-AR']
    });
    expect(locale).toBe('en');
  });

  it('ignores an unsupported ?lang= value and falls through to storage', () => {
    const locale = resolveLocale({
      search: new URLSearchParams('lang=zz'),
      storage: fakeStorage({ 'rrd.locale': 'en' }),
      languages: ['es-AR']
    });
    expect(locale).toBe('en');
  });

  it('falls back to localStorage when there is no query override', () => {
    const locale = resolveLocale({
      search: new URLSearchParams(''),
      storage: fakeStorage({ 'rrd.locale': 'en' }),
      languages: ['es-AR']
    });
    expect(locale).toBe('en');
  });

  it('falls back to navigator.languages when nothing is stored', () => {
    const locale = resolveLocale({
      search: new URLSearchParams(''),
      storage: fakeStorage(),
      languages: ['en-US', 'es-AR']
    });
    expect(locale).toBe('en');
  });

  it('defaults to es when nothing matches', () => {
    const locale = resolveLocale({
      search: new URLSearchParams(''),
      storage: fakeStorage(),
      languages: ['fr-FR']
    });
    expect(locale).toBe('es');
  });
});

describe('I18n', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.localStorage.clear();
  });

  it('resolves t() using the constructed locale', () => {
    const i18n = new I18n('en');
    expect(i18n.t('upload.preview.analyze')).toBe('Analyze');
  });

  it('re-resolves every key when the locale changes, without any network call', () => {
    const i18n = new I18n('es');
    expect(i18n.t('upload.preview.analyze')).toBe('Analizar');

    i18n.setLocale('en');

    expect(i18n.locale).toBe('en');
    expect(i18n.t('upload.preview.analyze')).toBe('Analyze');
    expect(window.localStorage.getItem('rrd.locale')).toBe('en');
  });

  it('falls back to the raw key for an unknown key, never an empty string', () => {
    const i18n = new I18n('en');
    expect(i18n.t('does.not.exist')).toBe('does.not.exist');
  });

  it('interpolates params into the resolved template', () => {
    const i18n = new I18n('es');
    expect(i18n.t('result.confidenceLabel', { confidence: 81 })).toBe('Confianza del análisis: 81%');
  });
});
