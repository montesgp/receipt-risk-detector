/**
 * Slice 3b Phase 3 (Success Criteria): proves no user-facing hardcoded
 * Spanish string literal remains in any component's markup outside the
 * centralized `lib/i18n/messages/{es,en}.json` catalogs. This is the
 * "grep-based CI step" alternative to a manual audit — it runs as part of
 * the existing `npx vitest run` CI job (see `.github/workflows/ci.yml`
 * "web" job), so a future regression fails CI automatically.
 *
 * Scope: `<script>` blocks and HTML comments are stripped before scanning,
 * since developer-facing code/comments are not user-facing copy. What
 * remains is template markup (text nodes and attribute values), which must
 * never contain accented Spanish characters — every real message goes
 * through `i18n.t(...)`.
 */
import { describe, expect, it } from 'vitest';

// Vite's import.meta.glob reads file contents at build/test time without
// Node's fs/path modules -- this workspace deliberately has no @types/node
// installed (see vite.config.ts's comment on the same tradeoff), so a
// node:fs-based version of this test fails svelte-check in CI even though
// it runs fine under plain vitest locally.
const componentSources = import.meta.glob('../../src/lib/components/*.svelte', {
  query: '?raw',
  import: 'default',
  eager: true
}) as Record<string, string>;

function stripScriptAndComments(source: string): string {
  return source
    .replace(/<script[^>]*>[\s\S]*?<\/script>/g, '')
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<style[^>]*>[\s\S]*?<\/style>/g, '');
}

describe('literal-copy audit: no hardcoded Spanish markup outside i18n catalogs', () => {
  const files = Object.keys(componentSources).map((path) => path.split('/').pop() as string);

  it('found at least one component to scan (sweep coverage sanity check)', () => {
    expect(files.length).toBeGreaterThanOrEqual(14);
  });

  it.each(Object.entries(componentSources))('%s has no hardcoded accented-Spanish text in its markup', (path, source) => {
    const file = path.split('/').pop();
    const markup = stripScriptAndComments(source);

    // Any of these accented characters appearing in template markup means a
    // literal Spanish string slipped through instead of going via t().
    const accentedSpanish = /[áéíóúñÁÉÍÓÚÑ¿¡]/;
    const match = markup.match(accentedSpanish);

    expect(match, `Found hardcoded Spanish-looking text in ${file}: ${match?.[0]}`).toBeNull();
  });
});
