<!--
  ui-polish round 2, item 6: the API is independent and consumable by any
  client, not just this site (PRD constraint, see repo README/API docs). This
  panel is a static, non-interactive visual showing the same three-step flow
  a WhatsApp/Telegram/messaging-app bot would follow against the public
  `/v1/receipts/analyze` endpoint. Purely illustrative — no forbidden
  authenticity language, no live network calls, no external branding assets.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  const i18n = getI18nContext();
  const STEPS = ['message', 'api', 'reply'] as const;
</script>

<div class="flex flex-col gap-4">
  <div class="max-w-reading">
    <p class="m-0 font-semibold">{i18n.t('pipeline.integration.heading')}</p>
    <p class="m-0 mt-1 text-sm text-ui-muted">{i18n.t('pipeline.integration.description')}</p>
  </div>

  <div class="flex flex-wrap items-center gap-2" aria-hidden="true">
    {#each STEPS as step, index (step)}
      <div
        class="flex min-w-[9rem] flex-1 flex-col items-center gap-2 rounded-ui border border-ui-line bg-ui-surface p-4 text-center"
      >
        <span
          class="flex h-9 w-9 items-center justify-center rounded-full border border-ui-line text-lg"
        >
          {#if step === 'message'}💬{:else if step === 'api'}⚙{:else}📊{/if}
        </span>
        <span class="text-sm font-medium">{i18n.t(`pipeline.integration.step.${step}`)}</span>
      </div>
      {#if index < STEPS.length - 1}
        <span class="bot-flow-arrow shrink-0 text-lg text-ui-muted">→</span>
      {/if}
    {/each}
  </div>
</div>

<style>
  /* Small, reduced-motion-respecting nudge so the flow reads as "moving
     forward" without a chart/animation library. */
  @media (prefers-reduced-motion: no-preference) {
    .bot-flow-arrow {
      animation: bot-flow-nudge 1.6s ease-in-out infinite;
    }
  }

  @keyframes bot-flow-nudge {
    0%,
    100% {
      transform: translateX(0);
    }
    50% {
      transform: translateX(3px);
    }
  }
</style>
