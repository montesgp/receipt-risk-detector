<!--
  Test-only host component mirroring the real composition of
  `+layout.svelte` (owns the `I18n` instance + `LanguageSwitcher`) and
  `+page.svelte` (renders `ResultView` reading the same context). Used by
  `locale-integration.test.ts` to prove that switching language via
  `LanguageSwitcher` re-renders the FULL result screen — ScoreSummary,
  EvidenceList, and ExtractedDataTable together — from shared held state,
  not just each component in isolation.
-->
<script lang="ts">
  import { I18n, setI18nContext } from '$lib/i18n/i18n.svelte';
  import LanguageSwitcher from '$lib/components/LanguageSwitcher.svelte';
  import ResultView from '$lib/components/ResultView.svelte';
  import type { AnalyzeResponse } from '$lib/api/types';

  let { result }: { result: AnalyzeResponse } = $props();

  const i18n = new I18n('es');
  setI18nContext(i18n);
</script>

<LanguageSwitcher />
<ResultView {result} />
