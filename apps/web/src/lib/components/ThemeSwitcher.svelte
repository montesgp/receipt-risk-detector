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

  ui-polish round 2, item 5: restyled to a compact icon-only control (label
  kept as visually-hidden text, so the accessible name/`aria-checked`
  semantics and the existing test suite are untouched) and migrated the
  scoped `<style>` block to Tailwind utilities, matching the rest of the
  app since the Tailwind adoption slice. `.theme-switcher__segmented` /
  `.theme-switcher__cycle` class names are kept as test selector hooks
  only — all visual styling now lives in the Tailwind classes alongside
  them. The >=44px touch target is preserved via `h-11 w-11` (44px).
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

<div class="inline-flex items-center">
  <div
    class="theme-switcher__segmented hidden items-center gap-0.5 rounded-full border border-ui-line p-0.5 md:inline-flex"
    role="radiogroup"
    aria-label={i18n.t('theme.groupLabel')}
  >
    {#each OPTIONS as option, index (option.mode)}
      <button
        type="button"
        role="radio"
        aria-checked={active === option.mode}
        tabindex={active === option.mode ? 0 : -1}
        class="flex h-11 w-11 items-center justify-center rounded-full text-base transition-colors"
        class:bg-ui-action={active === option.mode}
        class:text-ui-action-fg={active === option.mode}
        class:bg-transparent={active !== option.mode}
        class:text-ui-muted={active !== option.mode}
        onclick={() => select(option.mode)}
        onkeydown={(event) => handleKeydown(event, index)}
      >
        <span aria-hidden="true">{option.icon}</span>
        <span class="sr-only">{i18n.t(option.labelKey)}</span>
      </button>
    {/each}
  </div>

  <button
    type="button"
    class="theme-switcher__cycle flex h-11 min-w-11 items-center justify-center gap-1.5 rounded-full border border-ui-line bg-ui-surface px-3 text-sm text-ui-muted transition-colors hover:text-ui-fg md:hidden"
    aria-label={i18n.t('theme.cycleLabel', { label: currentLabel })}
    onclick={cycle}
  >
    <span aria-hidden="true">{currentOption.icon}</span>
    <!-- DESIGN.md §12: "a cycling icon button with a visible current-state
         label" — state must be conveyed as visible text, not only via
         aria-label. Kept minimal (small text, no extra chrome). -->
    <span>{currentLabel}</span>
  </button>
</div>
<LiveRegion message={announcement} />
