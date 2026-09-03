<!--
  Shared ARIA live region (DESIGN.md §14 checklist; spec "State change is
  announced and not color-only"). Referenced but not built in slice 2 — that
  slice used a local `role="status"` workaround inside `ThemeSwitcher`
  (documented there as an interim choice) because this component was out of
  scope until slice 4. `ThemeSwitcher`/`LanguageSwitcher` now render this
  instead of duplicating the markup.

  `visuallyHidden` defaults to true (announcement-only, e.g. the switchers'
  "Tema: Oscuro" confirmation). `ProcessingStages` keeps its own inline
  `role="status"` region as-is: its text is part of the *visible* UI, not an
  announcement-only region, so it is a different use case and migrating it
  risked an unnecessary regression for no accessibility benefit.
-->
<script lang="ts">
  let {
    message,
    politeness = 'polite',
    visuallyHidden = true
  }: {
    message: string;
    politeness?: 'polite' | 'assertive';
    visuallyHidden?: boolean;
  } = $props();
</script>

<p class="live-region" class:visually-hidden={visuallyHidden} role="status" aria-live={politeness}>
  {message}
</p>

<style>
  .live-region {
    margin: 0;
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
</style>
