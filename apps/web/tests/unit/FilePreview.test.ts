import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import FilePreview from '../../src/lib/components/FilePreview.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function makeFile(name = 'receipt.png', type = 'image/png', size = 2048): File {
  return new File([new Uint8Array(size)], name, { type });
}

function renderPreview(
  props: { file: File; onanalyze: () => void; onreplace: () => void },
  locale: 'es' | 'en' = 'es'
) {
  const i18n = new I18n(locale);
  render(FilePreview, { props, context: new Map([[I18N_CONTEXT_KEY, i18n]]) });
  return i18n;
}

describe('FilePreview', () => {
  it('shows filename, type and human-readable size with es labels', () => {
    renderPreview({
      file: makeFile('recibo.png', 'image/png', 1536),
      onanalyze: vi.fn(),
      onreplace: vi.fn()
    });

    expect(screen.getByText('recibo.png')).toBeTruthy();
    expect(screen.getByText(/image\/png/i)).toBeTruthy();
    expect(screen.getByText(/1(\.5)? ?KB/i)).toBeTruthy();
    expect(screen.getByText(es['upload.preview.name'])).toBeTruthy();
    expect(screen.getByText(es['upload.preview.type'])).toBeTruthy();
    expect(screen.getByText(es['upload.preview.size'])).toBeTruthy();
  });

  it('shows English labels when locale is en', () => {
    renderPreview({ file: makeFile('receipt.png'), onanalyze: vi.fn(), onreplace: vi.fn() }, 'en');

    expect(screen.getByText(en['upload.preview.name'])).toBeTruthy();
    expect(screen.getByText(en['upload.preview.type'])).toBeTruthy();
    expect(screen.getByText(en['upload.preview.size'])).toBeTruthy();
    expect(screen.getByRole('button', { name: en['upload.preview.analyze'] })).toBeTruthy();
    expect(screen.getByRole('button', { name: en['upload.preview.replace'] })).toBeTruthy();
  });

  it('calls onanalyze when the analyze action is used', () => {
    const onanalyze = vi.fn();
    renderPreview({ file: makeFile(), onanalyze, onreplace: vi.fn() });

    screen.getByRole('button', { name: es['upload.preview.analyze'] }).click();
    expect(onanalyze).toHaveBeenCalled();
  });

  it('calls onreplace when the replace action is used', () => {
    const onreplace = vi.fn();
    renderPreview({ file: makeFile(), onanalyze: vi.fn(), onreplace });

    screen.getByRole('button', { name: es['upload.preview.replace'] }).click();
    expect(onreplace).toHaveBeenCalled();
  });
});
