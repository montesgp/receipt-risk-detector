<!--
  DESIGN.md §13 "Language switcher UX": two-option control labelled `ES` /
  `EN`, each with an `aria-label` in its own language, placed in the header
  right cluster left of the theme switcher. Spec "Switchers are
  keyboard-operable with visible focus" / "State change is announced and
  not color-only".

  The `I18n` controller is read from context (mirrors `ThemeSwitcher`'s
  pattern), set once by the layout via `setI18nContext`. Switching locale
  only flips which catalog `t()` reads from — it never re-uploads or
  re-calls the API (design.md "Result re-render on locale switch").

  Announcements go through the shared `LiveRegion.svelte` (slice 4) — slice
  3a used a local `role="status"` workaround because that component did not
  exist yet.

  ui-polish round 2, item 5: migrated the scoped `<style>` block to Tailwind
  utilities (matching ThemeSwitcher and the rest of the app) and shrunk the
  visual footprint — smaller pill, tighter padding. No structural/ARIA
  change, so the existing test suite is untouched.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import type { Locale } from '$lib/i18n/resolve';
  import LiveRegion from './LiveRegion.svelte';

  const i18n = getI18nContext();

  const OPTIONS: { locale: Locale; label: string; switchLabelKey: string }[] = [
    { locale: 'es', label: 'ES', switchLabelKey: 'header.language.switchToEs' },
    { locale: 'en', label: 'EN', switchLabelKey: 'header.language.switchToEn' }
  ];

  let announcement = $state('');

  function select(locale: Locale): void {
    i18n.setLocale(locale);
    const languageName = i18n.t(locale === 'es' ? 'header.language.nameEs' : 'header.language.nameEn');
    announcement = i18n.t('header.language.announcement', { language: languageName });
  }
</script>

<div
  class="inline-flex items-center gap-0.5 rounded-full border border-ui-line p-0.5"
  role="group"
  aria-label={i18n.t('header.language.groupLabel')}
>
  {#each OPTIONS as option (option.locale)}
    <button
      type="button"
      aria-pressed={i18n.locale === option.locale}
      aria-label={i18n.t(option.switchLabelKey)}
      class="flex h-8 min-w-8 items-center justify-center rounded-full px-2 text-xs font-semibold transition-colors"
      class:bg-ui-action={i18n.locale === option.locale}
      class:text-ui-action-fg={i18n.locale === option.locale}
      class:bg-transparent={i18n.locale !== option.locale}
      class:text-ui-muted={i18n.locale !== option.locale}
      onclick={() => select(option.locale)}
    >
      {option.label}
    </button>
  {/each}
</div>
<LiveRegion message={announcement} />
