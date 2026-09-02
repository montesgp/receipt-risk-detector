<!--
  DESIGN.md §4.4 "Result" visual priority: (1) classification/risk,
  (2) confidence/limitation, (3) strongest evidence, (4) manual
  reconciliation action, (5) extracted data, (6) analyzer/version detail.
  Spec "Full result renders from the live response": the mandatory
  limitation disclaimer from `limitations[]` is always present, never
  omitted — falls back to the DESIGN.md §5 copy if the server sends none.
  Spec "No forbidden authenticity language appears" is enforced by every
  child component only using DESIGN.md §5-approved copy (never raw server
  text beyond `description`/`limitations`, which the API itself must keep
  compliant).
-->
<script lang="ts">
  import type { AnalyzeResponse } from '$lib/api/types';
  import ScoreSummary from './ScoreSummary.svelte';
  import EvidenceList from './EvidenceList.svelte';
  import ReconciliationChecklist from './ReconciliationChecklist.svelte';
  import ExtractedDataTable from './ExtractedDataTable.svelte';
  import TechnicalDetail from './TechnicalDetail.svelte';

  let { result }: { result: AnalyzeResponse } = $props();

  const FALLBACK_LIMITATION =
    'Este análisis evalúa el comprobante presentado. Confirmá la acreditación en la cuenta beneficiaria antes de entregar productos o servicios.';

  const limitations = $derived(result.limitations.length > 0 ? result.limitations : [FALLBACK_LIMITATION]);
</script>

<section class="result-view" aria-labelledby="result-heading">
  <h2 id="result-heading">Resultado del análisis</h2>

  <ScoreSummary
    classification={result.classification}
    riskScore={result.risk_score}
    confidenceScore={result.confidence_score}
    recommendedAction={result.recommended_action}
  />

  <div class="result-view__limitations">
    {#each limitations as limitation (limitation)}
      <p>{limitation}</p>
    {/each}
  </div>

  <section aria-labelledby="evidence-heading">
    <h3 id="evidence-heading">Evidencia principal</h3>
    <EvidenceList signals={result.signals} />
  </section>

  <section aria-labelledby="checklist-heading">
    <h3 id="checklist-heading">Checklist de conciliación manual</h3>
    <ReconciliationChecklist data={result.extracted_data} />
  </section>

  <section aria-labelledby="extracted-heading">
    <h3 id="extracted-heading">Datos extraídos</h3>
    <ExtractedDataTable data={result.extracted_data} />
  </section>

  <TechnicalDetail
    engineVersion={result.engine_version}
    rulesetVersion={result.ruleset_version}
    analyzerStatuses={result.analyzer_statuses}
  />
</section>

<style>
  .result-view {
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
  }

  .result-view__limitations {
    color: var(--color-text-muted);
    font-size: 0.875rem;
  }

  .result-view__limitations p {
    margin: 0;
  }
</style>
