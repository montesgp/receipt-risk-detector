import { PUBLIC_API_BASE_URL } from '$env/static/public';
import type { AnalyzeResponse } from './types';
import {
  buildFailureFromResponse,
  parseRetryAfter,
  type AnalyzeResult,
  type ClientValidationReason
} from './errors';

const ANALYZE_PATH = '/v1/receipts/analyze';
const SUPPORTED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const MAX_FILE_BYTES = 10 * 1024 * 1024;

/**
 * Client-side pre-validation per the "File selection and validation"
 * requirement: the client MUST NOT call the API for a file it can already
 * reject locally (unsupported type or over the 10 MB limit).
 */
export function validateFileForUpload(file: File): ClientValidationReason | null {
  if (!SUPPORTED_TYPES.has(file.type)) {
    return 'unsupported-type';
  }
  if (file.size > MAX_FILE_BYTES) {
    return 'too-large';
  }
  return null;
}

export async function analyzeReceipt(file: File): Promise<AnalyzeResult> {
  const validationReason = validateFileForUpload(file);
  if (validationReason) {
    return { ok: false, failure: { kind: 'client-validation', reason: validationReason } };
  }

  const formData = new FormData();
  formData.append('file', file);

  let response: Response;
  try {
    response = await fetch(`${PUBLIC_API_BASE_URL}${ANALYZE_PATH}`, {
      method: 'POST',
      body: formData,
      headers: { Accept: 'application/json' }
    });
  } catch {
    return { ok: false, failure: { kind: 'network' } };
  }

  if (response.status === 200) {
    try {
      const data: AnalyzeResponse = await response.json();
      return { ok: true, data };
    } catch {
      return { ok: false, failure: { kind: 'malformed', status: 200 } };
    }
  }

  const retryAfterSeconds =
    response.status === 429 ? parseRetryAfter(response.headers.get('Retry-After')) : undefined;

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return { ok: false, failure: { kind: 'malformed', status: response.status } };
  }

  return { ok: false, failure: buildFailureFromResponse(response.status, body, retryAfterSeconds) };
}
