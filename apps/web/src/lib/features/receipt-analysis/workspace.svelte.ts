/**
 * DD1: one `AnalysisWorkspace` class using Svelte 5 runes, instantiated
 * per-page-instance (not a module singleton) so SSR/prerender and Vitest
 * both get an isolated workspace. See DESIGN.md §4 and the design.md
 * "Workspace state machine" table for the exact transition contract.
 */

import { analyzeReceipt, validateFileForUpload } from '../../api/client';
import type { AnalyzeFailure } from '../../api/errors';
import type { AnalyzeResponse } from '../../api/types';

export type WorkspaceStatus = 'idle' | 'selected' | 'uploading' | 'result' | 'error';

export type WorkspaceErrorVariant =
  | { kind: 'rate-limited'; retryAfterSeconds?: number; detail: string }
  | { kind: 'timeout'; detail: string }
  | { kind: 'network' }
  | { kind: 'rejected-file'; code: string; detail: string }
  | { kind: 'client-validation'; reason: 'unsupported-type' | 'too-large' };

export class AnalysisWorkspace {
  status = $state<WorkspaceStatus>('idle');
  file = $state<File | null>(null);
  result = $state<AnalyzeResponse | null>(null);
  error = $state<WorkspaceErrorVariant | null>(null);

  canAnalyze = $derived(this.status === 'selected' && this.file !== null);

  /**
   * File selection and validation: an invalid file never reaches
   * `selected` and the API is never called for it.
   */
  selectFile(file: File): void {
    const reason = validateFileForUpload(file);
    if (reason) {
      this.file = null;
      this.result = null;
      this.error = { kind: 'client-validation', reason };
      this.status = 'idle';
      return;
    }
    this.file = file;
    this.result = null;
    this.error = null;
    this.status = 'selected';
  }

  reset(): void {
    this.file = null;
    this.result = null;
    this.error = null;
    this.status = 'idle';
  }

  async analyze(): Promise<void> {
    if (!this.file) return;
    const file = this.file;
    this.status = 'uploading';
    this.error = null;

    const outcome = await analyzeReceipt(file);

    if (outcome.ok) {
      this.result = outcome.data;
      this.status = 'result';
      return;
    }
    this.applyFailure(outcome.failure);
  }

  private applyFailure(failure: AnalyzeFailure): void {
    if (failure.kind === 'network') {
      // File retained per spec "Network failure shows a connectivity state".
      this.error = { kind: 'network' };
      this.status = 'error';
      return;
    }

    if (failure.kind === 'malformed') {
      // File retained: this is a server/contract problem, not a file problem.
      this.error = {
        kind: 'rejected-file',
        code: 'MALFORMED_RESPONSE',
        detail: 'The server returned an unexpected response.'
      };
      this.status = 'error';
      return;
    }

    if (failure.kind === 'client-validation') {
      this.file = null;
      this.error = { kind: 'client-validation', reason: failure.reason };
      this.status = 'idle';
      return;
    }

    // failure.kind === 'problem'
    const { problem, retryAfterSeconds } = failure;

    if (problem.status === 429) {
      // File retained; the caller MUST NOT auto-resubmit before Retry-After.
      this.error = { kind: 'rate-limited', retryAfterSeconds, detail: problem.detail };
      this.status = 'error';
      return;
    }

    if (problem.status === 504) {
      // File retained; distinct from a validation error per spec.
      this.error = { kind: 'timeout', detail: problem.detail };
      this.status = 'error';
      return;
    }

    // 400 / 413 / 415 / 422 — file cleared, back to idle so the user picks another file.
    this.file = null;
    this.error = { kind: 'rejected-file', code: problem.code, detail: problem.detail };
    this.status = 'idle';
  }
}
