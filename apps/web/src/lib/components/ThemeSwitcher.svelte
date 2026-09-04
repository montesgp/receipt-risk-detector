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

  ui-polish round 3: swapped the platform emoji (☀/🌙, which render
  inconsistently across OS/browser emoji fonts and read as childish next to
  the rest of the monochrome brand) for the same sun/moon line-icon pair
  used by most dark-mode toggles (Lucide/Feather-style paths), stroked with
  `currentColor` to match the navbar mark's line weight.
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
        class="flex h-11 w-11 items-center justify-center rounded-full transition-colors"
        class:bg-ui-action={active === option.mode}
        class:text-ui-action-fg={active === option.mode}
        class:bg-transparent={active !== option.mode}
        class:text-ui-muted={active !== option.mode}
        onclick={() => select(option.mode)}
        onkeydown={(event) => handleKeydown(event, index)}
      >
        {@render (option.mode === 'light' ? sunIcon : moonIcon)()}
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
    {@render (currentOption.mode === 'light' ? sunIcon : moonIcon)()}
    <!-- DESIGN.md §12: "a cycling icon button with a visible current-state
         label" — state must be conveyed as visible text, not only via
         aria-label. Kept minimal (small text, no extra chrome). -->
    <span>{currentLabel}</span>
  </button>
</div>
<LiveRegion message={announcement} />
