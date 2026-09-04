<!--
  ui-polish round 3: user-requested clarification that this web app is a
  manual-verification demo of the underlying capability, not the product
  itself — the product is the public, framework-agnostic API, meant for
  bots/apps handling volume (WhatsApp/Telegram bots, back-office tools,
  etc., see BotIntegrationShowcase for the same idea shown as a flow).
  Links to the interactive OpenAPI/Swagger UI FastAPI serves by default at
  `/docs` (never disabled in bootstrap/app.py) and to the versioned
  markdown contract in the repo, for a technical reader who wants the
  static reference instead of trying requests live.
-->
<script lang="ts">
  import { PUBLIC_API_BASE_URL } from '$env/static/public';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  const i18n = getI18nContext();
  const REPO_URL = 'https://github.com/montesgp/receipt-risk-detector';
</script>

<aside class="flex flex-col gap-3 rounded-ui border border-ui-line bg-ui-surface p-6" aria-labelledby="api-callout-heading">
  <p id="api-callout-heading" class="m-0 font-semibold">{i18n.t('apiCallout.heading')}</p>
  <p class="m-0 max-w-reading text-sm text-ui-muted">{i18n.t('apiCallout.body')}</p>
  <div class="flex flex-wrap gap-3">
    <a href={`${PUBLIC_API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer" class="btn-secondary">
      {i18n.t('apiCallout.interactiveDocsLink')}
    </a>
    <a href={`${REPO_URL}/blob/main/docs/API.md`} target="_blank" rel="noopener noreferrer" class="btn-secondary">
      {i18n.t('apiCallout.referenceDocsLink')}
    </a>
  </div>
</aside>
