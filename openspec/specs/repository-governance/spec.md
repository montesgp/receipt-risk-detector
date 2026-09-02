# Repository Governance Specification

## Purpose

Defines the GitHub repository's existence, branch model, protection rules, label taxonomy, issue/PR templates, and PR-validation gates that enforce `CONTRIBUTING.md`'s gitflow (D5) and issue-granularity (D6) policies. Also defines the reviewable issue-draft artifact produced instead of live issue creation (D4).

## Requirements

### Requirement: Repository Identity

The system MUST define the target repository as public, named `montesgp/receipt-risk-detector`, licensed Apache-2.0. (Decision D1)

#### Scenario: Repo settings checklist names the target
- GIVEN the repo-settings checklist produced by this change
- WHEN a maintainer reads it before running the orchestrator's live-creation step
- THEN it states visibility `public`, name `montesgp/receipt-risk-detector`, and license Apache-2.0

### Requirement: Branch Model and Protection

The system MUST document a two-branch model where `dev` allows direct maintainer push and `main` requires pull-request merges from `dev` with required status checks. (Decision D2)

#### Scenario: Direct push permitted on dev
- GIVEN the branch-protection checklist
- WHEN the maintainer pushes a commit directly to `dev`
- THEN the checklist confirms no protection rule blocks this push

#### Scenario: Main requires PR and passing checks
- GIVEN the branch-protection checklist
- WHEN a merge into `main` is attempted without an approved PR and passing status checks
- THEN the checklist confirms GitHub blocks the merge

### Requirement: Label Taxonomy Manifest

The system MUST commit a single `.github/labels.json` manifest defining `status:approved` and the `type:*` labels (`bug`, `feature`, `docs`, `refactor`, `chore`, `breaking-change`) required by the `branch-pr` workflow, plus a `.github/labels.sh` bootstrap script that upserts them via the `gh` CLI (no `mcp__github__*` label-creation tool exists). (Decision D5)

#### Scenario: Manifest is the single source of truth
- GIVEN `.github/labels.json`
- WHEN a label is needed by `pr-validation.yml` or an issue template
- THEN that label name exists verbatim in `.github/labels.json`

### Requirement: PR and Issue Templates with Validation Gates

The system MUST author `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`, and `.github/workflows/pr-validation.yml` satisfying every automated check the `branch-pr` skill requires: issue-reference check, `status:approved` check, and exactly-one `type:*` label check. (Decision D5)

#### Scenario: PR without linked issue fails validation
- GIVEN a PR opened against `main` or `dev`
- WHEN its body contains no `Closes/Fixes/Resolves #N` reference
- THEN the `pr-validation.yml` "Check Issue Reference" job fails

#### Scenario: PR with unapproved linked issue fails validation
- GIVEN a PR whose body links an issue lacking `status:approved`
- WHEN `pr-validation.yml` runs
- THEN the "Check Issue Has status:approved" job fails

#### Scenario: PR with zero or multiple type labels fails validation
- GIVEN a PR with zero or more than one `type:*` label
- WHEN `pr-validation.yml` runs
- THEN the "Check PR Has type:* Label" job fails

### Requirement: Issue Draft Traceability

The system MUST generate `issue-drafts.md` containing exactly one issue draft per capability spec under `openspec/specs/`, each with a title, summary, and a link to the owning spec file, without copying scenario text into the body. (Decision D6, CONTRIBUTING.md D6)

#### Scenario: One draft per existing capability spec
- GIVEN the 6 archived capability specs in `openspec/specs/`
- WHEN `issue-drafts.md` is generated
- THEN it contains exactly 6 drafts, each linking a distinct spec file

#### Scenario: Draft omits scenario text
- GIVEN a generated issue draft
- WHEN its body is reviewed
- THEN it contains no copied Given/When/Then scenario text, only title, summary, and spec link

### Requirement: No Live Mutation From Apply

The system MUST NOT create, modify, or delete any live GitHub repository, issue, label, or wiki page during the `sdd-apply` phase. (Decision D4)

#### Scenario: Apply phase produces drafts only
- GIVEN `sdd-apply` has no `mcp__github__*` tools
- WHEN the phase completes
- THEN only `issue-drafts.md` and the repo-settings checklist exist as new artifacts, with zero live GitHub API calls made
