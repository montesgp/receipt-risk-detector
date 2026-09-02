<!--
  DESIGN.md §4.5 "Error": explain what the user can do next, preserve the
  file in memory only when retry is safe, never a raw stack trace or tool
  error. Spec "Service-unavailable / connectivity error state": network
  failure must never look like a result. Spec "Rate-limit (429) handling":
  the client MUST NOT auto-resubmit before Retry-After elapses, so the retry
  action stays disabled until then.
-->
<script lang="ts">
  type Variant = 'network' | 'timeout' | 'rate-limited' | 'rejected-file';

  let {
    variant,
    code,
    retryAfterSeconds,
    onretry
  }: {
    variant: Variant;
    code?: string;
    retryAfterSeconds?: number;
    onretry: () => void;
  } = $props();

  // Every message here is authored copy, never `detail`/a stack trace, per
  // the "Server-side validation error is explained" spec scenario.
  const REJECTED_FILE_MESSAGES: Record<string, string> = {
    MISSING_FILE: 'No se recibió ningún archivo. Elegí un comprobante para continuar.',
    FILE_TOO_LARGE: 'El archivo supera el límite de 10 MB. Elegí un comprobante más liviano.',
    UNSUPPORTED_IMAGE: 'El formato no es compatible. Usá PNG, JPG o WebP.',
    IMAGE_DIMENSIONS_EXCEEDED: 'Las dimensiones de la imagen exceden lo permitido.',
    MALFORMED_RESPONSE: 'El servidor devolvió una respuesta inesperada.'
  };

  const message = $derived.by(() => {
    if (variant === 'network') return 'No pudimos contactar el servicio. Intentá nuevamente.';
    if (variant === 'timeout') return 'El análisis no terminó a tiempo. Podés reintentar.';
    if (variant === 'rate-limited') {
      const wait =
        retryAfterSeconds !== undefined
          ? `Reintentá en ${retryAfterSeconds} segundos.`
          : 'Reintentá en unos instantes.';
      return `Hay demasiadas solicitudes en este momento. ${wait}`;
    }
    return code && REJECTED_FILE_MESSAGES[code]
      ? REJECTED_FILE_MESSAGES[code]
      : 'Ocurrió un problema al procesar el comprobante. Elegí otro archivo.';
  });

  const retryDisabled = $derived(variant === 'rate-limited' && retryAfterSeconds !== undefined);
</script>

<div class="error-panel" role="alert">
  <p class="error-panel__message">{message}</p>
  <button type="button" onclick={onretry} disabled={retryDisabled}>Reintentar</button>
</div>

<style>
  .error-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    border: 1px solid var(--color-risk-high);
    border-radius: var(--radius);
    padding: var(--space-4);
    background: var(--color-surface);
  }

  .error-panel__message {
    margin: 0;
  }
</style>
