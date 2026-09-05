<!--
  DESIGN.md §4.4 result priority item 6 "Analyzer and version details".
  Two reading speeds principle (§2.3): kept available for audit, not the
  first thing a beneficiary sees.

  ui-polish round 3 (issue #34): each analyzer row gets a hover/focus
  helper describing what it actually checks. Deliberately shown, not
  hidden -- this is an MVP technical demo, not a production security
  boundary, and several of these analyzers (checksum validators, the C2PA
  signature check) are unevadable by construction regardless of whether a
  user reads the description.
-->
<script lang="ts">
  import type { AnalyzerStatusModel } from '$lib/api/types';
  import { getI18nContext } from '$lib/i18n/i18n.svelte';

  let {
    engineVersion,
    rulesetVersion,
    analyzerStatuses
  }: {
    engineVersion: string;
    rulesetVersion: string;
    analyzerStatuses: AnalyzerStatusModel[];
  } = $props();

  const i18n = getI18nContext();

  // Only the analyzers this app actually ships get a help key -- an unknown
  // future analyzer name falls back to no tooltip rather than a broken t()
  // lookup, same "unknown code has no catalogued key" convention as
  // enum-map.ts.
  const KNOWN_ANALYZERS = new Set([
    'paddleocr-onnx',
    'exiftool',
    'c2pa',
    'mobilenetv3-embedding'
  ]);

  function helpKey(analyzer: string): string | undefined {
    return KNOWN_ANALYZERS.has(analyzer) ? `result.technical.help.${analyzer}` : undefined;
  }
</script>

<details class="rounded-ui border border-ui-line px-4 py-3">
  <summary class="cursor-pointer select-none font-medium">{i18n.t('result.technical.summary')}</summary>
  <dl class="my-4 grid grid-cols-[max-content_1fr] items-baseline gap-x-4 gap-y-2">
    <dt class="whitespace-nowrap text-ui-muted">{i18n.t('result.technical.engineVersion')}</dt>
    <dd class="m-0 font-mono text-sm"><code>{engineVersion}</code></dd>
    <dt class="whitespace-nowrap text-ui-muted">{i18n.t('result.technical.rulesetVersion')}</dt>
    <dd class="m-0 font-mono text-sm"><code>{rulesetVersion}</code></dd>
  </dl>

  {#if analyzerStatuses.length > 0}
    <table class="w-full border-collapse text-sm">
      <thead>
        <tr>
          <th scope="col" class="border-b border-ui-line px-3 py-2 text-left">{i18n.t('result.technical.analyzerColumn')}</th>
          <th scope="col" class="border-b border-ui-line px-3 py-2 text-left">{i18n.t('result.technical.statusColumn')}</th>
          <th scope="col" class="border-b border-ui-line px-3 py-2 text-left">{i18n.t('result.technical.durationColumn')}</th>
        </tr>
      </thead>
      <tbody>
        {#each analyzerStatuses as analyzer (analyzer.analyzer)}
          {@const key = helpKey(analyzer.analyzer)}
          <tr>
            <td class="border-b border-ui-line px-3 py-2 text-left">
              <span class="inline-flex items-center gap-1.5">
                {analyzer.analyzer}
                {#if key}
                  <span class="group relative inline-flex">
                    <button
                      type="button"
                      class="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-ui-line text-[10px] leading-none text-ui-muted"
                      aria-label={i18n.t('result.technical.helpLabel', { analyzer: analyzer.analyzer })}
                      aria-describedby={`analyzer-help-${analyzer.analyzer}`}
                    >?</button>
                    <span
                      id={`analyzer-help-${analyzer.analyzer}`}
                      role="tooltip"
                      class="pointer-events-none absolute left-0 top-full z-10 mt-2 w-64 rounded-ui border border-ui-line bg-ui-surface p-2 text-xs font-normal text-ui-muted opacity-0 shadow-sm transition-opacity group-hover:opacity-100 group-focus-within:opacity-100"
                    >{i18n.t(key)}</span>
                  </span>
                {/if}
              </span>
            </td>
            <td class="border-b border-ui-line px-3 py-2 text-left">{analyzer.status}</td>
            <td class="border-b border-ui-line px-3 py-2 text-left">{analyzer.duration_ms} ms</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</details>
