<!--
  DESIGN.md §7 "Score summary": classification as text first, risk as
  `74 / 100` (never a percentage), confidence shown separately. If
  `INCONCLUSIVE`, confidence and missing-evidence context dominate and no
  risk-tier color is forced (spec "INCONCLUSIVE result does not force a risk
  color"). Colors map to §6.3 tokens; never used alone (text label always
  accompanies the color per §10 accessibility).
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import { actionKey, classificationKey } from '$lib/i18n/enum-map';

  let {
    classification,
    riskScore,
    confidenceScore,
    recommendedAction
  }: {
    classification: string;
    riskScore: number;
    /**
     * Already a 0-100 integer per `AnalyzeResponse.confidence_score`
     * (`schemas.py`), same scale as `risk_score` — NOT a 0-1 float.
     */
    confidenceScore: number;
    recommendedAction: string;
  } = $props();

  const i18n = getI18nContext();

  const RISK_TIER: Record<string, string> = {
    LOW_RISK: 'low',
    REVIEW_RECOMMENDED: 'review',
    SUSPICIOUS: 'review',
    HIGH_RISK: 'high'
    // INCONCLUSIVE intentionally omitted: no forced risk-tier color.
  };

  const tier = $derived(RISK_TIER[classification]);
  const isInconclusive = $derived(classification === 'INCONCLUSIVE');
  const confidencePercent = $derived(Math.round(confidenceScore));
  const classificationLabel = $derived.by(() => {
    const key = classificationKey(classification);
    return key ? i18n.t(key) : classification;
  });
  const actionLabel = $derived.by(() => {
    const key = actionKey(recommendedAction);
    return key ? i18n.t(key) : undefined;
  });
</script>

<section
  class="score-summary flex flex-col gap-3 rounded-ui border border-ui-line bg-ui-surface p-6"
  class:score-summary--low={tier === 'low'}
  class:score-summary--review={tier === 'review'}
  class:score-summary--high={tier === 'high'}
  class:border-ui-risk-low={tier === 'low'}
  class:border-ui-risk-review={tier === 'review'}
  class:border-ui-risk-high={tier === 'high'}
>
  <p class="m-0 text-xl font-semibold">{classificationLabel}</p>

  {#if isInconclusive}
    <p class="m-0 text-ui-muted">
      {i18n.t('result.inconclusiveNote', { confidence: confidencePercent })}
    </p>
  {:else}
    <p class="m-0 mt-1 text-[2.5rem] font-bold leading-none tabular-nums">{riskScore} / 100</p>
  {/if}

  <p class="m-0 text-ui-muted">{i18n.t('result.confidenceLabel', { confidence: confidencePercent })}</p>

  {#if actionLabel}
    <p class="m-0 text-ui-muted">{actionLabel}</p>
  {/if}
</section>
