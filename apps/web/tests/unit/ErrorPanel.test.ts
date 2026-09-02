import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import ErrorPanel from '../../src/lib/components/ErrorPanel.svelte';

afterEach(() => cleanup());

describe('ErrorPanel', () => {
  it('renders a distinct connectivity message for the network variant, never a result', () => {
    render(ErrorPanel, { props: { variant: 'network', onretry: vi.fn() } });

    expect(screen.getByRole('alert').textContent).toMatch(/no pudimos contactar/i);
  });

  it('renders a distinct timeout message', () => {
    render(ErrorPanel, { props: { variant: 'timeout', onretry: vi.fn() } });

    expect(screen.getByRole('alert').textContent).toMatch(/no termin[oó]/i);
  });

  it('surfaces the Retry-After wait for rate-limited without auto-resubmitting', () => {
    render(ErrorPanel, { props: { variant: 'rate-limited', retryAfterSeconds: 30, onretry: vi.fn() } });

    expect(screen.getByRole('alert').textContent).toMatch(/30/);
    // No retry button should be immediately actionable before the wait; a
    // disabled retry communicates "not yet" rather than inviting a bypass.
    const retryButton = screen.getByRole('button', { name: /Reintentar/i });
    expect(retryButton.hasAttribute('disabled')).toBe(true);
  });

  it('derives an actionable message from the error code, never a raw detail/stack', () => {
    render(ErrorPanel, {
      props: {
        variant: 'rejected-file',
        code: 'UNSUPPORTED_IMAGE',
        onretry: vi.fn()
      }
    });

    const alert = screen.getByRole('alert');
    expect(alert.textContent).not.toMatch(/Traceback|at [A-Za-z]+\.[a-z]+ \(/);
    expect(alert.textContent?.length).toBeGreaterThan(0);
  });

  it('calls onretry when the retry action is available and clicked', () => {
    const onretry = vi.fn();
    render(ErrorPanel, { props: { variant: 'network', onretry } });

    screen.getByRole('button', { name: /Reintentar/i }).click();
    expect(onretry).toHaveBeenCalled();
  });
});
