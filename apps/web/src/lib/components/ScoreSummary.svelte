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

  Always draws a COMPLETE ring (never partially empty, per user feedback:
  a 0/100 score used to render as an empty gray circle, reading as
  "no data" rather than "great news, no risk"). The ring's color instead
  interpolates continuously green -> yellow -> red across the 0-100 range
  via CSS `color-mix()` against the existing `--color-ui-risk-*` custom
  properties (`app.css`), so it stays theme-aware (light/dark) without a
  duplicated hex table in this component. This is a decorative recolor
  only — the outer card's `score-summary--{low,review,high}` tier classes
  (still driven by `classification`) are unchanged.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import { actionKey, classificationKey } from '$lib/i18n/enum-map';

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
  /**
   * Continuous green -> yellow -> red interpolation via `color-mix()`,
   * two linear segments (0-50: low->review, 50-100: review->high) so the
   * midpoint of each half is a clean blend rather than an abrupt jump.
   * Reads the same theme-aware custom properties the rest of the app
   * uses (`app.css`), so it never needs its own light/dark hex table.
   */
  const ringColor = $derived.by(() => {
    const score = Math.max(0, Math.min(100, riskScore));
    const [from, to, percent] =
      score <= 50
        ? (['--color-ui-risk-low', '--color-ui-risk-review', (score / 50) * 100] as const)
        : (['--color-ui-risk-review', '--color-ui-risk-high', ((score - 50) / 50) * 100] as const);
    return `color-mix(in srgb, var(${to}) ${Math.round(percent)}%, var(${from}))`;
  });
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
      <svg viewBox="0 0 100 100" class="h-24 w-24 shrink-0" aria-hidden="true">
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke-width="9"
          stroke={ringColor}
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
