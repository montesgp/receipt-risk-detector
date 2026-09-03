<!--
  DESIGN.md §7 "Evidence list": order by severity then score impact.
  Spec "Full result renders from the live response": ordered evidence
  (`signals` by severity).
-->
<script lang="ts">
  import type { SignalModel } from '$lib/api/types';
  import EvidenceItem from './EvidenceItem.svelte';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  let { signals }: { signals: SignalModel[] } = $props();

  const i18n = getI18nContext();

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
  <ul class="m-0 list-none p-0">
    {#each sorted as signal (signal.code + signal.category)}
      <EvidenceItem {signal} />
    {/each}
  </ul>
{:else}
  <p class="m-0 text-ui-muted">{i18n.t('evidence.empty')}</p>
{/if}
