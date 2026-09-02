import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import FilePreview from '../../src/lib/components/FilePreview.svelte';

afterEach(() => cleanup());

function makeFile(name = 'receipt.png', type = 'image/png', size = 2048): File {
  return new File([new Uint8Array(size)], name, { type });
}

describe('FilePreview', () => {
  it('shows filename, type and human-readable size', () => {
    render(FilePreview, {
      props: { file: makeFile('recibo.png', 'image/png', 1536), onanalyze: vi.fn(), onreplace: vi.fn() }
    });

    expect(screen.getByText('recibo.png')).toBeTruthy();
    expect(screen.getByText(/image\/png/i)).toBeTruthy();
    expect(screen.getByText(/1(\.5)? ?KB/i)).toBeTruthy();
  });

  it('calls onanalyze when the analyze action is used', async () => {
    const onanalyze = vi.fn();
    render(FilePreview, { props: { file: makeFile(), onanalyze, onreplace: vi.fn() } });

    screen.getByRole('button', { name: /Analizar/i }).click();
    expect(onanalyze).toHaveBeenCalled();
  });

  it('calls onreplace when the replace action is used', () => {
    const onreplace = vi.fn();
    render(FilePreview, { props: { file: makeFile(), onanalyze: vi.fn(), onreplace } });

    screen.getByRole('button', { name: /Reemplazar/i }).click();
    expect(onreplace).toHaveBeenCalled();
  });
});
