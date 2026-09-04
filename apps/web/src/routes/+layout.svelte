<script lang="ts">
  import '../app.css';
  import { ThemeController, setThemeContext } from '$lib/theme/theme.svelte';
  import { I18n, setI18nContext } from '$lib/i18n/i18n.svelte';
  import ThemeSwitcher from '$lib/components/ThemeSwitcher.svelte';
  import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';

  let { children } = $props();

  // DESIGN.md §3 "Header": product identity + language/theme switchers,
  // present across idle/uploading/result/error — the layout wraps every
  // route. DESIGN.md §13 "Placement": language switcher sits left of the
  // theme switcher in the header right cluster.
  const theme = new ThemeController();
  setThemeContext(theme);

  const i18n = new I18n();
  setI18nContext(i18n);
</script>

<header class="border-b border-ui-line bg-ui-surface">
  <div class="mx-auto flex max-w-content items-center justify-between gap-4 px-4 py-4">
    <span class="flex items-center gap-2">
      <!-- ui-polish round 2, item 2: same mark as static/favicon.svg, but
           inline so it uses `currentColor` and adapts to the app's explicit
           light/dark toggle (not just OS preference, unlike the favicon
           file which has no access to `[data-theme]`). -->
      <svg
        viewBox="0 0 32 32"
        class="h-6 w-6 shrink-0 text-ui-fg"
        aria-hidden="true"
        fill="none"
        stroke="currentColor"
        stroke-width="2.75"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <rect x="5" y="5" width="14" height="18" rx="2.5" />
        <line x1="9" y1="11.5" x2="15" y2="11.5" />
        <line x1="9" y1="16.5" x2="15" y2="16.5" />
        <circle cx="22.5" cy="22.5" r="5.5" />
        <line x1="26.3" y1="26.3" x2="29.5" y2="29.5" />
      </svg>
      <span class="app-header__brand">Receipt Risk Detector</span>
    </span>
    <div class="app-header__switchers">
      <LanguageSwitcher />
      <ThemeSwitcher />
    </div>
  </div>
</header>

{@render children()}

<style>
  .app-header__brand {
    font-weight: 600;
  }

  .app-header__switchers {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
</style>
