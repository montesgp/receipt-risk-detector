# ADR 0001: Railway as the concrete deployment target

## Status

Accepted

## Context

`docs/ARCHITECTURE.md` §12 documents hosting as architecture-agnostic: "Railway, Cloud Run, Azure
Container Apps or a VM can host the containers. Hosting choice is not an MVP architecture dependency."
That framing is still correct at the container-boundary level, but MVP1 needs one concrete target to
write a gitflow policy against (`CONTRIBUTING.md`, proposal decision D5) and to produce a deployment
diagram (`docs/diagrams/deployment-railway.drawio`). Leaving the target unnamed would block both.

## Decision

Adopt Railway as the concrete deployment target for MVP1, with two environments:

- `dev` branch → Railway staging environment.
- `main` branch → Railway production environment.

This is recorded as a deployment preference, not a new architectural dependency. Nothing in the
container/adapter boundaries (`docs/ARCHITECTURE.md` §5–§7) requires a Railway-specific primitive;
the deployment view (`docs/ARCHITECTURE.md` §12: `Internet → edge → web/API containers → ephemeral
filesystem/local OCR`) remains portable to Cloud Run, Azure Container Apps or a VM without redesign.

## Consequences

- `CONTRIBUTING.md` documents the `dev`→staging, `main`→production gitflow policy (D5) against a real
  target instead of a placeholder.
- `docs/diagrams/deployment-railway.drawio` and its ARCHITECTURE.md §12 annotation name Railway
  explicitly, while the annotation reaffirms that hosting choice is not an architecture dependency.
- Actual Railway project/environment provisioning, secrets and CI/CD wiring are explicitly deferred to
  the future `repo-github-setup` change (this change is documentation-only; the repository does not
  exist yet).
- If Railway is later replaced, only the deployment diagram, the gitflow target names and any
  Railway-specific environment configuration need to change — no domain, application or adapter code
  depends on this choice.

## References

- `docs/ARCHITECTURE.md` §12 (Deployment view)
- `docs/diagrams/deployment-railway.drawio`
- `CONTRIBUTING.md` (Branching policy)
- `openspec/changes/mvp-init-foundation/proposal.md` decision D5
