<!--
  DESIGN.md §4.2 "File selected": constrained preview, filename, type,
  human-readable size, replace/analyze actions. Never expose full financial
  identifiers here — this component only reflects the raw File metadata.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  let {
    file,
    onanalyze,
    onreplace
  }: { file: File; onanalyze: () => void; onreplace: () => void } = $props();

  const i18n = getI18nContext();

  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    const kb = bytes / 1024;
    if (kb < 1024) return `${Number(kb.toFixed(1))} KB`;
    return `${Number((kb / 1024).toFixed(1))} MB`;
  }

  // `URL.createObjectURL` is unavailable in jsdom (Vitest's test DOM); guard
  // so component tests don't need a global mock just to render metadata.
  const canPreview = typeof URL !== 'undefined' && typeof URL.createObjectURL === 'function';
  const previewUrl = $derived(canPreview ? URL.createObjectURL(file) : undefined);

  $effect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  });
</script>

<div class="flex flex-col gap-4 rounded-ui border border-ui-line bg-ui-surface p-6">
  {#if previewUrl}
    <img
      class="max-h-80 max-w-full rounded-ui object-contain"
      src={previewUrl}
      alt={i18n.t('upload.preview.imageAlt')}
    />
  {/if}
  <dl class="m-0 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1">
    <dt class="text-ui-muted">{i18n.t('upload.preview.name')}</dt>
    <dd class="m-0">{file.name}</dd>
    <dt class="text-ui-muted">{i18n.t('upload.preview.type')}</dt>
    <dd class="m-0">{file.type}</dd>
    <dt class="text-ui-muted">{i18n.t('upload.preview.size')}</dt>
    <dd class="m-0">{formatSize(file.size)}</dd>
  </dl>
  <div class="flex flex-wrap gap-3 pt-1">
    <button type="button" class="btn-primary" onclick={onanalyze}>{i18n.t('upload.preview.analyze')}</button>
    <button type="button" class="btn-secondary" onclick={onreplace}>{i18n.t('upload.preview.replace')}</button>
  </div>
</div>
