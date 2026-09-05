/**
 * Slice 3b Phase 3 (Success Criteria), widened in slice 4's corrective pass:
 * proves no user-facing hardcoded Spanish string literal remains in any
 * component OR route markup outside the centralized
 * `lib/i18n/messages/{es,en}.json` catalogs. This is the "grep-based CI
 * step" alternative to a manual audit — it runs as part of the existing
 * `npx vitest run` CI job (see `.github/workflows/ci.yml` "web" job), so a
 * future regression fails CI automatically.
 *
 * Slice 4's sdd-verify found this test originally only globbed
 * `src/lib/components/*.svelte`, so `src/routes/+page.svelte`'s hardcoded
 * heading/intro/button text (introduced in slice 1a, never caught) slipped
 * through every prior run. Fixed two ways: (1) widened the glob to also
 * cover `src/routes/**\/*.svelte`, (2) added a wordlist check, since
 * "Analizar otro comprobante" has no accented characters at all and the
 * original accent-only regex could never have caught it regardless of
 * scope.
 *
 * Scope: `<script>` blocks and HTML comments are stripped before scanning,
 * since developer-facing code/comments are not user-facing copy. What
 * remains is template markup (text nodes and attribute values), which must
 * never contain accented Spanish characters or a common accent-free
 * Spanish word — every real message goes through `i18n.t(...)`.
 */
import { describe, expect, it } from 'vitest';

// Vite's import.meta.glob reads file contents at build/test time without
// Node's fs/path modules -- this workspace deliberately has no @types/node
// installed (see vite.config.ts's comment on the same tradeoff), so a
// node:fs-based version of this test fails svelte-check in CI even though
// it runs fine under plain vitest locally.
const sources = {
  ...import.meta.glob('../../src/lib/components/*.svelte', {
    query: '?raw',
    import: 'default',
    eager: true
  }),
  ...import.meta.glob('../../src/routes/**/*.svelte', {
    query: '?raw',
    import: 'default',
    eager: true
  })
} as Record<string, string>;

function stripScriptAndComments(source: string): string {
  return source
    .replace(/<script[^>]*>[\s\S]*?<\/script>/g, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/g, '');
}

// Accent-free Spanish words that have actually appeared in this app's
// hardcoded copy (not an exhaustive dictionary — a targeted deny-list for
// the words this project's copy tends to use, matched on word boundaries
// so it doesn't false-positive on English substrings).
const ACCENT_FREE_SPANISH_WORDS =
  /\b(analizar|comprobante|otro|otra|conciliar|conciliarlo|detectamos|revisar|transferencia|ayudarte)\b/i;

describe('new hedged copy contains no absolute-verdict language', () => {
  it('result.inconclusiveNoTextNote never asserts a definitive non-transfer verdict', async () => {
    const es = (await import('../../src/lib/i18n/messages/es.json')).default as Record<
      string,
      string
    >;
    const en = (await import('../../src/lib/i18n/messages/en.json')).default as Record<
      string,
      string
    >;

    const forbidden = /no es un comprobante|this is not a transfer/i;
    expect(forbidden.test(es['result.inconclusiveNoTextNote'])).toBe(false);
    expect(forbidden.test(en['result.inconclusiveNoTextNote'])).toBe(false);
  });
});

describe('literal-copy audit: no hardcoded Spanish markup outside i18n catalogs', () => {
  const files = Object.keys(sources).map((path) => path.split('/').pop() as string);

  it('found at least one component/route to scan (sweep coverage sanity check)', () => {
    expect(files.length).toBeGreaterThanOrEqual(15);
  });

  it.each(Object.entries(sources))(
    '%s has no hardcoded Spanish text in its markup',
    (path, source) => {
      const file = path.split('/').pop();
      const markup = stripScriptAndComments(source);

      const accentedSpanish = /[áéíóúñÁÉÍÓÚÑ¿¡]/;
      const accentMatch = markup.match(accentedSpanish);
      expect(
        accentMatch,
        `Found hardcoded accented Spanish text in ${file}: ${accentMatch?.[0]}`
      ).toBeNull();

      const wordMatch = markup.match(ACCENT_FREE_SPANISH_WORDS);
      expect(
        wordMatch,
        `Found hardcoded accent-free Spanish word in ${file}: ${wordMatch?.[0]}`
      ).toBeNull();
    }
  );
});
