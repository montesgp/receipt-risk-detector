# Continuous Delivery Specification

## Purpose

Defines the CI pipeline, minimal API scaffold that gives CI real commands to run, and the Railway deployment configuration mapping branches to environments.

## Requirements

### Requirement: Minimal API Scaffold

The system MUST provide a minimal `apps/api` uv project (Python 3.12+, FastAPI/Pydantic) with one passing pytest, containing no domain or business logic and no imports that violate `AGENTS.md` layering. (Decision D6)

#### Scenario: Scaffold has no domain imports
- GIVEN `apps/api` source files
- WHEN their imports are inspected
- THEN none import a domain or application-layer module, satisfying `AGENTS.md` layering

#### Scenario: One test passes via uv
- GIVEN the `apps/api` scaffold
- WHEN `uv run pytest` executes
- THEN exactly one test runs and passes

### Requirement: CI Workflow Runs Real Commands

The system MUST author `.github/workflows/ci.yml` that lints, type-checks, and runs tests against `apps/api` using the scaffold's real commands, satisfying the `branch-pr` skill's Shellcheck/CI check where applicable. (Decision D5, D6)

#### Scenario: CI fails on a failing test
- GIVEN a PR that breaks the scaffold's pytest
- WHEN `ci.yml` runs
- THEN the workflow reports failure and blocks merge readiness

#### Scenario: CI passes on unmodified scaffold
- GIVEN the scaffold as delivered by this change
- WHEN `ci.yml` runs on `dev` or `main`
- THEN lint, type-check, and test steps all succeed

### Requirement: Railway Deploy Configuration

The system MUST commit `railway.json` describing the `dev`→staging and `main`→production environment mapping, relying on Railway's native GitHub integration (branch-based auto-deploy) rather than a custom GitHub Actions deploy workflow — a token-authenticated `deploy.yml` cannot exist meaningfully before a Railway account/project is linked. No live Railway account, project, or secret is provisioned by this change. (Decision D7 revised by Design A1, ADR 0001)

#### Scenario: Dev branch maps to staging
- GIVEN `railway.json` and Railway's native GitHub integration configured post-linkage
- WHEN a commit lands on `dev`
- THEN the configuration targets the staging environment, not production

#### Scenario: Main branch maps to production
- GIVEN `railway.json` and Railway's native GitHub integration configured post-linkage
- WHEN a commit lands on `main`
- THEN the configuration targets the production environment

#### Scenario: No live provisioning occurs
- GIVEN the deploy configuration files
- WHEN this change is applied
- THEN no Railway account, project, or secret is created; a manual-linkage runbook documents the human follow-up step
