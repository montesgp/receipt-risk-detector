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

<div class="file-preview">
  {#if previewUrl}
    <img class="file-preview__image" src={previewUrl} alt={i18n.t('upload.preview.imageAlt')} />
  {/if}
  <dl class="file-preview__meta">
    <dt>{i18n.t('upload.preview.name')}</dt>
    <dd>{file.name}</dd>
    <dt>{i18n.t('upload.preview.type')}</dt>
    <dd>{file.type}</dd>
    <dt>{i18n.t('upload.preview.size')}</dt>
    <dd>{formatSize(file.size)}</dd>
  </dl>
  <div class="file-preview__actions">
    <button type="button" onclick={onanalyze}>{i18n.t('upload.preview.analyze')}</button>
    <button type="button" onclick={onreplace}>{i18n.t('upload.preview.replace')}</button>
  </div>
</div>

<style>
  .file-preview {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-4);
    background: var(--color-surface);
  }

  .file-preview__image {
    max-width: 100%;
    max-height: 320px;
    object-fit: contain;
    border-radius: var(--radius);
  }

  .file-preview__meta {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-1) var(--space-2);
    margin: 0;
  }

  .file-preview__meta dt {
    color: var(--color-text-muted);
  }

  .file-preview__meta dd {
    margin: 0;
  }

  .file-preview__actions {
    display: flex;
    gap: var(--space-2);
  }
</style>
