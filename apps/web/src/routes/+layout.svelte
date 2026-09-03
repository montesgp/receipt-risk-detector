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

<header class="app-header">
  <div class="app-header__inner">
    <span class="app-header__brand">Receipt Risk Detector</span>
    <div class="app-header__switchers">
      <LanguageSwitcher />
      <ThemeSwitcher />
    </div>
  </div>
</header>

{@render children()}

<style>
  .app-header {
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface);
  }

  .app-header__inner {
    max-width: var(--content-max-width);
    margin: 0 auto;
    padding: var(--space-3) var(--space-4);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-4);
  }

  .app-header__brand {
    font-weight: 600;
  }

  .app-header__switchers {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
</style>
