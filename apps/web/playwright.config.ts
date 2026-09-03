import { defineConfig, devices } from '@playwright/test';

/**
 * Slice 4: the core suite mocks the API entirely via Playwright route
 * interception (design.md "Testing Strategy" / "Playwright slice 4
 * sketch"), so it never depends on a running `apps/api` instance and stays
 * fast/deterministic in CI. `tests/e2e/real-api.spec.ts` is the sole
 * exception — it is excluded here by default (grep-invert) and only runs
 * when explicitly requested (`RUN_REAL_API=1`), per design.md's Open
 * Questions recommendation not to couple CI to a live API process.
 */
export default defineConfig({
  testDir: 'tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  grepInvert: process.env.RUN_REAL_API ? undefined : /@real-api/,
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'on-first-retry',
    // The app's i18n resolution order is ?lang= -> localStorage ->
    // navigator.languages -> 'es' (DD4). Without a fixed locale here,
    // CI/local runner OS defaults would leak into which language the suite
    // exercises by default and make assertions non-deterministic.
    locale: 'es-AR'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ],
  webServer: {
    command: 'npm run build && npm run preview -- --port 4173',
    url: 'http://localhost:4173',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      PUBLIC_API_BASE_URL: 'http://localhost:8000'
    }
  }
});
