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
  class="flex flex-col items-center gap-2 rounded-ui border-2 border-dashed border-ui-line bg-ui-surface px-4 py-8 text-center cursor-pointer transition-colors duration-150 hover:border-ui-muted aria-disabled:cursor-not-allowed aria-disabled:opacity-60"
  class:border-ui-focus={isDragOver}
  role="button"
  tabindex="0"
  aria-disabled={disabled}
  onclick={openPicker}
  onkeydown={onKeydown}
  ondrop={onDrop}
  ondragover={onDragOver}
  ondragleave={onDragLeave}
>
  <p class="m-0 text-lg font-semibold">{i18n.t('upload.dropzone.heading')}</p>
  <p class="m-0 text-ui-muted">{i18n.t('upload.dropzone.constraints')}</p>
  <input
    bind:this={inputEl}
    id="receipt-file"
    type="file"
    accept="image/png,image/jpeg,image/webp"
    disabled={disabled}
    onchange={onInputChange}
    tabindex="-1"
    class="sr-only"
  />
</div>
