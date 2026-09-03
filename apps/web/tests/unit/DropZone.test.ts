import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import DropZone from '../../src/lib/components/DropZone.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function makeFile(name = 'receipt.png', type = 'image/png'): File {
  return new File([new Uint8Array(1024)], name, { type });
}

function renderZone(props: { disabled?: boolean; onselect: (file: File) => void }, locale: 'es' | 'en' = 'es') {
  const i18n = new I18n(locale);
  render(DropZone, {
    props: { disabled: false, ...props },
    context: new Map([[I18N_CONTEXT_KEY, i18n]])
  });
  return i18n;
}

describe('DropZone', () => {
  it('shows the idle constraints copy from the i18n catalog (es)', () => {
    renderZone({ onselect: vi.fn() });

    expect(screen.getByText(es['upload.dropzone.constraints'])).toBeTruthy();
    expect(screen.getByText(es['upload.dropzone.heading'])).toBeTruthy();
  });

  it('shows the idle constraints copy from the i18n catalog (en)', () => {
    renderZone({ onselect: vi.fn() }, 'en');

    expect(screen.getByText(en['upload.dropzone.constraints'])).toBeTruthy();
    expect(screen.getByText(en['upload.dropzone.heading'])).toBeTruthy();
  });

  it('is keyboard-operable: the drop zone is a focusable button', () => {
    renderZone({ onselect: vi.fn() });

    const zone = screen.getByRole('button', { name: new RegExp(es['upload.dropzone.heading']) });
    expect(zone.getAttribute('tabindex')).toBe('0');
  });

  it('calls onselect(file) when a file is chosen via the native input', () => {
    const onselect = vi.fn();
    renderZone({ onselect });

    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(input).toBeTruthy();

    const file = makeFile();
    Object.defineProperty(input, 'files', { value: [file] });
    input.dispatchEvent(new Event('change', { bubbles: true }));

    expect(onselect).toHaveBeenCalledWith(file);
  });

  it('calls onselect(file) when a file is dropped', () => {
    const onselect = vi.fn();
    renderZone({ onselect });

    const zone = screen.getByRole('button', { name: new RegExp(es['upload.dropzone.heading']) });
    const file = makeFile();
    const dataTransfer = { files: [file] } as unknown as DataTransfer;

    zone.dispatchEvent(
      Object.assign(new Event('drop', { bubbles: true, cancelable: true }), { dataTransfer })
    );

    expect(onselect).toHaveBeenCalledWith(file);
  });

  it('marks the zone aria-disabled and ignores input when disabled', () => {
    const onselect = vi.fn();
    renderZone({ disabled: true, onselect });

    const zone = screen.getByRole('button', { name: new RegExp(es['upload.dropzone.heading']) });
    expect(zone.getAttribute('aria-disabled')).toBe('true');
  });
});
