<script lang="ts">
  import '../app.css';
  import { ThemeController, setThemeContext } from '$lib/theme/theme.svelte';
  import ThemeSwitcher from '$lib/components/ThemeSwitcher.svelte';

  let { children } = $props();

  // DESIGN.md §3 "Header": product identity + theme switcher, present
  // across idle/uploading/result/error — the layout wraps every route.
  const theme = new ThemeController();
  setThemeContext(theme);
</script>

<header class="app-header">
  <div class="app-header__inner">
    <span class="app-header__brand">Receipt Risk Detector</span>
    <ThemeSwitcher />
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
</style>
