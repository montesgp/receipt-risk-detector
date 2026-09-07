/**
 * tasks.md Slice 4 task 2.2. design.md "Playwright slice 4 sketch": set
 * `localStorage['rrd.theme']='dark'`, reload, assert `<html
 * data-theme="dark">` on the *first* paint via an `addInitScript` probe (no
 * flash of the wrong theme, DD3/DESIGN.md §12).
 *
 * Also verifies the single-button ThemeSwitcher (ui-polish round 4, DESIGN.md
 * §12 "Control" row) shows a visible current-state label and a >=44x44px
 * touch target at every viewport width — needs a real browser layout
 * engine, which jsdom (used by the Vitest unit tests) does not provide.
 */
import { test, expect } from '@playwright/test';

test.describe('theme persistence', () => {
  test('an explicit dark preference applies on the very first paint after reload (no flash)', async ({
    page
  }) => {
    await page.goto('/');
    await page.evaluate(() => window.localStorage.setItem('rrd.theme', 'dark'));

    // Probe the `data-theme` attribute as early as possible — before any
    // Svelte hydration — to prove the blocking inline script in `app.html`
    // (DD3) is what sets it, not a post-hydration effect.
    await page.addInitScript(() => {
      const observer = new MutationObserver(() => {
        (window as unknown as { __themeAtFirstPaint?: string }).__themeAtFirstPaint =
          document.documentElement.dataset.theme;
      });
      observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    });

    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    const themeAttr = await page.evaluate(() => document.documentElement.dataset.theme);
    expect(themeAttr).toBe('dark');
  });

  test('reloading with no stored preference falls back to the OS/browser color-scheme preference', async ({
    page,
    browser
  }) => {
    const context = await browser.newContext({ colorScheme: 'dark' });
    const darkPage = await context.newPage();
    await darkPage.goto('/');

    const themeAttr = await darkPage.evaluate(() => document.documentElement.dataset.theme);
    expect(themeAttr).toBe('dark');

    await context.close();
  });
});

test.describe('theme switcher single-button control (DESIGN.md §12)', () => {
  for (const viewport of [
    { width: 1024, height: 768, label: 'desktop' },
    { width: 375, height: 812, label: 'mobile' }
  ]) {
    test(`shows the cycling button with a visible current-state label and a >=44x44px touch target (${viewport.label})`, async ({
      page
    }) => {
      await page.setViewportSize(viewport);
      await page.goto('/');

      const cycleButton = page.locator('.theme-switcher__cycle');
      await expect(cycleButton).toBeVisible();

      // The current state (e.g. "Claro"/"Oscuro") is visible text, not only
      // an aria-label (DESIGN.md §12 "a cycling icon button with a visible
      // current-state label").
      await expect(cycleButton).toHaveText(/Claro|Oscuro/i);

      const box = await cycleButton.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.width).toBeGreaterThanOrEqual(44);
      expect(box!.height).toBeGreaterThanOrEqual(44);

      const beforeLabel = await cycleButton.textContent();
      await cycleButton.click();
      const afterLabel = await cycleButton.textContent();
      expect(afterLabel).not.toBe(beforeLabel);
    });
  }
});
