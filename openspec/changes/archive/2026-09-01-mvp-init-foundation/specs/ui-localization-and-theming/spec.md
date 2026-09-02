# UI Localization and Theming Specification

## Purpose

Expanded FR-012 (proposal decision D1, user-approved): full bilingual ES/EN UI copy AND a working light/dark theme switcher, superseding the narrower "foundation only" wording in `docs/PRD.md` FR-012.

## Requirements

### Requirement: Full bilingual ES/EN UI copy
User-facing strings MUST be centralized and available in both Spanish and English, with no component restructuring required to add a locale (FR-012 expanded per D1).

#### Scenario: Language switch updates all visible copy
- GIVEN the UI is rendered in Spanish
- WHEN the user switches to English
- THEN every user-facing string (upload flow, results, disclaimers, checklist) renders in English without a page architecture change

#### Scenario: Centralized strings source
- GIVEN a developer adds a new user-facing string
- WHEN the string is added to the centralized copy source
- THEN both locales must define it before release (no orphan-locale strings)

### Requirement: Light/dark theme switcher
The UI MUST provide a working light/dark theme switcher built on the existing semantic color token system (D1; docs/DESIGN.md §6).

#### Scenario: Manual theme toggle
- GIVEN the user opens the theme switcher control
- WHEN they select dark theme
- THEN the UI immediately re-renders using dark-theme semantic tokens (`[data-theme='dark']`)

#### Scenario: System-preference default
- GIVEN a user with no stored theme preference
- WHEN they load the application
- THEN the UI defaults to the operating system's light/dark preference

### Requirement: Persisted user choice
Theme and language selections MUST persist across sessions on the same device (D1).

#### Scenario: Theme persists after reload
- GIVEN a user manually selected dark theme
- WHEN they reload the application later
- THEN the UI loads in dark theme without requiring re-selection

#### Scenario: Language persists after reload
- GIVEN a user manually selected English
- WHEN they reload the application later
- THEN the UI loads in English without requiring re-selection

### Requirement: Accessible switcher controls
The language and theme switchers MUST be keyboard-operable, expose visible focus states, use WCAG AA color contrast, and never communicate their current state by color alone (NFR-004; DESIGN.md §12, §13).

#### Scenario: Switchers are keyboard-operable with visible focus
- GIVEN a keyboard-only user tabs to the language or theme switcher
- WHEN the control receives focus and is activated with the keyboard
- THEN a visible focus state appears using `--color-focus`, and the switch completes without a pointer device (NFR-004)

#### Scenario: State change is announced and not color-only
- GIVEN the user changes the theme or language
- WHEN the switch takes effect
- THEN the new state is exposed via `aria-pressed`/`aria-checked` and announced through the existing ARIA live region, without relying on color alone to convey the current state (NFR-004)

## Key Learnings

1. D1 is a user-approved scope expansion over the original PRD FR-012 wording ("Spanish-first foundation only"); this spec documents the expanded scope, and `docs/PRD.md` is back-annotated separately.
2. Both switchers reuse the existing DESIGN.md token system rather than introducing new visual primitives.
