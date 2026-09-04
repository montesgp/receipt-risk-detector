<!--
  DESIGN.md §7 "Evidence list": each item shows severity, plain-language
  title (the server's `description`), confidence, and score contribution.
  Severity is communicated by text/icon, never color alone (§10).
-->
<script lang="ts">
  import type { SignalModel } from '$lib/api/types';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import { severityKey } from '$lib/i18n/enum-map';

  let { signal }: { signal: SignalModel } = $props();

  const i18n = getI18nContext();

  const confidencePercent = $derived(Math.round(signal.confidence * 100));
  const severityLabel = $derived.by(() => {
    const key = severityKey(signal.severity);
    return key ? i18n.t(key) : signal.severity;
  });
</script>

<li
  class="evidence-item flex flex-col gap-2 border-b border-ui-line px-1 py-4 last:border-b-0"
  data-code={signal.code}
>
  <p class="m-0 text-[0.8125rem] font-semibold uppercase tracking-wide text-ui-muted">{severityLabel}</p>
  <p class="m-0 max-w-reading">{signal.description}</p>
  <dl class="m-0 mt-1 flex flex-wrap gap-x-6 gap-y-1">
    <dt class="text-ui-muted">{i18n.t('evidence.confidenceLabel')}</dt>
    <dd>{confidencePercent}%</dd>
    <dt class="text-ui-muted">{i18n.t('evidence.scoreContributionLabel')}</dt>
    <dd>{signal.score_contribution}</dd>
  </dl>
</li>
