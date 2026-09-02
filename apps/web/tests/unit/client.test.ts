import { afterEach, describe, expect, it, vi } from 'vitest';
import { analyzeReceipt } from '../../src/lib/api/client';

function makeFile(options: { type?: string; size?: number; name?: string } = {}): File {
  const size = options.size ?? 1024;
  const bytes = new Uint8Array(size);
  return new File([bytes], options.name ?? 'receipt.png', { type: options.type ?? 'image/png' });
}

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...headers }
  });
}

function problem(status: number, code: string, detail = 'detail'): unknown {
  return {
    type: `https://project.example/problems/${code.toLowerCase()}`,
    title: code,
    status,
    detail,
    instance: '/v1/receipts/analyze',
    request_id: 'req_01',
    code
  };
}

describe('analyzeReceipt', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('maps a 200 response to an ok result', async () => {
    const body = { analysis_id: 'sha256:abc', classification: 'LOW_RISK' };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, body)));

    const result = await analyzeReceipt(makeFile());

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.classification).toBe('LOW_RISK');
    }
  });

  it.each([
    ['MISSING_FILE', 400],
    ['FILE_TOO_LARGE', 413],
    ['UNSUPPORTED_IMAGE', 415],
    ['IMAGE_DIMENSIONS_EXCEEDED', 422]
  ])('maps %s (%d) to a problem failure', async (code, status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(status, problem(status, code))));

    const result = await analyzeReceipt(makeFile());

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.failure.kind).toBe('problem');
      if (result.failure.kind === 'problem') {
        expect(result.failure.problem.code).toBe(code);
      }
    }
  });

  it('maps a 504 to a problem failure labeled by status for timeout handling', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(504, problem(504, 'ANALYSIS_TIMEOUT')))
    );

    const result = await analyzeReceipt(makeFile());

    expect(result.ok).toBe(false);
    if (!result.ok && result.failure.kind === 'problem') {
      expect(result.failure.problem.status).toBe(504);
      expect(result.failure.problem.code).toBe('ANALYSIS_TIMEOUT');
    }
  });

  it('maps a fetch rejection to a network failure, never a problem', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    const result = await analyzeReceipt(makeFile());

    expect(result).toEqual({ ok: false, failure: { kind: 'network' } });
  });

  it('parses Retry-After and preserves the 429 problem code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(429, problem(429, 'RATE_LIMITED'), { 'retry-after': '30' })
      )
    );

    const result = await analyzeReceipt(makeFile());

    expect(result.ok).toBe(false);
    if (!result.ok && result.failure.kind === 'problem') {
      expect(result.failure.problem.code).toBe('RATE_LIMITED');
      expect(result.failure.retryAfterSeconds).toBe(30);
    }
  });

  it('maps an unparseable error body to malformed', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('not json', { status: 500, headers: { 'content-type': 'text/plain' } })
      )
    );

    const result = await analyzeReceipt(makeFile());

    expect(result).toEqual({ ok: false, failure: { kind: 'malformed', status: 500 } });
  });

  it('rejects an oversized file client-side without calling fetch', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const result = await analyzeReceipt(makeFile({ size: 11 * 1024 * 1024 }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(result).toEqual({
      ok: false,
      failure: { kind: 'client-validation', reason: 'too-large' }
    });
  });

  it('rejects an unsupported file type client-side without calling fetch', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const result = await analyzeReceipt(makeFile({ type: 'application/pdf' }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(result).toEqual({
      ok: false,
      failure: { kind: 'client-validation', reason: 'unsupported-type' }
    });
  });
});
