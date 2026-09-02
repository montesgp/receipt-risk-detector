<script lang="ts">
  import { AnalysisWorkspace } from '$lib/features/receipt-analysis/workspace.svelte';

  const workspace = new AnalysisWorkspace();

  function onFileInputChange(event: Event): void {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      workspace.selectFile(file);
    }
  }
</script>

<main class="page">
  <h1>Analizá un comprobante antes de conciliarlo</h1>
  <p>
    Detectamos señales de manipulación, procedencia digital e inconsistencias para ayudarte a
    revisar una transferencia.
  </p>
  <p>PNG, JPG o WebP · máximo 10 MB</p>

  <div role="region" aria-live="polite">
    {#if workspace.status === 'idle'}
      <label for="receipt-file">Arrastrá o seleccioná un comprobante</label>
      <input id="receipt-file" type="file" accept="image/png,image/jpeg,image/webp" onchange={onFileInputChange} />
    {:else if workspace.status === 'selected'}
      <p>Archivo listo: {workspace.file?.name}</p>
      <button type="button" onclick={() => workspace.analyze()}>Analizar</button>
      <button type="button" onclick={() => workspace.reset()}>Reemplazar</button>
    {:else if workspace.status === 'uploading'}
      <p>Analizando el comprobante…</p>
    {:else if workspace.status === 'result' && workspace.result}
      <h2>Resultado: {workspace.result.classification}</h2>
      <p>Riesgo: {workspace.result.risk_score} / 100</p>
      <button type="button" onclick={() => workspace.reset()}>Analizar otro comprobante</button>
    {:else if workspace.status === 'error' && workspace.error}
      <p role="alert">
        {#if workspace.error.kind === 'network'}
          No pudimos contactar el servicio. Intentá nuevamente.
        {:else if workspace.error.kind === 'timeout'}
          El análisis no terminó a tiempo. Podés reintentar.
        {:else if workspace.error.kind === 'rate-limited'}
          Hay demasiadas solicitudes en este momento. Reintentá en unos segundos.
        {:else}
          Ocurrió un problema al analizar el comprobante.
        {/if}
      </p>
      <button type="button" onclick={() => workspace.analyze()}>Reintentar</button>
    {/if}
  </div>

  <p>
    Este análisis evalúa el comprobante presentado. Confirmá la acreditación en la cuenta
    beneficiaria antes de entregar productos o servicios.
  </p>
</main>
