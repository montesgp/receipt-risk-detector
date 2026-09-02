<!--
  DESIGN.md §4.3 "Processing": honest coarse stages, never a fabricated
  precise percentage; announced through an ARIA live region (§10
  accessibility, NFR-004). Slice 1a has no real per-stage signal from the
  API yet, so this shows one honest indeterminate stage rather than
  simulating granular progress the API cannot actually report.
-->
<script lang="ts"></script>

<div role="status" aria-live="polite" class="processing">
  <p class="processing__label">Analizando el comprobante…</p>
  <div class="processing__bar" aria-hidden="true"></div>
</div>

<style>
  .processing {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    padding: var(--space-4);
  }

  .processing__label {
    margin: 0;
  }

  .processing__bar {
    height: 4px;
    border-radius: var(--radius);
    background: linear-gradient(90deg, var(--color-border), var(--color-focus), var(--color-border));
    background-size: 200% 100%;
    animation: processing-sweep 1.4s linear infinite;
  }

  @media (prefers-reduced-motion: reduce) {
    .processing__bar {
      animation: none;
    }
  }

  @keyframes processing-sweep {
    from {
      background-position: 200% 0;
    }
    to {
      background-position: -200% 0;
    }
  }
</style>
