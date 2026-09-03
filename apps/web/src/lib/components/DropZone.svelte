<!--
  DESIGN.md §4.1/§7 "Drop zone": the entire area is clickable and keyboard
  reachable, drag/drop always has a native file-picker equivalent (§10
  accessibility), and the zone never fabricates a busy/loading look while
  idle. Validation is left entirely to the caller (AnalysisWorkspace) — this
  component only reports the raw picked/dropped File.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  let { disabled = false, onselect }: { disabled?: boolean; onselect: (file: File) => void } =
    $props();

  const i18n = getI18nContext();

  let inputEl: HTMLInputElement | undefined;
  let isDragOver = $state(false);

  function openPicker(): void {
    if (disabled) return;
    inputEl?.click();
  }

  function onKeydown(event: KeyboardEvent): void {
    if (disabled) return;
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openPicker();
    }
  }

  function onInputChange(event: Event): void {
    if (disabled) return;
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (file) onselect(file);
  }

  function onDrop(event: DragEvent): void {
    event.preventDefault();
    isDragOver = false;
    if (disabled) return;
    const file = event.dataTransfer?.files?.[0];
    if (file) onselect(file);
  }

  function onDragOver(event: DragEvent): void {
    event.preventDefault();
    if (disabled) return;
    isDragOver = true;
  }

  function onDragLeave(): void {
    isDragOver = false;
  }
</script>

<div
  class="drop-zone"
  class:drop-zone--drag={isDragOver}
  role="button"
  tabindex="0"
  aria-disabled={disabled}
  onclick={openPicker}
  onkeydown={onKeydown}
  ondrop={onDrop}
  ondragover={onDragOver}
  ondragleave={onDragLeave}
>
  <p class="drop-zone__heading">{i18n.t('upload.dropzone.heading')}</p>
  <p class="drop-zone__constraints">{i18n.t('upload.dropzone.constraints')}</p>
  <input
    bind:this={inputEl}
    id="receipt-file"
    type="file"
    accept="image/png,image/jpeg,image/webp"
    disabled={disabled}
    onchange={onInputChange}
    tabindex="-1"
  />
</div>

<style>
  .drop-zone {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-2);
    border: 2px dashed var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-8) var(--space-4);
    text-align: center;
    cursor: pointer;
    background: var(--color-surface);
  }

  .drop-zone[aria-disabled='true'] {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .drop-zone--drag {
    border-color: var(--color-focus);
  }

  .drop-zone__heading {
    font-weight: 600;
    margin: 0;
  }

  .drop-zone__constraints {
    color: var(--color-text-muted);
    margin: 0;
  }

  input[type='file'] {
    /* Native input stays in the DOM (accessible fallback) but is visually
       hidden; the zone itself owns the click/keyboard affordance. */
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
</style>
