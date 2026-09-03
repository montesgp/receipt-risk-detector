/**
 * design.md i18n contract: server enums (`classification`,
 * `recommended_action`, `signals[].severity`) map client-side to
 * `result.classification.<CODE>` / `result.action.<CODE>` /
 * `evidence.severity.<level>` message keys. An unknown signal `code` has no
 * catalogued key — the server-provided `description` field is the only
 * text for it, so `signalKey` intentionally returns `undefined` for any
 * code not in the caller-supplied `known` map (DESIGN.md §13 "Server
 * enums").
 *
 * This module only maps codes to message keys; it does not call `t()`
 * itself. Wiring these into components is slice 3b's sweep.
 */

export const CLASSIFICATION_KEYS: Readonly<Record<string, string>> = {
  LOW_RISK: 'result.classification.LOW_RISK',
  REVIEW_RECOMMENDED: 'result.classification.REVIEW_RECOMMENDED',
  SUSPICIOUS: 'result.classification.SUSPICIOUS',
  HIGH_RISK: 'result.classification.HIGH_RISK',
  INCONCLUSIVE: 'result.classification.INCONCLUSIVE'
};

export const ACTION_KEYS: Readonly<Record<string, string>> = {
  STANDARD_MANUAL_RECONCILIATION: 'result.action.STANDARD_MANUAL_RECONCILIATION',
  PRIORITY_MANUAL_RECONCILIATION: 'result.action.PRIORITY_MANUAL_RECONCILIATION',
  DO_NOT_RELY_ON_RECEIPT: 'result.action.DO_NOT_RELY_ON_RECEIPT'
};

export const SEVERITY_KEYS: Readonly<Record<string, string>> = {
  info: 'evidence.severity.info',
  low: 'evidence.severity.low',
  medium: 'evidence.severity.medium',
  high: 'evidence.severity.high',
  critical: 'evidence.severity.critical'
};

export function classificationKey(code: string): string | undefined {
  return CLASSIFICATION_KEYS[code];
}

export function actionKey(code: string): string | undefined {
  return ACTION_KEYS[code];
}

export function severityKey(code: string): string | undefined {
  return SEVERITY_KEYS[code];
}

/**
 * Signal codes are open-ended — the server can add new ones without a
 * client release, so there is no catalogue for arbitrary codes. Callers
 * that want a canned title for a curated subset pass their own `known` map;
 * anything else should keep using the server's `description` field.
 */
export function signalKey(code: string, known: Readonly<Record<string, string>> = {}): string | undefined {
  return known[code];
}
