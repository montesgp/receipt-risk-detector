/**
 * tasks.md Slice 4 task 2.3. design.md "Playwright slice 4 sketch": switch
 * to EN, assert the heading text changed with no second network request
 * (design.md "Result re-render on locale switch" — locale is a pure
 * client-side re-render, never a re-fetch/re-upload).
 */
import { test, expect } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MOCK_ANALYZE_RESPONSE } from './fixtures/responses';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RECEIPT_FIXTURE = path.join(__dirname, 'fixtures', 'receipt.png');

test.describe('locale switch', () => {
  test('switching to EN re-renders visible copy immediately without a second analyze request', async ({
    page
  }) => {
    let analyzeCallCount = 0;
    await page.route('**/v1/receipts/analyze', async (route) => {
      analyzeCallCount += 1;
      await route.fulfill({ status: 200, json: MOCK_ANALYZE_RESPONSE });
    });

    await page.goto('/');
    await page.locator('input[type="file"]').setInputFiles(RECEIPT_FIXTURE);
    await page.getByRole('button', { name: /analiz/i }).click();

    await expect(page.getByRole('heading', { name: /resultado del análisis/i })).toBeVisible();
    expect(analyzeCallCount).toBe(1);

    await page.getByRole('button', { name: /cambiar a inglés/i }).click();

    await expect(page.getByRole('heading', { name: /analysis result/i })).toBeVisible();
    expect(analyzeCallCount).toBe(1);
  });

  test('the whole app renders in Spanish by default and switches persist after reload', async ({
    page
  }) => {
    await page.goto('/');
    await expect(page.getByText(/Arrastrá o seleccioná un comprobante/i)).toBeVisible();

    await page.getByRole('button', { name: /cambiar a inglés/i }).click();
    await expect(page.getByRole('button', { name: /switch to spanish/i })).toBeVisible();

    await page.reload();
    await expect(page.getByRole('button', { name: /switch to spanish/i })).toBeVisible();

  });
});
