/**
 * Phase 1 (slice 1b): `Intl`-based amount/date formatting. These are pure
 * functions with no DOM dependency — formatted per DESIGN.md §13's
 * `Intl.NumberFormat`/`Intl.DateTimeFormat` guidance (locale is fixed
 * `es-AR` in this slice; locale-switching lands in slice 3).
 */
import { describe, expect, it } from 'vitest';
import { formatAmount, formatDateTime } from '../../src/lib/features/receipt-analysis/format';

describe('formatAmount', () => {
  it('formats a numeric string as ARS currency', () => {
    expect(formatAmount('125000.00')).toMatch(/125[.,]?000/);
    expect(formatAmount('125000.00')).toMatch(/\$/);
  });

  it('respects an explicit currency code', () => {
    expect(formatAmount('10.5', 'USD')).toMatch(/US\$|USD|\$/);
  });

  it('returns null for null/undefined input', () => {
    expect(formatAmount(null)).toBeNull();
    expect(formatAmount(undefined)).toBeNull();
  });

  it('returns null for a non-numeric string rather than throwing', () => {
    expect(formatAmount('not-a-number')).toBeNull();
  });
});

describe('formatDateTime', () => {
  it('formats an ISO datetime string into a readable es-AR date/time', () => {
    const result = formatDateTime('2026-09-01T14:43:00-03:00');
    expect(result).not.toBeNull();
    expect(result).toMatch(/2026/);
  });

  it('returns null for null/undefined/empty input', () => {
    expect(formatDateTime(null)).toBeNull();
    expect(formatDateTime(undefined)).toBeNull();
    expect(formatDateTime('')).toBeNull();
  });

  it('returns null for an unparseable date string rather than throwing', () => {
    expect(formatDateTime('not-a-date')).toBeNull();
  });
});
