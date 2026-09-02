# Contributor Onboarding Specification

## Purpose

Defines the GitHub Wiki's scope and anti-duplication policy, and the minimal GitHub-facing README additions.

## Requirements

### Requirement: Wiki Scoped to Process and Onboarding Content

The system MUST limit `docs/wiki/` source pages to process and onboarding content — local setup, contribution flow, environment/secrets runbook, and release process — and MUST link to `docs/` for specs, architecture, or design content instead of duplicating it. (Decision D3)

#### Scenario: Wiki page links instead of duplicating
- GIVEN a Wiki page that references architecture or design decisions
- WHEN its content is reviewed
- THEN it contains a link to the corresponding `docs/` file, not a copy of that file's content

#### Scenario: No PRD/ARCHITECTURE/DESIGN duplication
- GIVEN all pages under `docs/wiki/`
- WHEN searched for PRD, ARCHITECTURE, or DESIGN section content
- THEN no page contains a copy of that content; only links to `docs/PRD.md`, `docs/ARCHITECTURE.md`, or design docs appear

#### Scenario: Onboarding topics are covered
- GIVEN the full set of `docs/wiki/` pages
- WHEN checked against the required topic list
- THEN local setup, contribution flow, environment/secrets runbook, and release process each have a page

### Requirement: README GitHub Surface Additions Only

The system MUST preserve the current `README.md` structure and add only a CI badge, a Wiki link, and an Issues link. (Decision D8)

#### Scenario: Existing README sections remain unchanged
- GIVEN the README before this change
- WHEN diffed against the README after this change
- THEN all pre-existing sections and their content remain, with additions limited to the CI badge, Wiki link, and Issues link

#### Scenario: New links resolve to expected surfaces
- GIVEN the updated README
- WHEN the CI badge, Wiki link, and Issues link are followed
- THEN they resolve respectively to the CI workflow status, the repository Wiki, and the repository Issues tab
