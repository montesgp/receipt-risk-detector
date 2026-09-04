/**
 * tasks.md Slice 4 task 2.4 / design.md Open Questions: "One real-API spec
 * stays opt-in behind an env flag so CI is not coupled to a running API."
 *
 * Excluded from the default Playwright run by `playwright.config.ts`'s
 * `grepInvert` (matches the `@real-api` tag) unless `RUN_REAL_API=1` is set.
 * Requires a real `apps/api` instance reachable at `PUBLIC_API_BASE_URL`
 * (see docs/wiki/Local-Setup.md) — this is intentionally NOT run in CI.
 */
import { test, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RECEIPT_FIXTURE = path.join(__dirname, 'fixtures', 'receipt.png');

test.describe('real API integration @real-api', () => {
  test('uploading a real receipt against a live apps/api returns a result or a documented error', async ({
    page
  }) => {
    await page.goto('/');
    await page.locator('input[type="file"]').setInputFiles(RECEIPT_FIXTURE);
    await page.getByRole('button', { name: /analiz/i }).click();

    // The synthetic 1x1 PNG fixture is not a real receipt, so the API may
    // legitimately reject it (e.g. IMAGE_DIMENSIONS_EXCEEDED or a low-
    // confidence INCONCLUSIVE result) — this spec only proves the full
    // client -> live-API -> client round trip completes into ONE of the
    // documented terminal states, never an unhandled crash.
    const resultHeading = page.getByRole('heading', { name: /resultado del análisis/i });
    const alert = page.getByRole('alert');
    await expect(resultHeading.or(alert)).toBeVisible({ timeout: 30_000 });
  });
});
