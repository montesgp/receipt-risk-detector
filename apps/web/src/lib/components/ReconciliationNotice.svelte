<!--
  DD7 / AGENTS.md MVP1 invariant: this component is mounted unconditionally
  by +page.svelte in EVERY workspace state (idle and result), never behind a
  state branch, so a state-machine bug can never silently drop the
  disclaimer. See DESIGN.md §5 "Result language" for the exact required
  sentence and the forbidden-word list.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  const i18n = getI18nContext();
</script>

<p class="reconciliation-notice">{i18n.t('legal.disclaimer')}</p>

<style>
  .reconciliation-notice {
    color: var(--color-text-muted);
    font-size: 0.875rem;
    margin: 0;
  }
</style>
