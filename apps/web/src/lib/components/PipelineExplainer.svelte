<!--
  design.md Slice 4 / spec delta "Idle state renders the pipeline explainer"
  (PRD FR-013): a static, non-interactive, bilingual summary of the seven
  real pipeline steps (FR-001 through FR-007, plus the PyTorch-based visual
  inspection step added by the visual-anomaly-detection change), rendered
  directly below the drop zone in the idle state only. Deliberately carries
  no `role="status"` /
  `aria-live` — it is not `ProcessingStages` (§4.3), which is the live
  uploading-status widget.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  const i18n = getI18nContext();
  const STEPS = [
    'upload',
    'validation',
    'provenance',
    'extraction',
    'identifiers',
    'vision',
    'scoring'
  ] as const;
</script>

<section class="max-w-reading" aria-labelledby="pipeline-heading">
  <h2 id="pipeline-heading" class="m-0 mb-4 text-lg font-semibold">
    {i18n.t('upload.pipeline.heading')}
  </h2>
  <ol class="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
    {#each STEPS as step, index (step)}
      <li class="flex gap-3 rounded-ui border border-ui-line bg-ui-surface p-4">
        <span
          aria-hidden="true"
          class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-ui-line font-mono text-sm text-ui-muted tabular-nums"
        >{index + 1}</span>
        <div class="flex flex-col gap-1">
          <p class="m-0 font-semibold">{i18n.t(`upload.pipeline.step.${step}.title`)}</p>
          <p class="m-0 text-sm text-ui-muted">{i18n.t(`upload.pipeline.step.${step}.detail`)}</p>
        </div>
      </li>
    {/each}
  </ol>
</section>
