import { afterEach, describe, expect, it, vi } from 'vitest';
import { AnalysisWorkspace } from '../../src/lib/features/receipt-analysis/workspace.svelte';

function makeFile(options: { type?: string; size?: number } = {}): File {
  const size = options.size ?? 1024;
  return new File([new Uint8Array(size)], 'receipt.png', { type: options.type ?? 'image/png' });
}

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json', ...headers }
  });
}

function problem(status: number, code: string): unknown {
  return {
    type: `https://project.example/problems/${code.toLowerCase()}`,
    title: code,
    status,
    detail: `${code} happened`,
    instance: '/v1/receipts/analyze',
    request_id: 'req_01',
    code
  };
}

describe('AnalysisWorkspace', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('starts idle', () => {
    const workspace = new AnalysisWorkspace();
    expect(workspace.status).toBe('idle');
    expect(workspace.file).toBeNull();
  });

  it('follows the idle -> selected -> uploading -> result happy path', async () => {
    const body = { analysis_id: 'sha256:abc', classification: 'LOW_RISK', risk_score: 10 };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, body)));

    const workspace = new AnalysisWorkspace();
    const file = makeFile();

    workspace.selectFile(file);
    expect(workspace.status).toBe('selected');
    expect(workspace.file).toBe(file);

    const pending = workspace.analyze();
    expect(workspace.status).toBe('uploading');
    await pending;

    expect(workspace.status).toBe('result');
    expect(workspace.result?.classification).toBe('LOW_RISK');
  });

  it('retains the file and stays retryable on a 429 rate-limit response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(429, problem(429, 'RATE_LIMITED'), { 'retry-after': '5' }))
    );

    const workspace = new AnalysisWorkspace();
    const file = makeFile();
    workspace.selectFile(file);
    await workspace.analyze();

    expect(workspace.status).toBe('error');
    expect(workspace.file).toBe(file);
    expect(workspace.error).toEqual({ kind: 'rate-limited', retryAfterSeconds: 5, detail: 'RATE_LIMITED happened' });
  });

  it('retains the file on a network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    const workspace = new AnalysisWorkspace();
    const file = makeFile();
    workspace.selectFile(file);
    await workspace.analyze();

    expect(workspace.status).toBe('error');
    expect(workspace.file).toBe(file);
    expect(workspace.error).toEqual({ kind: 'network' });
  });

  it('retains the file on a 504 timeout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(504, problem(504, 'ANALYSIS_TIMEOUT'))));

    const workspace = new AnalysisWorkspace();
    const file = makeFile();
    workspace.selectFile(file);
    await workspace.analyze();

    expect(workspace.status).toBe('error');
    expect(workspace.file).toBe(file);
    expect(workspace.error?.kind).toBe('timeout');
  });

  it.each([
    ['MISSING_FILE', 400],
    ['FILE_TOO_LARGE', 413],
    ['UNSUPPORTED_IMAGE', 415],
    ['IMAGE_DIMENSIONS_EXCEEDED', 422]
  ])('clears the file back to idle on %s (%d)', async (code, status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(status, problem(status, code))));

    const workspace = new AnalysisWorkspace();
    const file = makeFile();
    workspace.selectFile(file);
    await workspace.analyze();

    expect(workspace.status).toBe('idle');
    expect(workspace.file).toBeNull();
    expect(workspace.error).toEqual({ kind: 'rejected-file', code, detail: `${code} happened` });
  });

  it('never calls the API and clears back to idle for a client-validation failure', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const workspace = new AnalysisWorkspace();
    workspace.selectFile(makeFile({ type: 'application/pdf' }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(workspace.status).toBe('idle');
    expect(workspace.file).toBeNull();
    expect(workspace.error).toEqual({ kind: 'client-validation', reason: 'unsupported-type' });
  });

  it('reset clears file, result and error back to idle', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(200, { classification: 'LOW_RISK' })));

    const workspace = new AnalysisWorkspace();
    workspace.selectFile(makeFile());
    await workspace.analyze();
    expect(workspace.status).toBe('result');

    workspace.reset();

    expect(workspace.status).toBe('idle');
    expect(workspace.file).toBeNull();
    expect(workspace.result).toBeNull();
    expect(workspace.error).toBeNull();
  });
});
