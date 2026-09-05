<!--
  DESIGN.md §13 "Language switcher UX": single cycling button showing the
  active language's full name, with an `aria-label` describing the switch
  action. Spec "Switchers are keyboard-operable with visible focus" / "State
  change is announced and not color-only".

  The `I18n` controller is read from context (mirrors `ThemeSwitcher`'s
  pattern), set once by the layout via `setI18nContext`. Switching locale
  only flips which catalog `t()` reads from — it never re-uploads or
  re-calls the API (design.md "Result re-render on locale switch").

  Announcements go through the shared `LiveRegion.svelte`.

  ui-polish round 4 (issue TBD): replaced the ES/EN two-button pill with a
  single cycling button matching ThemeSwitcher's redesigned single-button
  shape -- the two identical pill controls sitting side by side read as a
  pair of generic on/off toggles. Shows the resolved language's full name
  (Español/English) rather than the two-letter code, for the same reason
  ThemeSwitcher shows "Claro"/"Oscuro" rather than an abbreviation.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import type { Locale } from '$lib/i18n/resolve';
  import LiveRegion from './LiveRegion.svelte';

  const i18n = getI18nContext();

  let announcement = $state('');

  function nameKey(locale: Locale): string {
    return locale === 'es' ? 'header.language.nameEs' : 'header.language.nameEn';
  }

  const currentLabel = $derived(i18n.t(nameKey(i18n.locale as Locale)));

  function select(locale: Locale): void {
    i18n.setLocale(locale);
    announcement = i18n.t('header.language.announcement', { language: i18n.t(nameKey(locale)) });
  }

  function cycle(): void {
    select(i18n.locale === 'es' ? 'en' : 'es');
  }
</script>

{#snippet globeIcon()}
  <svg viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="9" />
    <line x1="3" y1="12" x2="21" y2="12" />
    <path d="M12 3c3 3.5 3 14.5 0 18" />
    <path d="M12 3c-3 3.5-3 14.5 0 18" />
  </svg>
{/snippet}

<button
  type="button"
  class="language-switcher__cycle flex h-11 items-center gap-2 rounded-ui border border-ui-line bg-ui-surface px-3 text-sm text-ui-muted transition-colors hover:border-ui-muted hover:text-ui-fg"
  aria-label={i18n.t('header.language.cycleLabel', { label: currentLabel })}
  onclick={cycle}
>
  {@render globeIcon()}
  <span>{currentLabel}</span>
</button>
<LiveRegion message={announcement} />
