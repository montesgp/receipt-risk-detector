import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ProcessingStages from '../../src/lib/components/ProcessingStages.svelte';

afterEach(() => cleanup());

describe('ProcessingStages', () => {
  it('exposes an ARIA live region announcing the processing state', () => {
    render(ProcessingStages);

    const region = screen.getByRole('status');
    expect(region.getAttribute('aria-live')).toBe('polite');
  });

  it('never renders a fabricated percentage', () => {
    render(ProcessingStages);

    expect(screen.queryByText(/%/)).toBeNull();
  });

  it('shows coarse honest stage copy', () => {
    render(ProcessingStages);

    expect(screen.getByText(/Analizando el comprobante/i)).toBeTruthy();
  });
});
