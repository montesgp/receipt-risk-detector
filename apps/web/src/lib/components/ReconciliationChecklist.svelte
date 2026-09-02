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

  let { data }: { data: Record<string, ExtractedFieldModel> } = $props();

  const CHECKLIST_ITEMS: { key: string; label: string }[] = [
    { key: 'amount', label: 'Monto acreditado' },
    { key: 'date_time', label: 'Fecha aproximada' },
    { key: 'destination_cbu', label: 'CBU/CVU beneficiario' },
    { key: 'cuit', label: 'CUIT/CUIL beneficiario' }
  ];

  function statusFor(key: string): string {
    const field = data[key];
    if (!field) return 'No extraído del comprobante — verificá manualmente.';
    return 'Presente en el comprobante — comparalo con tu cuenta.';
  }
</script>

<ul class="reconciliation-checklist">
  {#each CHECKLIST_ITEMS as item (item.key)}
    <li class="reconciliation-checklist__item">
      <span class="reconciliation-checklist__label">{item.label}</span>
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
