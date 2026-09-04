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

<ul class="m-0 flex list-none flex-col gap-4 p-0">
  {#each CHECKLIST_ITEMS as item (item.key)}
    <li class="flex flex-col gap-1">
      <span class="font-semibold">{i18n.t(item.labelKey)}</span>
      <span class="text-sm text-ui-muted">{statusFor(item.key)}</span>
    </li>
  {/each}
</ul>
