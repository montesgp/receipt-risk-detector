<!--
  DESIGN.md §4.4 result priority item 6 "Analyzer and version details".
  Two reading speeds principle (§2.3): kept available for audit, not the
  first thing a beneficiary sees.
-->
<script lang="ts">
  import type { AnalyzerStatusModel } from '$lib/api/types';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  let {
    engineVersion,
    rulesetVersion,
    analyzerStatuses
  }: {
    engineVersion: string;
    rulesetVersion: string;
    analyzerStatuses: AnalyzerStatusModel[];
  } = $props();

  const i18n = getI18nContext();
</script>

<details class="rounded-ui border border-ui-line px-4 py-3">
  <summary class="cursor-pointer select-none font-medium">{i18n.t('result.technical.summary')}</summary>
  <dl class="my-3 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1">
    <dt class="text-ui-muted">{i18n.t('result.technical.engineVersion')}</dt>
    <dd class="m-0 font-mono text-sm"><code>{engineVersion}</code></dd>
    <dt class="text-ui-muted">{i18n.t('result.technical.rulesetVersion')}</dt>
    <dd class="m-0 font-mono text-sm"><code>{rulesetVersion}</code></dd>
  </dl>

  {#if analyzerStatuses.length > 0}
    <table class="w-full border-collapse text-sm">
      <thead>
        <tr>
          <th scope="col" class="border-b border-ui-line px-2 py-1 text-left">{i18n.t('result.technical.analyzerColumn')}</th>
          <th scope="col" class="border-b border-ui-line px-2 py-1 text-left">{i18n.t('result.technical.statusColumn')}</th>
          <th scope="col" class="border-b border-ui-line px-2 py-1 text-left">{i18n.t('result.technical.durationColumn')}</th>
        </tr>
      </thead>
      <tbody>
        {#each analyzerStatuses as analyzer (analyzer.analyzer)}
          <tr>
            <td class="border-b border-ui-line px-2 py-1 text-left">{analyzer.analyzer}</td>
            <td class="border-b border-ui-line px-2 py-1 text-left">{analyzer.status}</td>
            <td class="border-b border-ui-line px-2 py-1 text-left">{analyzer.duration_ms} ms</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</details>
