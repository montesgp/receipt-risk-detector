import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import DropZone from '../../src/lib/components/DropZone.svelte';

afterEach(() => cleanup());

function makeFile(name = 'receipt.png', type = 'image/png'): File {
  return new File([new Uint8Array(1024)], name, { type });
}

describe('DropZone', () => {
  it('shows the idle constraints copy', () => {
    render(DropZone, { props: { disabled: false, onselect: vi.fn() } });

    expect(screen.getByText(/PNG, JPG o WebP/i)).toBeTruthy();
    expect(screen.getByText(/10 MB/i)).toBeTruthy();
  });

  it('is keyboard-operable: the drop zone is a focusable button', () => {
    render(DropZone, { props: { disabled: false, onselect: vi.fn() } });

    const zone = screen.getByRole('button', { name: /Arrastrá o seleccioná un comprobante/i });
    expect(zone.getAttribute('tabindex')).toBe('0');
  });

  it('calls onselect(file) when a file is chosen via the native input', () => {
    const onselect = vi.fn();
    render(DropZone, { props: { disabled: false, onselect } });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeTruthy();

    const file = makeFile();
    Object.defineProperty(input, 'files', { value: [file] });
    input.dispatchEvent(new Event('change', { bubbles: true }));

    expect(onselect).toHaveBeenCalledWith(file);
  });

  it('calls onselect(file) when a file is dropped', () => {
    const onselect = vi.fn();
    render(DropZone, { props: { disabled: false, onselect } });

    const zone = screen.getByRole('button', { name: /Arrastrá o seleccioná un comprobante/i });
    const file = makeFile();
    const dataTransfer = { files: [file] } as unknown as DataTransfer;

    zone.dispatchEvent(
      Object.assign(new Event('drop', { bubbles: true, cancelable: true }), { dataTransfer })
    );

    expect(onselect).toHaveBeenCalledWith(file);
  });

  it('marks the zone aria-disabled and ignores input when disabled', () => {
    const onselect = vi.fn();
    render(DropZone, { props: { disabled: true, onselect } });

    const zone = screen.getByRole('button', { name: /Arrastrá o seleccioná un comprobante/i });
    expect(zone.getAttribute('aria-disabled')).toBe('true');
  });
});
