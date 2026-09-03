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
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import type { Locale } from '$lib/i18n/resolve';

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

<div class="language-switcher" role="group" aria-label={i18n.t('header.language.groupLabel')}>
  {#each OPTIONS as option (option.locale)}
    <button
      type="button"
      aria-pressed={i18n.locale === option.locale}
      aria-label={i18n.t(option.switchLabelKey)}
      onclick={() => select(option.locale)}
    >
      {option.label}
    </button>
  {/each}
</div>
<p class="visually-hidden" role="status" aria-live="polite">{announcement}</p>

<style>
  .language-switcher {
    display: inline-flex;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-1);
    background: var(--color-surface);
  }

  .language-switcher button {
    border: none;
    background: transparent;
    color: var(--color-text);
    padding: var(--space-1) var(--space-2);
    border-radius: calc(var(--radius) - 4px);
    cursor: pointer;
    font: inherit;
    min-height: 32px;
  }

  .language-switcher button[aria-pressed='true'] {
    background: var(--color-action);
    color: var(--color-action-text);
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
