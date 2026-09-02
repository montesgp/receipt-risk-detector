# Repository Settings Checklist (orchestrator-executed, post-review)

This file lists the exact live settings the orchestrator must apply after human review of the
PR produced by this change (`sdd-apply`). Nothing here is executed automatically — no
`mcp__github__*` or Railway API call was made while generating this checklist (D4).

## Repository identity

| Setting | Value |
|---------|-------|
| Owner | `montesgp` |
| Name | `receipt-risk-detector` (user-confirmable, D1) |
| Visibility | `public` |
| License | Apache-2.0 (already present as `LICENSE`) |
| Default branch | `dev` (set only after `dev` is pushed — see rollout order below) |

## Repo-level settings payload

`PATCH /repos/montesgp/receipt-risk-detector`:

```json
{
  "default_branch": "dev",
  "has_issues": true,
  "has_wiki": true,
  "has_projects": false,
  "has_discussions": false,
  "allow_merge_commit": false,
  "allow_squash_merge": true,
  "allow_rebase_merge": true,
  "allow_auto_merge": true,
  "delete_branch_on_merge": true
}
```

## Branch protection — `dev` (minimal)

`PUT /repos/montesgp/receipt-risk-detector/branches/dev/protection`:

```json
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```

Effect: maintainer direct push allowed; force-push and deletion blocked.

## Branch protection — `main` (strict)

`PUT /repos/montesgp/receipt-risk-detector/branches/main/protection`:

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Check Issue Reference",
      "Check Issue Has status:approved",
      "Check PR Has type:* Label",
      "Check Source Branch",
      "API Lint and Test"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```

Notes: `required_approving_review_count: 0` because solo maintainer; raise to 1 when a second
contributor joins. `enforce_admins: false` leaves an emergency escape hatch.

## Load-bearing order (design "Migration / Rollout")

Applying branch protection before the target branch exists returns `404`. Execute in this order:

1. `git init`, commit on `main`, create the GitHub repository, push `main`.
2. Branch and push `dev`; set `dev` as the default branch (repo-level settings payload above).
3. Run `.github/labels.sh montesgp/receipt-risk-detector` (labels must exist before any PR needs
   a `type:*` label).
4. Apply `main` protection, then `dev` protection.
5. Publish issues from `openspec/changes/repo-github-setup/issue-drafts.md`; apply
   `status:approved` to whichever issue is selected next.
6. Push `docs/wiki/*.md` to the `receipt-risk-detector.wiki.git` repository.
7. Link Railway manually (account/project creation is out of design control).

## Verification

After applying, diff the live state against the payloads above:

```bash
gh api repos/montesgp/receipt-risk-detector/branches/main/protection
gh api repos/montesgp/receipt-risk-detector/branches/dev/protection
```
