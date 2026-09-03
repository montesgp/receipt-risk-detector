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
    <span class="app-header__brand">Receipt Risk Detector</span>
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
