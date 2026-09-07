<!--
  DESIGN.md §12 "Theme switcher UX": single cycling icon button with a
  visible current-state label, state change announced through an ARIA live
  region. Spec "Switchers are keyboard-operable with visible focus" / "State
  change is announced and not color-only".

  The controller is read from context (design.md: "lib/theme ... provided
  through Svelte context"), set once by the layout via `setThemeContext`.
  Announcements go through the shared `LiveRegion.svelte`.

  ui-design-refresh slice 3 fix: `controller.mode` stays 'system' until the
  user makes an explicit choice (ThemeController is untouched), so the
  button's current-state label derives from `controller.resolved` (always
  'light' | 'dark') instead of `mode` — otherwise a dark-first-paint via OS
  preference would incorrectly show "Light". `theme.system` stays in both
  message files for `ThemeMode`/i18n key-parity but is never rendered.

  ui-polish round 2/3: swapped platform emoji for monochrome sun/moon
  line-icons (Lucide/Feather-style paths), stroked with `currentColor`.

  ui-polish round 4 (issue TBD): dropped the >=768px segmented
  radiogroup variant entirely -- it read as a generic on/off toggle next to
  the language switcher's identical pill shape. A single cycling button
  (previously the <768px-only variant) is now used at every width, matching
  LanguageSwitcher's own single-button redesign. `.theme-switcher__cycle` is
  kept as a test-selector hook only.
-->
<script lang="ts">
  import { getThemeContext } from '$lib/theme/theme.svelte';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import LiveRegion from './LiveRegion.svelte';

  const controller = getThemeContext();
  const i18n = getI18nContext();

  const OPTIONS: { mode: 'light' | 'dark'; labelKey: string }[] = [
    { mode: 'light', labelKey: 'theme.light' },
    { mode: 'dark', labelKey: 'theme.dark' }
  ];

  let announcement = $state('');

  const active = $derived(controller.resolved);
  const currentOption = $derived(OPTIONS.find((option) => option.mode === active) ?? OPTIONS[0]);
  const currentLabel = $derived(i18n.t(currentOption.labelKey));

  function select(mode: 'light' | 'dark'): void {
    controller.setTheme(mode);
    const option = OPTIONS.find((candidate) => candidate.mode === mode);
    const label = option ? i18n.t(option.labelKey) : mode;
    announcement = i18n.t('theme.announcement', { label });
  }

  function cycle(): void {
    select(active === 'light' ? 'dark' : 'light');
  }
</script>

{#snippet sunIcon()}
  <svg viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="4" />
    <line x1="12" y1="2" x2="12" y2="4.5" />
    <line x1="12" y1="19.5" x2="12" y2="22" />
    <line x1="2" y1="12" x2="4.5" y2="12" />
    <line x1="19.5" y1="12" x2="22" y2="12" />
    <line x1="4.93" y1="4.93" x2="6.64" y2="6.64" />
    <line x1="17.36" y1="17.36" x2="19.07" y2="19.07" />
    <line x1="4.93" y1="19.07" x2="6.64" y2="17.36" />
    <line x1="17.36" y1="6.64" x2="19.07" y2="4.93" />
  </svg>
{/snippet}

{#snippet moonIcon()}
  <svg viewBox="0 0 24 24" class="h-[18px] w-[18px]" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M20.5 14.5A8.5 8.5 0 1 1 9.5 3.5a7 7 0 0 0 11 11z" />
  </svg>
{/snippet}

<button
  type="button"
  class="theme-switcher__cycle flex h-11 items-center gap-2 rounded-ui border border-ui-line bg-ui-surface px-3 text-sm text-ui-muted transition-colors hover:border-ui-muted hover:text-ui-fg"
  aria-label={i18n.t('theme.cycleLabel', { label: currentLabel })}
  onclick={cycle}
>
  {@render (currentOption.mode === 'light' ? sunIcon : moonIcon)()}
  <span>{currentLabel}</span>
</button>
<LiveRegion message={announcement} />
