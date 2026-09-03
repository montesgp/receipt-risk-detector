/**
 * Core upload -> result e2e flow (tasks.md Slice 4 task 2.1; design.md
 * "Playwright slice 4 sketch"). The API is fully mocked via route
 * interception so this suite never depends on a running `apps/api`
 * instance (design.md Testing Strategy).
 *
 * Also covers the "Server-side validation error is explained" and
 * "Network failure shows a connectivity state" spec scenarios — added
 * beyond task 2.1's literal wording per this apply batch's explicit
 * instruction to cover a validation error state and a connectivity error
 * state at minimum.
 */
import { test, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MOCK_ANALYZE_RESPONSE, problemDetails } from './fixtures/responses';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RECEIPT_FIXTURE = path.join(__dirname, 'fixtures', 'receipt.png');
const ANALYZE_URL = '**/v1/receipts/analyze';

test.describe('upload to result', () => {
  test('successful upload renders the full result screen', async ({ page }) => {
    await page.route(ANALYZE_URL, async (route) => {
      await route.fulfill({ status: 200, json: MOCK_ANALYZE_RESPONSE });
    });

    await page.goto('/');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(RECEIPT_FIXTURE);

    await page.getByRole('button', { name: /analiz/i }).click();

    const heading = page.getByRole('heading', { name: /resultado del análisis/i });
    await expect(heading).toBeVisible();
    // Slice 4 focus management: the heading receives focus on render.
    await expect(heading).toBeFocused();

    await expect(page.getByText('74 / 100')).toBeVisible();
    await expect(page.locator('li.evidence-item')).toHaveCount(1);
    await expect(page.getByText(/^\*+5678$/)).toBeVisible();
    // The client-owned disclaimer must render; the raw server limitations[]
    // text (deliberately different in the fixture) must never appear.
    // Both the always-mounted ReconciliationNotice and ResultView's own
    // disclaimer render the identical DESIGN.md §5 sentence; at least one
    // visible match is required.
    await expect(
      page.getByText(/Confirmá la acreditación en la cuenta beneficiaria/i).first()
    ).toBeVisible();
    await expect(page.getByText(/raw server limitation text/i)).toHaveCount(0);
  });

  test('a validation error shows an actionable message and preserves retry, never a raw stack trace', async ({
    page
  }) => {
    await page.route(ANALYZE_URL, async (route) => {
      await route.fulfill({ status: 415, json: problemDetails(415, 'UNSUPPORTED_IMAGE') });
    });

    await page.goto('/');
    await page.locator('input[type="file"]').setInputFiles(RECEIPT_FIXTURE);
    await page.getByRole('button', { name: /analiz/i }).click();

    const alert = page.getByRole('alert');
    await expect(alert).toBeVisible();
    await expect(alert).toBeFocused();
    await expect(alert).toContainText(/PNG, JPG o WebP/i);
    await expect(alert).not.toContainText(/Traceback/i);

    // Rejected files clear back to idle — the drop zone is available again.
    await expect(page.getByText(/Arrastrá o seleccioná un comprobante/i)).toBeVisible();
  });

  test('a connectivity failure renders a distinct service-unavailable state, never a result', async ({
    page
  }) => {
    await page.route(ANALYZE_URL, async (route) => {
      await route.abort('failed');
    });

    await page.goto('/');
    await page.locator('input[type="file"]').setInputFiles(RECEIPT_FIXTURE);
    await page.getByRole('button', { name: /analiz/i }).click();

    const alert = page.getByRole('alert');
    await expect(alert).toBeVisible();
    await expect(alert).toContainText(/no pudimos contactar/i);
    await expect(page.getByRole('heading', { name: /resultado del análisis/i })).toHaveCount(0);
  });
});
