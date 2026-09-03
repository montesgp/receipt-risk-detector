import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ErrorPanel from '../../src/lib/components/ErrorPanel.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderPanel(
  props: {
    variant: 'network' | 'timeout' | 'rate-limited' | 'rejected-file';
    code?: string;
    retryAfterSeconds?: number;
    onretry: () => void;
  },
  locale: 'es' | 'en' = 'es'
) {
  const i18n = new I18n(locale);
  render(ErrorPanel, { props, context: new Map([[I18N_CONTEXT_KEY, i18n]]) });
  return i18n;
}

describe('ErrorPanel', () => {
  it('renders a distinct connectivity message for the network variant, never a result (es)', () => {
    renderPanel({ variant: 'network', onretry: vi.fn() });

    expect(screen.getByRole('alert').textContent).toContain(es['errors.network']);
  });

  it('renders a distinct connectivity message for the network variant (en)', () => {
    renderPanel({ variant: 'network', onretry: vi.fn() }, 'en');

    expect(screen.getByRole('alert').textContent).toContain(en['errors.network']);
  });

  it('renders a distinct timeout message', () => {
    renderPanel({ variant: 'timeout', onretry: vi.fn() });

    expect(screen.getByRole('alert').textContent).toContain(es['errors.timeout']);
  });

  it('surfaces the Retry-After wait for rate-limited without auto-resubmitting (es)', () => {
    renderPanel({ variant: 'rate-limited', retryAfterSeconds: 30, onretry: vi.fn() });

    const expectedWait = es['errors.rateLimited.waitSeconds'].replace('{seconds}', '30');
    expect(screen.getByRole('alert').textContent).toContain(es['errors.rateLimited.prefix']);
    expect(screen.getByRole('alert').textContent).toContain(expectedWait);
    // No retry button should be immediately actionable before the wait; a
    // disabled retry communicates "not yet" rather than inviting a bypass.
    const retryButton = screen.getByRole('button', { name: es['common.retry'] });
    expect(retryButton.hasAttribute('disabled')).toBe(true);
  });

  it('surfaces the Retry-After wait for rate-limited (en)', () => {
    renderPanel({ variant: 'rate-limited', retryAfterSeconds: 30, onretry: vi.fn() }, 'en');

    const expectedWait = en['errors.rateLimited.waitSeconds'].replace('{seconds}', '30');
    expect(screen.getByRole('alert').textContent).toContain(en['errors.rateLimited.prefix']);
    expect(screen.getByRole('alert').textContent).toContain(expectedWait);
  });

  it('derives an actionable message from the error code, never a raw detail/stack (es)', () => {
    renderPanel({ variant: 'rejected-file', code: 'UNSUPPORTED_IMAGE', onretry: vi.fn() });

    const alert = screen.getByRole('alert');
    expect(alert.textContent).toContain(es['errors.rejectedFile.unsupportedImage']);
    expect(alert.textContent).not.toMatch(/Traceback|at [A-Za-z]+\.[a-z]+ \(/);
  });

  it('derives an actionable message from the error code (en)', () => {
    renderPanel({ variant: 'rejected-file', code: 'UNSUPPORTED_IMAGE', onretry: vi.fn() }, 'en');

    expect(screen.getByRole('alert').textContent).toContain(en['errors.rejectedFile.unsupportedImage']);
  });

  it('falls back to the generic rejected-file message for an unknown code', () => {
    renderPanel({ variant: 'rejected-file', code: 'SOMETHING_ELSE', onretry: vi.fn() });

    expect(screen.getByRole('alert').textContent).toContain(es['errors.rejectedFile.generic']);
  });

  it('moves focus to the alert message when it renders (focus management, slice 4)', async () => {
    renderPanel({ variant: 'network', onretry: vi.fn() });
    await Promise.resolve();

    expect(document.activeElement).toBe(screen.getByRole('alert'));
  });

  it('calls onretry when the retry action is available and clicked', () => {
    const onretry = vi.fn();
    renderPanel({ variant: 'network', onretry });

    screen.getByRole('button', { name: es['common.retry'] }).click();
    expect(onretry).toHaveBeenCalled();
  });
});
