<!--
  DESIGN.md §12 "Theme switcher UX": tri-state control (System · Light ·
  Dark), `aria-checked` semantics, focus ring via `--color-focus`, state
  change announced through an ARIA live region. Spec "Switchers are
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
-->
<script lang="ts">
  import { getThemeContext, type ThemeMode } from '$lib/theme/theme.svelte';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import LiveRegion from './LiveRegion.svelte';

  const controller = getThemeContext();
  const i18n = getI18nContext();

  const OPTIONS: { mode: ThemeMode; labelKey: string; icon: string }[] = [
    { mode: 'system', labelKey: 'theme.system', icon: '🖥' },
    { mode: 'light', labelKey: 'theme.light', icon: '☀' },
    { mode: 'dark', labelKey: 'theme.dark', icon: '🌙' }
  ];

  let announcement = $state('');

  const currentOption = $derived(
    OPTIONS.find((candidate) => candidate.mode === controller.mode) ?? OPTIONS[0]
  );
  const currentLabel = $derived(i18n.t(currentOption.labelKey));

  function select(mode: ThemeMode): void {
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
    const index = OPTIONS.findIndex((candidate) => candidate.mode === controller.mode);
    const nextIndex = (index + 1) % OPTIONS.length;
    select(OPTIONS[nextIndex].mode);
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
        aria-checked={controller.mode === option.mode}
        tabindex={controller.mode === option.mode ? 0 : -1}
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
