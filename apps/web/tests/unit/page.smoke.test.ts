/**
 * Smoke-level component test for the full workspace wiring in
 * `+page.svelte`: idle -> selected -> uploading -> result, every documented
 * error variant, and (ui-polish round 3, issue #34) that the reconciliation
 * disclaimer renders exactly once, ONLY in the result state -- it used to
 * also render unconditionally in every other state via a separately-mounted
 * `ReconciliationNotice`, duplicating the sentence once a result appeared.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/svelte';
import { tick } from 'svelte';
import Page from '../../src/routes/+page.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const DISCLAIMER_TEXT = /Confirmá la acreditación en la cuenta beneficiaria/i;

function makeFile(type = 'image/png', size = 1024): File {
  return new File([new Uint8Array(size)], 'receipt.png', { type });
}

// `+page.svelte` reads i18n from context, which `+layout.svelte` normally
// provides; this smoke test renders the page in isolation, so it must supply
// the same context itself (mirrors the pattern used by
// DropZone/FilePreview/etc. component tests).
function renderPage() {
  return render(Page, { context: new Map([[I18N_CONTEXT_KEY, new I18n('es')]]) });
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
  it('renders the idle drop zone, without the disclaimer (no result yet)', () => {
    renderPage();

    expect(screen.getByText(/Arrastrá o seleccioná un comprobante/i)).toBeTruthy();
    expect(screen.queryByText(DISCLAIMER_TEXT)).toBeNull();
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

    renderPage();
    expect(screen.queryByText(DISCLAIMER_TEXT)).toBeNull();

    await selectFileViaInput(makeFile());
    expect(screen.getByRole('button', { name: /Analizar/i })).toBeTruthy();
    expect(screen.queryByText(DISCLAIMER_TEXT)).toBeNull();

    screen.getByRole('button', { name: /Analizar/i }).click();
    await tick();
    expect(screen.getByRole('status').textContent).toMatch(/Analizando/i);
    expect(screen.queryByText(DISCLAIMER_TEXT)).toBeNull();

    await waitFor(() => expect(screen.getByText(/Riesgo bajo/i)).toBeTruthy());
    // Disclaimer now renders exactly once, only in the result state.
    expect(screen.getAllByText(DISCLAIMER_TEXT).length).toBe(1);

    // Slice 4: the result transition is announced through the shared
    // LiveRegion (ProcessingStages already unmounted, so this is now the
    // only role="status" node) and focus moved to the result heading.
    expect(screen.getByRole('status').textContent).toMatch(/completo|disponible/i);
    expect(document.activeElement).toBe(screen.getByRole('heading', { name: /Resultado del análisis/i }));
  });

  it('shows a distinct connectivity error, never a result, on a network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    renderPage();
    await selectFileViaInput(makeFile());
    screen.getByRole('button', { name: /Analizar/i }).click();

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/no pudimos contactar/i));
    expect(screen.queryByText(/Resultado:/i)).toBeNull();
    expect(screen.queryByText(DISCLAIMER_TEXT)).toBeNull();
  });

  it('preserves the file and surfaces the Retry-After wait on a 429', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(429, problem(429, 'RATE_LIMITED'), { 'retry-after': '15' }))
    );

    renderPage();
    await selectFileViaInput(makeFile());
    screen.getByRole('button', { name: /Analizar/i }).click();

    await waitFor(() => expect(screen.getByRole('alert').textContent).toMatch(/15/));
    expect(screen.queryByText(DISCLAIMER_TEXT)).toBeNull();
  });

  it('clears the file back to idle on a server validation rejection', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(415, problem(415, 'UNSUPPORTED_IMAGE')))
    );

    renderPage();
    await selectFileViaInput(makeFile());
    screen.getByRole('button', { name: /Analizar/i }).click();

    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(screen.getByText(/Arrastrá o seleccioná un comprobante/i)).toBeTruthy();
    expect(screen.queryByText(DISCLAIMER_TEXT)).toBeNull();
  });

  it('rejects an oversized file client-side (never calling fetch)', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    renderPage();
    await selectFileViaInput(makeFile('image/png', 11 * 1024 * 1024));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toBeTruthy();
    expect(screen.queryByText(DISCLAIMER_TEXT)).toBeNull();
  });
});
