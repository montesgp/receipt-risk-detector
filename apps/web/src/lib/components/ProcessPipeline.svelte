<!--
  ui-polish round 2, item 3+6: the six-step explainer must stay reachable
  across every workspace state (it previously disappeared once a file was
  selected/analyzed), and a second tab shows the same public API consumed
  from a messaging bot. Always mounted by +page.svelte, outside every
  workspace-state branch. `PipelineExplainer` itself is unchanged (its own
  unit test renders it standalone), just nested as this tablist's first
  panel.
-->
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  import PipelineExplainer from './PipelineExplainer.svelte';
  import BotIntegrationShowcase from './BotIntegrationShowcase.svelte';

  const i18n = getI18nContext();
  const TABS = ['pipeline', 'integration'] as const;
  type Tab = (typeof TABS)[number];

  let active = $state<Tab>('pipeline');

  function select(tab: Tab): void {
    active = tab;
  }

  function handleKeydown(event: KeyboardEvent, index: number): void {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
    event.preventDefault();
    const delta = event.key === 'ArrowRight' ? 1 : -1;
    const nextIndex = (index + delta + TABS.length) % TABS.length;
    select(TABS[nextIndex]);
  }
</script>

<section class="flex flex-col gap-4 border-t border-ui-line pt-8">
  <div
    role="tablist"
    aria-label={i18n.t('pipeline.section.heading')}
    class="inline-flex w-fit gap-1 rounded-ui border border-ui-line bg-ui-surface p-1"
  >
    {#each TABS as tab, index (tab)}
      <button
        type="button"
        role="tab"
        id={`pipeline-tab-${tab}`}
        aria-selected={active === tab}
        aria-controls={`pipeline-panel-${tab}`}
        tabindex={active === tab ? 0 : -1}
        class="rounded-ui-sm px-3 py-2 text-sm font-medium transition-colors"
        class:bg-ui-action={active === tab}
        class:text-ui-action-fg={active === tab}
        class:bg-transparent={active !== tab}
        class:text-ui-muted={active !== tab}
        onclick={() => select(tab)}
        onkeydown={(event) => handleKeydown(event, index)}
      >
        {i18n.t(`pipeline.tab.${tab}`)}
      </button>
    {/each}
  </div>

  <div
    id="pipeline-panel-pipeline"
    role="tabpanel"
    aria-labelledby="pipeline-tab-pipeline"
    hidden={active !== 'pipeline'}
  >
    <PipelineExplainer />
  </div>
  <div
    id="pipeline-panel-integration"
    role="tabpanel"
    aria-labelledby="pipeline-tab-integration"
    hidden={active !== 'integration'}
  >
    <BotIntegrationShowcase />
  </div>
</section>
