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

<li class="evidence-item" data-code={signal.code}>
  <p class="evidence-item__severity">{severityLabel}</p>
  <p class="evidence-item__description">{signal.description}</p>
  <dl class="evidence-item__meta">
    <dt>{i18n.t('evidence.confidenceLabel')}</dt>
    <dd>{confidencePercent}%</dd>
    <dt>{i18n.t('evidence.scoreContributionLabel')}</dt>
    <dd>{signal.score_contribution}</dd>
  </dl>
</li>

<style>
  .evidence-item {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
    padding: var(--space-3) 0;
    border-bottom: 1px solid var(--color-border);
  }

  .evidence-item:last-child {
    border-bottom: none;
  }

  .evidence-item__severity {
    margin: 0;
    font-size: 0.8125rem;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--color-text-muted);
  }

  .evidence-item__description {
    margin: 0;
  }

  .evidence-item__meta {
    display: flex;
    gap: var(--space-4);
    margin: 0;
  }

  .evidence-item__meta dt {
    color: var(--color-text-muted);
  }
</style>
