<!--
  DESIGN.md §12 "Theme switcher UX": binary control (Light · Dark),
  `aria-checked` semantics, focus ring via `--color-focus`, state change
  announced through an ARIA live region. Spec "Switchers are
  keyboard-operable with visible focus" / "State change is announced and
  not color-only".

  The controller is read from context (design.md: "lib/theme ... provided
  through Svelte context"), set once by the layout via `setThemeContext`.
  Announcements go through the shared `LiveRegion.svelte` (slice 4) — slice 2
  used a local `role="status"` workaround because that component did not
  exist yet.

  Slice 4 fix (verify follow-up from slice 2): DESIGN.md §12's "Control" row
  requires a segmented control at >=768px and a cycling icon button with a
  visible current-state label below 768px, both with a >=44x44px touch
  target. Both variants are always in the DOM and toggled purely by CSS
  media query — no JS `matchMedia`/resize listener needed, so it works
  before hydration and needs no extra state. A hidden variant is inert to
  assistive tech (removed from the accessibility tree by `display: none`),
  so there is exactly one reachable control at any viewport width.

  ui-design-refresh slice 3 fix: `controller.mode` stays 'system' until the
  user makes an explicit choice (ThemeController is untouched), so a binary
  control's checked/current state derives from `controller.resolved` (always
  'light' | 'dark') instead of `mode` — otherwise a dark-first-paint via OS
  preference would incorrectly render "Light" as checked. `theme.system`
  stays in both message files for `ThemeMode`/i18n key-parity but is never
  rendered as a selectable option.
-->
<script lang="ts">
  import { getThemeContext } from '$lib/theme/theme.svelte';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import LiveRegion from './LiveRegion.svelte';

  const controller = getThemeContext();
  const i18n = getI18nContext();

  const OPTIONS: { mode: 'light' | 'dark'; labelKey: string; icon: string }[] = [
    { mode: 'light', labelKey: 'theme.light', icon: '☀' },
    { mode: 'dark', labelKey: 'theme.dark', icon: '🌙' }
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

  function handleKeydown(event: KeyboardEvent, index: number): void {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
    event.preventDefault();
    const delta = event.key === 'ArrowRight' ? 1 : -1;
    const nextIndex = (index + delta + OPTIONS.length) % OPTIONS.length;
    select(OPTIONS[nextIndex].mode);
  }

  function cycle(): void {
    select(active === 'light' ? 'dark' : 'light');
  }
</script>

<div class="theme-switcher">
  <div
    class="theme-switcher__segmented"
    role="radiogroup"
    aria-label={i18n.t('theme.groupLabel')}
  >
    {#each OPTIONS as option, index (option.mode)}
      <button
        type="button"
        role="radio"
        aria-checked={active === option.mode}
        tabindex={active === option.mode ? 0 : -1}
        onclick={() => select(option.mode)}
        onkeydown={(event) => handleKeydown(event, index)}
      >
        {i18n.t(option.labelKey)}
      </button>
    {/each}
  </div>

  <button
    type="button"
    class="theme-switcher__cycle"
    aria-label={i18n.t('theme.cycleLabel', { label: currentLabel })}
    onclick={cycle}
  >
    <span aria-hidden="true">{currentOption.icon}</span>
    <span>{currentLabel}</span>
  </button>
</div>
<LiveRegion message={announcement} />

<style>
  .theme-switcher {
    display: inline-flex;
    align-items: center;
  }

  .theme-switcher__segmented {
    display: none;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-1);
    background: var(--color-surface);
  }

  .theme-switcher__segmented button {
    border: none;
    background: transparent;
    color: var(--color-text);
    padding: var(--space-1) var(--space-2);
    border-radius: calc(var(--radius) - 4px);
    cursor: pointer;
    font: inherit;
    min-width: 44px;
    min-height: 44px;
  }

  .theme-switcher__segmented button[aria-checked='true'] {
    background: var(--color-action);
    color: var(--color-action-text);
  }

  .theme-switcher__cycle {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-1) var(--space-2);
    background: var(--color-surface);
    color: var(--color-text);
    cursor: pointer;
    font: inherit;
    min-width: 44px;
    min-height: 44px;
  }

  /* DESIGN.md §12: segmented control at >=768px, cycling icon button below. */
  @media (min-width: 768px) {
    .theme-switcher__segmented {
      display: inline-flex;
    }

    .theme-switcher__cycle {
      display: none;
    }
  }
</style>
