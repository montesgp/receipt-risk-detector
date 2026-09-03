// DESIGN.md §13 "Source of truth": es.json defines the key set; a unit test
// asserts exact key parity between locales and fails CI on drift. design.md
// Testing Strategy "Key parity": Object.keys(es) === Object.keys(en), diff
// printed both ways, plus every value is a string (enforces flatness).
import { describe, expect, it } from 'vitest';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

describe('i18n key parity', () => {
  it('has an identical key set in both locales', () => {
    const esKeys = new Set(Object.keys(es));
    const enKeys = new Set(Object.keys(en));

    const onlyInEs = [...esKeys].filter((key) => !enKeys.has(key));
    const onlyInEn = [...enKeys].filter((key) => !esKeys.has(key));

    expect(onlyInEs, `keys only in es.json: ${JSON.stringify(onlyInEs)}`).toEqual([]);
    expect(onlyInEn, `keys only in en.json: ${JSON.stringify(onlyInEn)}`).toEqual([]);
  });

  it('has at least one namespaced key per known UI area', () => {
    const esKeys = Object.keys(es);
    for (const prefix of ['upload.', 'processing.', 'errors.', 'result.', 'evidence.', 'theme.', 'header.', 'legal.']) {
      expect(esKeys.some((key) => key.startsWith(prefix)), `no key with prefix "${prefix}"`).toBe(true);
    }
  });

  it('every value is a flat string in both locales', () => {
    for (const [key, value] of Object.entries(es)) {
      expect(typeof value, `es.json["${key}"] is not a string`).toBe('string');
    }
    for (const [key, value] of Object.entries(en)) {
      expect(typeof value, `en.json["${key}"] is not a string`).toBe('string');
    }
  });
});
