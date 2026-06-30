---
name: prepare-pr-handoff
description: Prepare a focused branch for human review by checking Git scope, running required validation, and summarizing evidence and residual risk. Use when Codex is asked to review completed work, make a change PR-ready, or hand off a dashboard or pipeline change without merging it.
---

# Prepare PR Handoff

Follow `AGENTS.md`; this skill does not grant permission to commit, push, create a PR, or merge.

## Workflow

1. Run `git branch --show-current` and `git status --short`.
2. Stop if the branch is `main` or `master` and changes would be required.
3. Inspect `git diff --stat`, the full diff, and `git diff --check`.
4. Verify every changed file belongs to the requested task. Leave unrelated
   user changes untouched.
5. Select validation from `docs/testing.md`:
   - Always run `make check` for code changes.
   - Add `make smoke` for backend/config/data-loading changes.
   - Add `make e2e` for frontend or cross-layer behavior changes.
6. Review for API compatibility, data-fixture independence, secret leakage,
   missing docs, and architecture-rule bypasses.
7. Report branch, files, behavior, exact validation results, known risks,
   uncommitted state, and whether a PR is recommended.

## Handoff boundary

- Do not stage unrelated files.
- Do not weaken tests or branch protections to make a handoff green.
- Do not merge. Commit, push, and PR actions require the user's explicit request
  or an already-authorized workflow.
