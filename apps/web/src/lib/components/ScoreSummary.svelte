<!--
  DESIGN.md §7 "Score summary": classification as text first, risk as
  `74 / 100` (never a percentage), confidence shown separately. If
  `INCONCLUSIVE`, confidence and missing-evidence context dominate and no
  risk-tier color is forced (spec "INCONCLUSIVE result does not force a risk
  color"). Colors map to §6.3 tokens; never used alone (text label always
  accompanies the color per §10 accessibility).
-->
<script lang="ts">
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

  const RISK_TIER: Record<string, string> = {
    LOW_RISK: 'low',
    REVIEW_RECOMMENDED: 'review',
    SUSPICIOUS: 'review',
    HIGH_RISK: 'high'
    // INCONCLUSIVE intentionally omitted: no forced risk-tier color.
  };

  const CLASSIFICATION_LABEL: Record<string, string> = {
    LOW_RISK: 'Riesgo bajo',
    REVIEW_RECOMMENDED: 'Revisión recomendada',
    SUSPICIOUS: 'Sospechoso',
    HIGH_RISK: 'Riesgo alto',
    INCONCLUSIVE: 'No concluyente'
  };

  const ACTION_LABEL: Record<string, string> = {
    STANDARD_MANUAL_RECONCILIATION: 'Realizá la conciliación manual habitual.',
    PRIORITY_MANUAL_RECONCILIATION: 'Priorizá la conciliación manual antes de continuar.',
    DO_NOT_RELY_ON_RECEIPT: 'No te bases en este comprobante para acreditar el pago.'
  };

  const tier = $derived(RISK_TIER[classification]);
  const isInconclusive = $derived(classification === 'INCONCLUSIVE');
  const confidencePercent = $derived(Math.round(confidenceScore));
</script>

<section class="score-summary" class:score-summary--low={tier === 'low'} class:score-summary--review={tier === 'review'} class:score-summary--high={tier === 'high'}>
  <p class="score-summary__classification">{CLASSIFICATION_LABEL[classification] ?? classification}</p>

  {#if isInconclusive}
    <p class="score-summary__inconclusive-note">
      No detectamos evidencia suficiente. La confianza del análisis ({confidencePercent}%) es baja;
      priorizá la conciliación manual.
    </p>
  {:else}
    <p class="score-summary__risk">{riskScore} / 100</p>
  {/if}

  <p class="score-summary__confidence">Confianza del análisis: {confidencePercent}%</p>

  {#if ACTION_LABEL[recommendedAction]}
    <p class="score-summary__action">{ACTION_LABEL[recommendedAction]}</p>
  {/if}
</section>

<style>
  .score-summary {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    padding: var(--space-4);
    background: var(--color-surface);
  }

  .score-summary__classification {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
  }

  .score-summary__risk {
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
    font-variant-numeric: tabular-nums;
  }

  .score-summary__confidence,
  .score-summary__action,
  .score-summary__inconclusive-note {
    margin: 0;
    color: var(--color-text-muted);
  }

  .score-summary--low {
    border-color: var(--color-risk-low);
  }

  .score-summary--review {
    border-color: var(--color-risk-review);
  }

  .score-summary--high {
    border-color: var(--color-risk-high);
  }
</style>
