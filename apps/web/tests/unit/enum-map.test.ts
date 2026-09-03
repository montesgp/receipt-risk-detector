// design.md i18n contract "Server enums": classification/action/severity
// codes map to message keys; unknown signal codes have no catalogued key
// and fall back to the server's own `description` field.
import { describe, expect, it } from 'vitest';
import { actionKey, classificationKey, severityKey, signalKey } from '../../src/lib/i18n/enum-map';
import es from '../../src/lib/i18n/messages/es.json';

describe('enum-map', () => {
  it('maps every known classification code to an existing message key', () => {
    for (const code of ['LOW_RISK', 'REVIEW_RECOMMENDED', 'SUSPICIOUS', 'HIGH_RISK', 'INCONCLUSIVE']) {
      const key = classificationKey(code);
      expect(key).toBeDefined();
      expect(Object.keys(es)).toContain(key);
    }
  });

  it('maps every known recommended-action code to an existing message key', () => {
    for (const code of [
      'STANDARD_MANUAL_RECONCILIATION',
      'PRIORITY_MANUAL_RECONCILIATION',
      'DO_NOT_RELY_ON_RECEIPT'
    ]) {
      const key = actionKey(code);
      expect(key).toBeDefined();
      expect(Object.keys(es)).toContain(key);
    }
  });

  it('maps every known severity level to an existing message key', () => {
    for (const level of ['info', 'low', 'medium', 'high', 'critical']) {
      const key = severityKey(level);
      expect(key).toBeDefined();
      expect(Object.keys(es)).toContain(key);
    }
  });

  it('returns undefined for an unmapped classification/action/severity code', () => {
    expect(classificationKey('UNKNOWN')).toBeUndefined();
    expect(actionKey('UNKNOWN')).toBeUndefined();
    expect(severityKey('unknown')).toBeUndefined();
  });

  it('falls back to undefined for an uncatalogued signal code, forcing callers onto description', () => {
    expect(signalKey('SOME_NEW_SIGNAL')).toBeUndefined();
    expect(signalKey('KNOWN_SIGNAL', { KNOWN_SIGNAL: 'evidence.signal.KNOWN_SIGNAL' })).toBe(
      'evidence.signal.KNOWN_SIGNAL'
    );
  });
});
