<!--
  DESIGN.md §5 "Result language": the mandatory reconciliation-limitation
  sentence, styled as an alert with an icon. ui-polish round 3 (issue #34):
  previously mounted unconditionally by +page.svelte in EVERY workspace
  state, which duplicated this exact sentence on screen whenever a result
  rendered (ResultView showed its own copy too). Now mounted ONLY inside
  ResultView, once a result exists -- idle/selected/uploading/error states
  no longer show it at all.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  const i18n = getI18nContext();
</script>

<div
  class="flex items-start gap-3 rounded-ui border border-ui-line bg-ui-surface p-4 text-sm text-ui-muted"
>
  <svg aria-hidden="true" viewBox="0 0 20 20" class="mt-0.5 h-5 w-5 shrink-0">
    <circle cx="10" cy="10" r="9" fill="none" stroke="currentColor" stroke-width="1.5" />
    <path d="M10 9v5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
    <circle cx="10" cy="6.5" r="1" fill="currentColor" />
  </svg>
  <p class="m-0 max-w-reading">{i18n.t('legal.disclaimer')}</p>
</div>
