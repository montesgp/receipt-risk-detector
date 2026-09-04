/**
 * design.md Slice 4 / spec delta "Idle state renders the pipeline explainer":
 * a static, non-interactive, bilingual pipeline explainer summarizing the
 * six real pipeline steps (upload, validation, provenance, extraction,
 * identifiers, scoring). Must carry no `role="status"` / `aria-live`
 * live-region semantics (distinct from `ProcessingStages`) and must never
 * overstate system capability (forbidden-language guard, reused from the
 * existing result-copy rule).
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import PipelineExplainer from '../../src/lib/components/PipelineExplainer.svelte';
import { I18N_CONTEXT_KEY, I18n } from '../../src/lib/i18n/i18n.svelte';
import es from '../../src/lib/i18n/messages/es.json';
import en from '../../src/lib/i18n/messages/en.json';

afterEach(() => cleanup());

function renderExplainer(locale: 'es' | 'en' = 'es') {
  const i18n = new I18n(locale);
  return render(PipelineExplainer, { context: new Map([[I18N_CONTEXT_KEY, i18n]]) });
}

describe('PipelineExplainer', () => {
  it('renders six steps in Spanish', () => {
    renderExplainer('es');

    const items = document.querySelectorAll('li');
    expect(items).toHaveLength(6);
    expect(document.body.textContent).toContain(es['upload.pipeline.heading']);
    expect(document.body.textContent).toContain(es['upload.pipeline.step.upload.title']);
    expect(document.body.textContent).toContain(es['upload.pipeline.step.scoring.detail']);
  });

  it('renders six steps in English', () => {
    renderExplainer('en');

    const items = document.querySelectorAll('li');
    expect(items).toHaveLength(6);
    expect(document.body.textContent).toContain(en['upload.pipeline.heading']);
    expect(document.body.textContent).toContain(en['upload.pipeline.step.upload.title']);
    expect(document.body.textContent).toContain(en['upload.pipeline.step.scoring.detail']);
  });

  it('carries no aria-live/role="status" live-region semantics (distinct from ProcessingStages)', () => {
    const { container } = renderExplainer('es');

    expect(container.querySelector('[role="status"]')).toBeNull();
    expect(container.querySelector('[aria-live]')).toBeNull();
  });

  it('never contains forbidden authenticity/capability language in either locale', () => {
    const forbidden = [
      /\breal\b/i,
      /\bfake\b/i,
      /aut[eé]ntic[oa]/i,
      /authentic/i,
      /\bverificad[oa]\b/i,
      /verified transfer/i
    ];

    renderExplainer('es');
    let text = document.body.textContent ?? '';
    for (const pattern of forbidden) {
      expect(text).not.toMatch(pattern);
    }

    cleanup();

    renderExplainer('en');
    text = document.body.textContent ?? '';
    for (const pattern of forbidden) {
      expect(text).not.toMatch(pattern);
    }
  });
});
