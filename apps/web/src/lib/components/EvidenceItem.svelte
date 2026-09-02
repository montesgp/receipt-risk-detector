<!--
  DESIGN.md §7 "Evidence list": each item shows severity, plain-language
  title (the server's `description`), confidence, and score contribution.
  Severity is communicated by text/icon, never color alone (§10).
-->
<script lang="ts">
  import type { SignalModel } from '$lib/api/types';

  let { signal }: { signal: SignalModel } = $props();

  const SEVERITY_LABEL: Record<string, string> = {
    info: 'Informativa',
    low: 'Baja',
    medium: 'Media',
    high: 'Alta',
    critical: 'Crítica'
  };

  const confidencePercent = $derived(Math.round(signal.confidence * 100));
</script>

<li class="evidence-item" data-code={signal.code}>
  <p class="evidence-item__severity">{SEVERITY_LABEL[signal.severity] ?? signal.severity}</p>
  <p class="evidence-item__description">{signal.description}</p>
  <dl class="evidence-item__meta">
    <dt>Confianza</dt>
    <dd>{confidencePercent}%</dd>
    <dt>Aporte al puntaje</dt>
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
