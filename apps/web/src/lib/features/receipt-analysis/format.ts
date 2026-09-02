/**
 * DESIGN.md §13: amount/date formatting uses `Intl.NumberFormat` /
 * `Intl.DateTimeFormat` with the active locale; the amount `currency` stays
 * the server-provided code (`ARS` today), never re-derived client-side.
 * Locale is fixed `es-AR` in this slice — locale switching lands in slice 3.
 */

export function formatAmount(
  value: string | null | undefined,
  currency = 'ARS'
): string | null {
  if (value === null || value === undefined) return null;
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return null;
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency }).format(numeric);
}

export function formatDateTime(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat('es-AR', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}
