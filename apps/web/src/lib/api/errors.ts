/**
 * DD2 failure taxonomy: a `fetch` rejection (API down, CORS blocked, DNS
 * failure) is semantically distinct from a structured `problem+json`
 * response and needs different copy/retry affordance. Never conflate them.
 */

import type { AnalyzeResponse, ProblemDetails } from './types';

export type ClientValidationReason = 'unsupported-type' | 'too-large';

export type AnalyzeFailure =
  | { kind: 'problem'; problem: ProblemDetails; retryAfterSeconds?: number }
  | { kind: 'network' }
  | { kind: 'malformed'; status: number }
  | { kind: 'client-validation'; reason: ClientValidationReason };

export type AnalyzeResult =
  | { ok: true; data: AnalyzeResponse }
  | { ok: false; failure: AnalyzeFailure };

/**
 * Parses the `Retry-After` header per docs/API.md §5b: an integer number of
 * seconds, present only on `429`. Returns `undefined` for a missing or
 * unparseable value rather than guessing a fallback wait time.
 */
export function parseRetryAfter(headerValue: string | null): number | undefined {
  if (!headerValue) return undefined;
  const seconds = Number(headerValue);
  if (!Number.isFinite(seconds) || seconds < 0) return undefined;
  return seconds;
}

export function isProblemDetails(value: unknown): value is ProblemDetails {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as Record<string, unknown>).code === 'string' &&
    typeof (value as Record<string, unknown>).status === 'number' &&
    typeof (value as Record<string, unknown>).detail === 'string'
  );
}

export function buildFailureFromResponse(
  status: number,
  body: unknown,
  retryAfterSeconds?: number
): AnalyzeFailure {
  if (!isProblemDetails(body)) {
    return { kind: 'malformed', status };
  }
  return { kind: 'problem', problem: body, retryAfterSeconds };
}
