<!--
  DESIGN.md §4.4 "Result" visual priority: (1) classification/risk,
  (2) confidence/limitation, (3) strongest evidence, (4) manual
  reconciliation action, (5) extracted data, (6) analyzer/version detail.

  Locale fix (slice 3a): this view intentionally never renders the server's
  raw `limitations[]` strings. `apps/api`'s `LIMITATION_STATEMENT` is a
  hardcoded English constant (`domain/assessment.py`), so displaying it
  verbatim would show English text inside an otherwise Spanish/bilingual
  frontend regardless of the user's chosen locale — the backend has no
  concept of the client's locale and is out of scope for this change. The
  mandatory disclaimer is instead always the client's own copy (identical
  Spanish text to `ReconciliationNotice.svelte`, which already renders it
  unconditionally in idle/result per DD7), so the sentence the user sees is
  always in a locale the client actually controls. It will move behind
  `t('legal.disclaimer')` in slice 3b along with every other literal in
  this component. Spec "No forbidden authenticity language appears" is
  enforced by every child component only using DESIGN.md §5-approved copy.
-->
<script lang="ts">
  import type { AnalyzeResponse } from '$lib/api/types';
  import ScoreSummary from './ScoreSummary.svelte';
  import EvidenceList from './EvidenceList.svelte';
  import ReconciliationChecklist from './ReconciliationChecklist.svelte';
  import ExtractedDataTable from './ExtractedDataTable.svelte';
  import TechnicalDetail from './TechnicalDetail.svelte';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  let { result }: { result: AnalyzeResponse } = $props();

  const i18n = getI18nContext();

  // Slice 4 focus management: `+page.svelte` mounts a fresh `ResultView`
  // per successful analysis, replacing the drop zone/processing UI. Without
  // this, keyboard/screen-reader focus stays on whatever element it was on
  // before submission (or resets to the document body), which is now
  // irrelevant. Moving focus to the result heading orients the user at the
  // start of the new content instead.
  let headingEl: HTMLHeadingElement | undefined;

  $effect(() => {
    headingEl?.focus();
  });
</script>

<section class="flex flex-col gap-8" aria-labelledby="result-heading">
  <h2 id="result-heading" bind:this={headingEl} tabindex="-1" class="m-0 text-2xl font-semibold">
    {i18n.t('result.heading')}
  </h2>

  <ScoreSummary
    classification={result.classification}
    riskScore={result.risk_score}
    confidenceScore={result.confidence_score}
    recommendedAction={result.recommended_action}
  />

  <div class="max-w-reading text-sm text-ui-muted">
    <p class="m-0">{i18n.t('legal.disclaimer')}</p>
  </div>

  <section aria-labelledby="evidence-heading">
    <h3 id="evidence-heading" class="m-0 mb-3 text-lg font-semibold">{i18n.t('result.evidenceHeading')}</h3>
    <EvidenceList signals={result.signals} />
  </section>

  <section aria-labelledby="checklist-heading">
    <h3 id="checklist-heading" class="m-0 mb-3 text-lg font-semibold">{i18n.t('result.checklistHeading')}</h3>
    <ReconciliationChecklist data={result.extracted_data} />
  </section>

  <section aria-labelledby="extracted-heading">
    <h3 id="extracted-heading" class="m-0 mb-3 text-lg font-semibold">{i18n.t('result.extractedHeading')}</h3>
    <ExtractedDataTable data={result.extracted_data} />
  </section>

  <TechnicalDetail
    engineVersion={result.engine_version}
    rulesetVersion={result.ruleset_version}
    analyzerStatuses={result.analyzer_statuses}
  />
</section>
