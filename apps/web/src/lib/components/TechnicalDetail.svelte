<!--
  DESIGN.md §4.4 result priority item 6 "Analyzer and version details".
  Two reading speeds principle (§2.3): kept available for audit, not the
  first thing a beneficiary sees.
-->
<script lang="ts">
  import type { AnalyzerStatusModel } from '$lib/api/types';

  let {
    engineVersion,
    rulesetVersion,
    analyzerStatuses
  }: {
    engineVersion: string;
    rulesetVersion: string;
    analyzerStatuses: AnalyzerStatusModel[];
  } = $props();
</script>

<details class="technical-detail">
  <summary>Detalle técnico</summary>
  <dl class="technical-detail__versions">
    <dt>Versión del motor</dt>
    <dd><code>{engineVersion}</code></dd>
    <dt>Versión del conjunto de reglas</dt>
    <dd><code>{rulesetVersion}</code></dd>
  </dl>

  {#if analyzerStatuses.length > 0}
    <table class="technical-detail__analyzers">
      <thead>
        <tr>
          <th scope="col">Analizador</th>
          <th scope="col">Estado</th>
          <th scope="col">Duración</th>
        </tr>
      </thead>
      <tbody>
        {#each analyzerStatuses as analyzer (analyzer.analyzer)}
          <tr>
            <td>{analyzer.analyzer}</td>
            <td>{analyzer.status}</td>
            <td>{analyzer.duration_ms} ms</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</details>

<style>
  .technical-detail {
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-3) var(--space-4);
  }

  .technical-detail__versions {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: var(--space-1) var(--space-2);
    margin: var(--space-3) 0;
  }

  .technical-detail__versions dt {
    color: var(--color-text-muted);
  }

  .technical-detail__versions dd {
    margin: 0;
    font-family: var(--font-mono);
    font-size: 0.875rem;
  }

  .technical-detail__analyzers {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .technical-detail__analyzers th,
  .technical-detail__analyzers td {
    text-align: left;
    padding: var(--space-1) var(--space-2);
    border-bottom: 1px solid var(--color-border);
  }
</style>
