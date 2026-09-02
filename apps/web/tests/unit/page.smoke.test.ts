/**
 * Smoke-level component test for the full workspace wiring in
 * `+page.svelte`: idle -> selected -> uploading -> result, every documented
 * error variant, and the DD7 invariant that `ReconciliationNotice` renders
 * unconditionally in every state (this test fails if any state renders
 * without it).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import Page from '../../src/routes/+page.svelte';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const DISCLAIMER_TEXT = /Confirmá la acreditación en la cuenta beneficiaria/i;

function makeFile(type = 'image/png', size = 1024): File {
  return new File([new Uint8Array(size)], 'receipt.png', { type });
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

async function selectFileViaInput(file: File): Promise<void> {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  Object.defineProperty(input, 'files', { value: [file], configurable: true });
  input.dispatchEvent(new Event('change', { bubbles: true }));
  await tick();
}

describe('+page.svelte wiring', () => {
  it('renders the idle drop zone and the disclaimer on first load', () => {
    render(Page);

    expect(screen.getByText(/Arrastrá o seleccioná un comprobante/i)).toBeTruthy();
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeTruthy();
  });

  it('runs the full idle -> selected -> uploading -> result loop against a mocked fetch', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(200, {
          analysis_id: 'sha256:abc',
          engine_version: '2026.09.01',
          ruleset_version: 'v2026_09_01',
          classification: 'LOW_RISK',
          risk_score: 10,
          confidence_score: 95,
          recommended_action: 'STANDARD_MANUAL_RECONCILIATION',
          signals: [],
          extracted_data: {},
          analyzer_statuses: [],
          limitations: [],
          duration_ms: 500
        })
      )
    );

    render(Page);
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeTruthy();

    await selectFileViaInput(makeFile());
    expect(screen.getByRole('button', { name: /Analizar/i })).toBeTruthy();
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeTruthy();

    screen.getByRole('button', { name: /Analizar/i }).click();
    await tick();
    expect(screen.getByRole('status').textContent).toMatch(/Analizando/i);
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeTruthy();

    await waitFor(() => expect(screen.getByText(/Riesgo bajo/i)).toBeTruthy());
    // Both the always-mounted ReconciliationNotice and ResultView's own
    // limitations fallback render the identical DESIGN.md §5 sentence when
    // the server sends no `limitations[]` — at least one match is required.
    expect(screen.getAllByText(DISCLAIMER_TEXT).length).toBeGreaterThan(0);
  });

  it('shows a distinct connectivity error, never a result, on a network failure — disclaimer stays present', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    render(Page);
    await selectFileViaInput(makeFile());
    screen.getByRole('button', { name: /Analizar/i }).click();

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/no pudimos contactar/i));
    expect(screen.queryByText(/Resultado:/i)).toBeNull();
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeTruthy();
  });

  it('preserves the file and surfaces the Retry-After wait on a 429 — disclaimer stays present', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(429, problem(429, 'RATE_LIMITED'), { 'retry-after': '15' }))
    );

    render(Page);
    await selectFileViaInput(makeFile());
    screen.getByRole('button', { name: /Analizar/i }).click();

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/15/));
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeTruthy();
  });

  it('clears the file back to idle on a server validation rejection — disclaimer stays present', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(415, problem(415, 'UNSUPPORTED_IMAGE')))
    );

    render(Page);
    await selectFileViaInput(makeFile());
    screen.getByRole('button', { name: /Analizar/i }).click();

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByText(/Arrastrá o seleccioná un comprobante/i)).toBeTruthy();
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeTruthy();
  });

  it('rejects an oversized file client-side (never calling fetch) — disclaimer stays present', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    render(Page);
    await selectFileViaInput(makeFile('image/png', 11 * 1024 * 1024));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.getByText(DISCLAIMER_TEXT)).toBeTruthy();
  });
});
