<!--
  DESIGN.md §7 "Evidence list": order by severity then score impact.
  Spec "Full result renders from the live response": ordered evidence
  (`signals` by severity).
-->
<script lang="ts">
  import type { SignalModel } from '$lib/api/types';
  import EvidenceItem from './EvidenceItem.svelte';

  let { signals }: { signals: SignalModel[] } = $props();

  const SEVERITY_RANK: Record<string, number> = {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
    info: 0
  };

  const sorted = $derived(
    [...signals].sort((a, b) => {
      const rankDiff = (SEVERITY_RANK[b.severity] ?? -1) - (SEVERITY_RANK[a.severity] ?? -1);
      if (rankDiff !== 0) return rankDiff;
      return b.score_contribution - a.score_contribution;
    })
  );
</script>

{#if sorted.length > 0}
  <ul class="evidence-list">
    {#each sorted as signal (signal.code + signal.category)}
      <EvidenceItem {signal} />
    {/each}
  </ul>
{:else}
  <p class="evidence-list__empty">No se registraron señales de riesgo para este comprobante.</p>
{/if}

<style>
  .evidence-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .evidence-list__empty {
    color: var(--color-text-muted);
  }
</style>
