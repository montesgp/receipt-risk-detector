<!--
  DESIGN.md §4.5 "Error": explain what the user can do next, preserve the
  file in memory only when retry is safe, never a raw stack trace or tool
  error. Spec "Service-unavailable / connectivity error state": network
  failure must never look like a result. Spec "Rate-limit (429) handling":
  the client MUST NOT auto-resubmit before Retry-After elapses, so the retry
  action stays disabled until then.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  type Variant = 'network' | 'timeout' | 'rate-limited' | 'rejected-file';

  let {
    variant,
    code,
    retryAfterSeconds,
    onretry
  }: {
    variant: Variant;
    code?: string;
    retryAfterSeconds?: number;
    onretry: () => void;
  } = $props();

  const i18n = getI18nContext();

  // Every message here is authored copy, never `detail`/a stack trace, per
  // the "Server-side validation error is explained" spec scenario.
  const REJECTED_FILE_MESSAGE_KEYS: Record<string, string> = {
    MISSING_FILE: 'errors.rejectedFile.missingFile',
    FILE_TOO_LARGE: 'errors.rejectedFile.fileTooLarge',
    UNSUPPORTED_IMAGE: 'errors.rejectedFile.unsupportedImage',
    IMAGE_DIMENSIONS_EXCEEDED: 'errors.rejectedFile.imageDimensionsExceeded',
    MALFORMED_RESPONSE: 'errors.rejectedFile.malformedResponse'
  };

  const message = $derived.by(() => {
    if (variant === 'network') return i18n.t('errors.network');
    if (variant === 'timeout') return i18n.t('errors.timeout');
    if (variant === 'rate-limited') {
      const wait =
        retryAfterSeconds !== undefined
          ? i18n.t('errors.rateLimited.waitSeconds', { seconds: retryAfterSeconds })
          : i18n.t('errors.rateLimited.waitGeneric');
      return `${i18n.t('errors.rateLimited.prefix')} ${wait}`;
    }
    const key = code && REJECTED_FILE_MESSAGE_KEYS[code];
    return i18n.t(key ?? 'errors.rejectedFile.generic');
  });

  const retryDisabled = $derived(variant === 'rate-limited' && retryAfterSeconds !== undefined);

  // Slice 4 focus management: `+page.svelte` mounts a fresh `ErrorPanel` per
  // failed attempt. Moving focus to the alert itself (rather than leaving it
  // on the now-removed drop zone/analyze button, or resetting to the page
  // top) means a screen-reader user lands directly on the actionable
  // message instead of having to relocate it after the DOM changed under
  // them.
  let panelEl: HTMLDivElement | undefined;

  $effect(() => {
    panelEl?.focus();
  });
</script>

<div class="error-panel" role="alert" bind:this={panelEl} tabindex="-1">
  <p class="error-panel__message">{message}</p>
  <button type="button" onclick={onretry} disabled={retryDisabled}>{i18n.t('common.retry')}</button>
</div>

<style>
  .error-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    border: 1px solid var(--color-risk-high);
    border-radius: var(--radius);
    padding: var(--space-4);
    background: var(--color-surface);
  }

  .error-panel:focus-visible {
    outline: 2px solid var(--color-focus);
    outline-offset: 2px;
  }

  .error-panel__message {
    margin: 0;
  }
</style>
