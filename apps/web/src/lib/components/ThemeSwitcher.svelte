<!--
  DESIGN.md §12 "Theme switcher UX": tri-state control (System · Light ·
  Dark), `aria-checked` semantics, focus ring via `--color-focus`, state
  change announced through an ARIA live region. Spec "Switchers are
  keyboard-operable with visible focus" / "State change is announced and
  not color-only".

  The controller is read from context (design.md: "lib/theme ... provided
  through Svelte context"), set once by the layout via `setThemeContext`.
  A local `role="status"` live region is used because the shared
  `LiveRegion.svelte` component is slice 4 scope and does not exist yet.
-->
<script lang="ts">
  import { getThemeContext, type ThemeMode } from '$lib/theme/theme.svelte';

  const controller = getThemeContext();

  const OPTIONS: { mode: ThemeMode; label: string }[] = [
    { mode: 'system', label: 'Sistema' },
    { mode: 'light', label: 'Claro' },
    { mode: 'dark', label: 'Oscuro' }
  ];

  let announcement = $state('');

  function select(mode: ThemeMode): void {
    controller.setTheme(mode);
    const option = OPTIONS.find((candidate) => candidate.mode === mode);
    announcement = `Tema: ${option?.label ?? mode}`;
  }

  function handleKeydown(event: KeyboardEvent, index: number): void {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
    event.preventDefault();
    const delta = event.key === 'ArrowRight' ? 1 : -1;
    const nextIndex = (index + delta + OPTIONS.length) % OPTIONS.length;
    select(OPTIONS[nextIndex].mode);
  }
</script>

<div class="theme-switcher" role="radiogroup" aria-label="Tema">
  {#each OPTIONS as option, index (option.mode)}
    <button
      type="button"
      role="radio"
      aria-checked={controller.mode === option.mode}
      tabindex={controller.mode === option.mode ? 0 : -1}
      onclick={() => select(option.mode)}
      onkeydown={(event) => handleKeydown(event, index)}
    >
      {option.label}
    </button>
  {/each}
</div>
<p class="visually-hidden" role="status" aria-live="polite">{announcement}</p>

<style>
  .theme-switcher {
    display: inline-flex;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-1);
    background: var(--color-surface);
  }

  .theme-switcher button {
    border: none;
    background: transparent;
    color: var(--color-text);
    padding: var(--space-1) var(--space-2);
    border-radius: calc(var(--radius) - 4px);
    cursor: pointer;
    font: inherit;
    min-height: 32px;
  }

  .theme-switcher button[aria-checked='true'] {
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
