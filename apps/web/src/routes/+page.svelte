<script lang="ts">
  import { AnalysisWorkspace } from '$lib/features/receipt-analysis/workspace.svelte';
  import DropZone from '$lib/components/DropZone.svelte';
  import FilePreview from '$lib/components/FilePreview.svelte';
  import ProcessingStages from '$lib/components/ProcessingStages.svelte';
  import ErrorPanel from '$lib/components/ErrorPanel.svelte';
  import ReconciliationNotice from '$lib/components/ReconciliationNotice.svelte';
  import ResultView from '$lib/components/ResultView.svelte';

  const workspace = new AnalysisWorkspace();

  // DESIGN.md §4.5: preserve the file only when retry is safe. Both
  // server-rejected files (400/413/415/422) and client-side validation
  // failures already cleared the file and returned the workspace to `idle`,
  // so their ErrorPanel renders above the drop zone rather than replacing it.
  const idleError = $derived(
    workspace.status === 'idle' &&
      (workspace.error?.kind === 'client-validation' || workspace.error?.kind === 'rejected-file')
      ? workspace.error
      : null
  );
</script>

<main class="page">
  <h1>Analizá un comprobante antes de conciliarlo</h1>
  <p>
    Detectamos señales de manipulación, procedencia digital e inconsistencias para ayudarte a
    revisar una transferencia.
  </p>

  <!-- DD7: always mounted, both in idle and result contexts, never behind a
       state branch. -->
  <ReconciliationNotice />

  <div role="region" aria-label="Estado del análisis">
    {#if idleError?.kind === 'client-validation'}
      <ErrorPanel
        variant="rejected-file"
        code={idleError.reason === 'too-large' ? 'FILE_TOO_LARGE' : 'UNSUPPORTED_IMAGE'}
        onretry={() => workspace.reset()}
      />
    {:else if idleError?.kind === 'rejected-file'}
      <ErrorPanel variant="rejected-file" code={idleError.code} onretry={() => workspace.reset()} />
    {/if}

    {#if workspace.status === 'idle'}
      <DropZone disabled={false} onselect={(file) => workspace.selectFile(file)} />
    {:else if workspace.status === 'selected' && workspace.file}
      <FilePreview
        file={workspace.file}
        onanalyze={() => workspace.analyze()}
        onreplace={() => workspace.reset()}
      />
    {:else if workspace.status === 'uploading'}
      <ProcessingStages />
    {:else if workspace.status === 'result' && workspace.result}
      <ResultView result={workspace.result} />
      <button type="button" onclick={() => workspace.reset()}>Analizar otro comprobante</button>
    {:else if workspace.status === 'error' && workspace.error}
      {@const err = workspace.error}
      {#if err.kind === 'network'}
        <ErrorPanel variant="network" onretry={() => workspace.analyze()} />
      {:else if err.kind === 'timeout'}
        <ErrorPanel variant="timeout" onretry={() => workspace.analyze()} />
      {:else if err.kind === 'rate-limited'}
        <ErrorPanel
          variant="rate-limited"
          retryAfterSeconds={err.retryAfterSeconds}
          onretry={() => workspace.analyze()}
        />
      {:else if err.kind === 'rejected-file'}
        <ErrorPanel variant="rejected-file" code={err.code} onretry={() => workspace.reset()} />
      {/if}
    {/if}
  </div>
</main>
