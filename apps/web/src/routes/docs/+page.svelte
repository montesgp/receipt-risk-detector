<!--
  ui-polish round 3, item 4: a documentation route inside the existing app
  (scope explicitly chosen over a separate docs site) explaining the
  product and the public API, the way svelte.dev/react.dev document their
  own project — content sourced from README.md and docs/API.md (never
  invented), condensed for a single scrollable page instead of copied
  verbatim. Bilingual like the rest of the app: every string goes through
  i18n.t() under the `docsPage.*` namespace, so literal-audit.test.ts
  covers this route like any other.
-->
<script lang="ts">
  import { PUBLIC_API_BASE_URL } from '$env/static/public';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  const i18n = getI18nContext();
  const REPO_URL = 'https://github.com/montesgp/receipt-risk-detector';

  const IN_SCOPE_KEYS = [
    'fileValidation',
    'hashing',
    'metadata',
    'c2pa',
    'ocr',
    'extraction',
    'validators',
    'scoring'
  ] as const;
  const OUT_OF_SCOPE_KEYS = ['auth', 'orgs', 'history', 'bankConnections', 'autoReconciliation', 'mlModels'] as const;
  const FLOW_STEPS = ['client', 'api', 'analyzers', 'engine', 'response'] as const;
  const STACK_ROWS = ['web', 'api', 'ocr', 'provenance', 'testing'] as const;

  const NAV_SECTIONS = ['product', 'scope', 'architecture', 'api', 'stack'] as const;

  const CURL_EXAMPLE = `curl -X POST ${PUBLIC_API_BASE_URL}/v1/receipts/analyze \\
  -H "Accept: application/json" \\
  -F "file=@receipt.png"`;

  const RESPONSE_EXAMPLE = `{
  "analysis_id": "sha256:4f...",
  "engine_version": "0.1.0",
  "classification": "SUSPICIOUS",
  "risk_score": 74,
  "confidence_score": 86,
  "recommended_action": "PRIORITY_MANUAL_RECONCILIATION",
  "signals": [],
  "extracted_data": {}
}`;
</script>

<svelte:head>
  <title>{i18n.t('docsPage.title')}</title>
</svelte:head>

