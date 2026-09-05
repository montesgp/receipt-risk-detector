<!--
  DESIGN.md §7 "Score summary": classification as text first, risk as
  `74 / 100` (never a percentage), confidence shown separately. If
  `INCONCLUSIVE`, confidence and missing-evidence context dominate and no
  risk-tier color is forced (spec "INCONCLUSIVE result does not force a risk
  color"). Colors map to §6.3 tokens; never used alone (text label always
  accompanies the color per §10 accessibility).

  ui-polish round 2, item 7: adds a decorative SVG risk-ring next to the
  score, hand-rolled (no charting library — avoids a new dependency for one
  small gauge). `aria-hidden`, since the same value is already conveyed as
  text right next to it. The `12 / 100` text node stays a standalone
  element with unchanged text, so the existing `getByText('N / 100')`
  assertions keep passing.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import { actionKey, classificationKey } from '$lib/i18n/enum-map';

  // r=42 circle: circumference = 2 * PI * 42 ≈ 264.
  const RING_CIRCUMFERENCE = 264;

  let {
    classification,
    riskScore,
    confidenceScore,
    recommendedAction,
    noTextDetected = false
  }: {
    classification: string;
    riskScore: number;
    /**
     * Already a 0-100 integer per `AnalyzeResponse.confidence_score`
     * (`schemas.py`), same scale as `risk_score` — NOT a 0-1 float.
     */
    confidenceScore: number;
    recommendedAction: string;
    /**
     * True when a `CORE_FIELD_EXTRACTION_FAILED` signal with
     * `evidence.reason === 'no_text_detected'` fired (derived by the
     * `ResultView` container from `result.signals` — scoring-confidence-
     * calibration change). Selects the hedged "we could not identify
     * transfer data" copy instead of the generic inconclusive note; never
     * asserts an absolute verdict either way.
     */
    noTextDetected?: boolean;
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
  const inconclusiveKey = $derived(
    noTextDetected ? 'result.inconclusiveNoTextNote' : 'result.inconclusiveNote'
  );
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

  <div class="flex flex-wrap items-center gap-6">
    {#if !isInconclusive}
      <svg viewBox="0 0 100 100" class="h-24 w-24 shrink-0 -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r="42" fill="none" stroke-width="9" class="stroke-ui-line" />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke-width="9"
          stroke-linecap="round"
          stroke="currentColor"
          stroke-dasharray={RING_CIRCUMFERENCE}
          stroke-dashoffset={RING_CIRCUMFERENCE - (RING_CIRCUMFERENCE * riskScore) / 100}
          class:text-ui-risk-low={tier === 'low'}
          class:text-ui-risk-review={tier === 'review'}
          class:text-ui-risk-high={tier === 'high'}
        />
      </svg>
    {/if}

    <div class="flex min-w-0 flex-col gap-2">
      {#if isInconclusive}
        <p class="m-0 text-ui-muted">
          {i18n.t(inconclusiveKey, { confidence: confidencePercent })}
        </p>
      {:else}
        <p class="m-0 text-[2.5rem] font-bold leading-none tabular-nums">{riskScore} / 100</p>
      {/if}

      <p class="m-0 text-ui-muted">{i18n.t('result.confidenceLabel', { confidence: confidencePercent })}</p>

      {#if actionLabel}
        <p class="m-0 text-ui-muted">{actionLabel}</p>
      {/if}
    </div>
  </div>
</section>
