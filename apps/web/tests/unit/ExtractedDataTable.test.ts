/**
 * DESIGN.md §7 "Extracted-data table": aligned label/value rows, mask
 * CBU/CVU and CUIT/CUIL by default. design.md: `is_checksum_valid` is never
 * populated today, so the table must treat it as optional and never
 * unmask a masked field by falling back to a (nonexistent) `value`.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ExtractedDataTable from '../../src/lib/components/ExtractedDataTable.svelte';
import type { ExtractedFieldModel } from '../../src/lib/api/types';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderTable(data: Record<string, ExtractedFieldModel>, locale: 'es' | 'en' = 'es') {
  return render(ExtractedDataTable, {
    props: { data },
    context: new Map([[I18N_CONTEXT_KEY, new I18n(locale)]])
  });
}

describe('ExtractedDataTable', () => {
  it('renders masked_value for a masked field and never renders a raw value for it', () => {
    const data: Record<string, ExtractedFieldModel> = {
      destination_cbu: { masked_value: '******************5678', confidence: 0.94 }
    };

    renderTable(data);

    expect(screen.getByText('******************5678')).toBeTruthy();
    expect(screen.getByText(es['result.field.destination_cbu'])).toBeTruthy();
  });

  it('renders the raw value when no masked_value is present (e.g. amount)', () => {
    const data: Record<string, ExtractedFieldModel> = {
      amount: { value: '125000.00', confidence: 0.97 }
    };

    renderTable(data);

    expect(screen.getByText(/125.?000/)).toBeTruthy();
    expect(screen.getByText(es['result.field.amount'])).toBeTruthy();
  });

  it('renders field labels in English when locale is en', () => {
    const data: Record<string, ExtractedFieldModel> = {
      amount: { value: '125000.00', confidence: 0.97 }
    };

    renderTable(data, 'en');

    expect(screen.getByText(en['result.field.amount'])).toBeTruthy();
  });

  it('renders correctly when is_checksum_valid is entirely absent', () => {
    const data: Record<string, ExtractedFieldModel> = {
      cuit: { masked_value: '*******4321', confidence: 0.9 }
    };

    expect(() => renderTable(data)).not.toThrow();
    expect(screen.getByText('*******4321')).toBeTruthy();
  });

  it('renders a checksum indicator only when is_checksum_valid is explicitly present', () => {
    const data: Record<string, ExtractedFieldModel> = {
      cuit: { masked_value: '*******4321', confidence: 0.9, is_checksum_valid: true }
    };

    renderTable(data);

    expect(screen.getByText(es['result.checksum.valid'])).toBeTruthy();
  });

  it('renders nothing misleading for an empty extracted_data map', () => {
    renderTable({});
    expect(screen.queryAllByRole('row').length).toBe(0);
    expect(screen.getByText(es['result.extractedEmpty'])).toBeTruthy();
  });
});
