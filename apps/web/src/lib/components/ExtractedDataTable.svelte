<!--
  DESIGN.md §7 "Extracted-data table": aligned label/value rows, mask
  CBU/CVU and CUIT/CUIL by default; allow deliberate reveal only if product
  requirements later authorize it (not in MVP1). `extracted_data` is a map
  with unknown keys — iterate entries and look up a label with the raw key
  as fallback. `is_checksum_valid` is never populated by `mappers.py` today,
  so it is treated as strictly optional (design.md Interfaces/Contracts).
-->
<script lang="ts">
  import type { ExtractedFieldModel } from '$lib/api/types';
  import { formatAmount, formatDateTime } from '$lib/features/receipt-analysis/format';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  let { data }: { data: Record<string, ExtractedFieldModel> } = $props();

  const i18n = getI18nContext();

  const FIELD_LABEL_KEY: Record<string, string> = {
    amount: 'result.field.amount',
    destination_cbu: 'result.field.destination_cbu',
    cuit: 'result.field.cuit',
    date_time: 'result.field.date_time'
  };

  function labelFor(key: string): string {
    const messageKey = FIELD_LABEL_KEY[key];
    return messageKey ? i18n.t(messageKey) : key;
  }

  // Never unmask: a masked field is rendered from `masked_value` only. Raw
  // `value` is only used when no `masked_value` was provided at all.
  function displayValue(key: string, field: ExtractedFieldModel): string {
    if (field.masked_value !== undefined && field.masked_value !== null) {
      return field.masked_value;
    }
    if (field.value === undefined || field.value === null) return '—';
    if (key === 'amount') return formatAmount(field.value) ?? field.value;
    if (key === 'date_time') return formatDateTime(field.value) ?? field.value;
    return field.value;
  }

  const entries = $derived(Object.entries(data));
</script>

{#if entries.length > 0}
  <table class="w-full border-collapse">
    <tbody>
      {#each entries as [key, field] (key)}
        <tr>
          <th scope="row" class="border-b border-ui-line px-3 py-3 text-left font-medium text-ui-muted">{labelFor(key)}</th>
          <td class="border-b border-ui-line px-3 py-3 text-left">{displayValue(key, field)}</td>
          <td class="border-b border-ui-line px-3 py-3 text-left font-mono text-sm text-ui-muted">{Math.round(field.confidence * 100)}%</td>
          <td class="border-b border-ui-line px-3 py-3 text-left font-mono text-sm text-ui-muted">
            {#if field.is_checksum_valid !== undefined && field.is_checksum_valid !== null}
              {field.is_checksum_valid ? i18n.t('result.checksum.valid') : i18n.t('result.checksum.invalid')}
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
{:else}
  <p class="m-0 text-ui-muted">{i18n.t('result.extractedEmpty')}</p>
{/if}
