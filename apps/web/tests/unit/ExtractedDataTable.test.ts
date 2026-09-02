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

afterEach(() => cleanup());

describe('ExtractedDataTable', () => {
  it('renders masked_value for a masked field and never renders a raw value for it', () => {
    const data: Record<string, ExtractedFieldModel> = {
      destination_cbu: { masked_value: '******************5678', confidence: 0.94 }
    };

    render(ExtractedDataTable, { props: { data } });

    expect(screen.getByText('******************5678')).toBeTruthy();
  });

  it('renders the raw value when no masked_value is present (e.g. amount)', () => {
    const data: Record<string, ExtractedFieldModel> = {
      amount: { value: '125000.00', confidence: 0.97 }
    };

    render(ExtractedDataTable, { props: { data } });

    expect(screen.getByText(/125.?000/)).toBeTruthy();
  });

  it('renders correctly when is_checksum_valid is entirely absent', () => {
    const data: Record<string, ExtractedFieldModel> = {
      cuit: { masked_value: '*******4321', confidence: 0.9 }
    };

    expect(() => render(ExtractedDataTable, { props: { data } })).not.toThrow();
    expect(screen.getByText('*******4321')).toBeTruthy();
  });

  it('renders a checksum indicator only when is_checksum_valid is explicitly present', () => {
    const data: Record<string, ExtractedFieldModel> = {
      cuit: { masked_value: '*******4321', confidence: 0.9, is_checksum_valid: true }
    };

    render(ExtractedDataTable, { props: { data } });

    expect(screen.getByText(/checksum|dígito verificador/i)).toBeTruthy();
  });

  it('renders nothing misleading for an empty extracted_data map', () => {
    render(ExtractedDataTable, { props: { data: {} } });
    expect(screen.queryAllByRole('row').length).toBe(0);
  });
});
