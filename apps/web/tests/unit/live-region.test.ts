/**
 * Shared ARIA live region (DESIGN.md §14 checklist "Keyboard, focus, contrast
 * and reduced-motion checks pass"; spec "State change is announced and not
 * color-only"). Slice 2/3a used a local `role="status"` workaround inside
 * `ThemeSwitcher`/`LanguageSwitcher` because this component didn't exist
 * yet; slice 4 introduces the real shared component and both switchers now
 * render it instead of duplicating the markup (see their own specs for the
 * migrated assertions).
 *
 * This component is also used at the `+page.svelte` workspace level to
 * announce the transition into the `result` state and into an error state —
 * the one gap slice 1a/1b left, since `ProcessingStages` already announces
 * itself via its own visible `role="status"` region and `ErrorPanel` already
 * uses `role="alert"` (an implicit assertive live region).
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/svelte';
import LiveRegion from '../../src/lib/components/LiveRegion.svelte';

afterEach(() => cleanup());

describe('LiveRegion', () => {
  it('renders a role="status" polite live region with the given message', () => {
    render(LiveRegion, { props: { message: 'Resultado disponible' } });

    const status = screen.getByRole('status');
    expect(status.getAttribute('aria-live')).toBe('polite');
    expect(status.textContent).toBe('Resultado disponible');
  });

  it('is visually hidden by default (announcement-only, no layout impact)', () => {
    render(LiveRegion, { props: { message: 'Tema: Oscuro' } });

    const status = screen.getByRole('status');
    expect(status.className).toMatch(/visually-hidden/);
  });

  it('renders visibly when visuallyHidden is false', () => {
    render(LiveRegion, { props: { message: 'Analizando el comprobante…', visuallyHidden: false } });

    const status = screen.getByRole('status');
    expect(status.className).not.toMatch(/visually-hidden/);
  });

  it('updates its announced text when the message prop changes', async () => {
    const { rerender } = render(LiveRegion, { props: { message: 'first' } });
    expect(screen.getByRole('status').textContent).toBe('first');

    await rerender({ message: 'second' });
    expect(screen.getByRole('status').textContent).toBe('second');
  });

  it('supports assertive politeness for urgent announcements', () => {
    render(LiveRegion, { props: { message: 'urgent', politeness: 'assertive' } });

    expect(screen.getByRole('status').getAttribute('aria-live')).toBe('assertive');
  });
});