<main class="page grid gap-10 lg:grid-cols-[220px_1fr] lg:items-start">
  <nav
    aria-label={i18n.t('docsPage.navLabel')}
    class="top-8 hidden flex-col gap-1 text-sm lg:sticky lg:flex"
  >
    {#each NAV_SECTIONS as section (section)}
      <a
        href={`#${section}`}
        class="rounded-ui-sm px-2 py-1.5 text-ui-muted no-underline transition-colors hover:bg-ui-canvas hover:text-ui-fg"
      >
        {i18n.t(`docsPage.nav.${section}`)}
      </a>
    {/each}
  </nav>

  <div class="flex max-w-reading flex-col gap-12">
    <header class="flex flex-col gap-3">
      <h1 class="m-0 text-3xl font-semibold tracking-tight">{i18n.t('docsPage.title')}</h1>
      <p class="m-0 text-ui-muted">{i18n.t('docsPage.intro')}</p>
    </header>

    <section id="product" class="flex flex-col gap-3" aria-labelledby="product-heading">
      <h2 id="product-heading" class="m-0 text-xl font-semibold">{i18n.t('docsPage.product.heading')}</h2>
      <p class="m-0 text-ui-muted">{i18n.t('docsPage.product.body')}</p>
      <p class="m-0 rounded-ui border border-ui-line bg-ui-surface px-4 py-3 font-mono text-sm">
        {i18n.t('docsPage.product.principle')}
      </p>
    </section>

    <section id="scope" class="flex flex-col gap-4" aria-labelledby="scope-heading">
      <h2 id="scope-heading" class="m-0 text-xl font-semibold">{i18n.t('docsPage.scope.heading')}</h2>
      <div class="grid gap-6 sm:grid-cols-2">
        <div class="flex flex-col gap-2">
          <p class="m-0 text-sm font-semibold text-ui-muted">{i18n.t('docsPage.scope.inHeading')}</p>
          <ul class="m-0 flex flex-col gap-1.5 pl-5 text-sm">
            {#each IN_SCOPE_KEYS as key (key)}
              <li>{i18n.t(`docsPage.scope.in.${key}`)}</li>
            {/each}
          </ul>
        </div>
        <div class="flex flex-col gap-2">
          <p class="m-0 text-sm font-semibold text-ui-muted">{i18n.t('docsPage.scope.outHeading')}</p>
          <ul class="m-0 flex flex-col gap-1.5 pl-5 text-sm text-ui-muted">
            {#each OUT_OF_SCOPE_KEYS as key (key)}
              <li>{i18n.t(`docsPage.scope.out.${key}`)}</li>
            {/each}
          </ul>
        </div>
      </div>
    </section>

    <section id="architecture" class="flex flex-col gap-3" aria-labelledby="architecture-heading">
      <h2 id="architecture-heading" class="m-0 text-xl font-semibold">{i18n.t('docsPage.architecture.heading')}</h2>
      <p class="m-0 text-ui-muted">{i18n.t('docsPage.architecture.body')}</p>
      <ol class="m-0 flex flex-col gap-2 rounded-ui border border-ui-line bg-ui-surface p-4 text-sm">
        {#each FLOW_STEPS as step, index (step)}
          <li class="flex items-center gap-3">
            <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-ui-line font-mono text-xs tabular-nums">{index + 1}</span>
            {i18n.t(`docsPage.architecture.flow.${step}`)}
          </li>
        {/each}
      </ol>
      <a href={`${REPO_URL}/blob/main/docs/ARCHITECTURE.md`} target="_blank" rel="noopener noreferrer" class="text-sm font-medium underline underline-offset-2">
        {i18n.t('docsPage.architecture.fullDocsLink')}
      </a>
    </section>

    <section id="api" class="flex flex-col gap-4" aria-labelledby="api-heading">
      <h2 id="api-heading" class="m-0 text-xl font-semibold">{i18n.t('docsPage.api.heading')}</h2>
      <p class="m-0 text-ui-muted">{i18n.t('docsPage.api.body')}</p>

      <div class="flex flex-col gap-2">
        <p class="m-0 text-sm font-semibold text-ui-muted">{i18n.t('docsPage.api.requestLabel')}</p>
        <pre class="overflow-x-auto rounded-ui border border-ui-line bg-ui-surface p-4 text-sm"><code>{CURL_EXAMPLE}</code></pre>
      </div>

      <div class="flex flex-col gap-2">
        <p class="m-0 text-sm font-semibold text-ui-muted">{i18n.t('docsPage.api.responseLabel')}</p>
        <pre class="overflow-x-auto rounded-ui border border-ui-line bg-ui-surface p-4 text-sm"><code>{RESPONSE_EXAMPLE}</code></pre>
      </div>

      <p class="m-0 text-sm text-ui-muted">{i18n.t('docsPage.api.note')}</p>

      <div class="flex flex-wrap gap-3">
        <a href={`${PUBLIC_API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer" class="btn-secondary">
          {i18n.t('docsPage.api.swaggerLink')}
        </a>
        <a href={`${REPO_URL}/blob/main/docs/API.md`} target="_blank" rel="noopener noreferrer" class="btn-secondary">
          {i18n.t('docsPage.api.referenceLink')}
        </a>
      </div>
    </section>

    <section id="stack" class="flex flex-col gap-4" aria-labelledby="stack-heading">
      <h2 id="stack-heading" class="m-0 text-xl font-semibold">{i18n.t('docsPage.stack.heading')}</h2>
      <dl class="m-0 grid grid-cols-[max-content_1fr] items-baseline gap-x-6 gap-y-2 text-sm">
        {#each STACK_ROWS as row (row)}
          <dt class="whitespace-nowrap text-ui-muted">{i18n.t(`docsPage.stack.${row}Label`)}</dt>
          <dd class="m-0">{i18n.t(`docsPage.stack.${row}Value`)}</dd>
        {/each}
      </dl>
      <p class="m-0 text-sm text-ui-muted">{i18n.t('docsPage.stack.license')}</p>
      <div class="flex flex-wrap gap-3">
        <a href={REPO_URL} target="_blank" rel="noopener noreferrer" class="btn-secondary">
          {i18n.t('docsPage.stack.repoLink')}
        </a>
      </div>
    </section>
  </div>
</main>
