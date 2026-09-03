<!--
  DESIGN.md §7 "Reconciliation checklist": present amount, approximate
  date, originator, beneficiary and operation ID as a checklist for
  comparing against the beneficiary account. Renders every item even when
  the corresponding extracted field is absent — this is manual-verification
  guidance, not a completeness report, and must never imply that viewing
  the screenshot alone constitutes reconciliation.
-->
<script lang="ts">
  import type { ExtractedFieldModel } from '$lib/api/types';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  let { data }: { data: Record<string, ExtractedFieldModel> } = $props();

  const i18n = getI18nContext();

  const CHECKLIST_ITEMS: { key: string; labelKey: string }[] = [
    { key: 'amount', labelKey: 'result.checklist.amount' },
    { key: 'date_time', labelKey: 'result.checklist.date_time' },
    { key: 'destination_cbu', labelKey: 'result.checklist.destination_cbu' },
    { key: 'cuit', labelKey: 'result.checklist.cuit' }
  ];

  function statusFor(key: string): string {
    const field = data[key];
    if (!field) return i18n.t('result.checklist.missing');
    return i18n.t('result.checklist.present');
  }
</script>

<ul class="reconciliation-checklist">
  {#each CHECKLIST_ITEMS as item (item.key)}
    <li class="reconciliation-checklist__item">
      <span class="reconciliation-checklist__label">{i18n.t(item.labelKey)}</span>
      <span class="reconciliation-checklist__status">{statusFor(item.key)}</span>
    </li>
  {/each}
</ul>

<style>
  .reconciliation-checklist {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }

  .reconciliation-checklist__item {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .reconciliation-checklist__label {
    font-weight: 600;
  }

  .reconciliation-checklist__status {
    color: var(--color-text-muted);
    font-size: 0.875rem;
  }
</style>
