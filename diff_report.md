# Diff Report - 2026-06-30

## Summary

- Current branch: `codex/20260630-update-readme`
- Comparison target: `origin/main`
- Branch divergence from `origin/main`: local branch has 1 unique commit; `origin/main` has 5 unique commits.
- Pull/merge status: not merged.
- Immediate blocker: local uncommitted changes overlap with files changed on `origin/main`.
- Merge state: no conflict markers were created; Git stopped before merging to avoid overwriting local work.

## Commit Divergence

Local-only commit:

```text
2c3067a Update README for current dashboard workflow
```

Remote-only commits:

```text
9b1afb1 Merge pull request #1 from zchi1992/codex/20260628-harness-engineering
949d1c1 Add dashboard harness engineering workflow
4978310 Merge dashboard playback baseline
f702425 Optimize dashboard playback delivery
6594c07 Update dashboard interaction and funding docs
```

## Local Uncommitted Changes

Local working tree summary:

```text
16 files changed, 212 insertions(+), 60 deletions(-)
```

Changed tracked files:

```text
M backend/app/data_service.py
M backend/app/schemas.py
M config.yaml
M dashboard/config.py
M dashboard/data_loader.py
M dashboard/scoring_rules.py
M frontend/package-lock.json
M frontend/src/App.tsx
M frontend/src/components/CrossAssetScatter.tsx
M frontend/src/services/contracts.ts
M frontend/src/stores/filterStore.ts
M frontend/src/styles/terminal.css
M frontend/src/utils/filtering.test.ts
M frontend/src/utils/filtering.ts
M src/zsxq_pipeline/signals/funding_lead_score.py
M tests/test_dashboard_market_map.py
```

Untracked:

```text
analyses/
```

Local diff stat:

```text
backend/app/data_service.py                     |  4 ++
backend/app/schemas.py                          |  4 ++
config.yaml                                     |  7 ++-
dashboard/config.py                             |  6 +-
dashboard/data_loader.py                        | 16 ++++++
dashboard/scoring_rules.py                      |  5 +-
frontend/package-lock.json                      | 39 -------------
frontend/src/App.tsx                            | 36 +++++++++---
frontend/src/components/CrossAssetScatter.tsx   |  7 ++-
frontend/src/services/contracts.ts              |  5 ++
frontend/src/stores/filterStore.ts              |  9 ++-
frontend/src/styles/terminal.css                |  2 +-
frontend/src/utils/filtering.test.ts            | 17 ++++++
frontend/src/utils/filtering.ts                 | 20 ++++++-
src/zsxq_pipeline/signals/funding_lead_score.py | 74 +++++++++++++++++++++++++
tests/test_dashboard_market_map.py              | 21 +++++++
```

## Remote Changes Waiting on `origin/main`

Remote diff summary:

```text
43 files changed, 2394 insertions(+), 281 deletions(-)
```

Main remote change areas:

- New agent skills under `.agents/skills/`.
- CI workflow under `.github/workflows/ci.yml`.
- Project documentation and architecture docs.
- `Makefile` workflow targets.
- Backend app/data service readiness, caching, and response behavior.
- Frontend playback/scatter interaction changes.
- Fixture dashboard data and new tests.
- README changes that overlap with the local-only README commit.

Remote diff stat:

```text
.agents/skills/diagnose-data-freshness/SKILL.md    |  36 ++
.agents/skills/diagnose-data-freshness/agents/openai.yaml |   4 +
.agents/skills/prepare-pr-handoff/SKILL.md         |  31 ++
.agents/skills/prepare-pr-handoff/agents/openai.yaml |   4 +
.agents/skills/verify-dashboard/SKILL.md           |  29 ++
.agents/skills/verify-dashboard/agents/openai.yaml |   4 +
.github/workflows/ci.yml                           |  63 +++
.gitignore                                         |   4 +
AGENTS.md                                          |  21 +
ARCHITECTURE.md                                    |  72 +++
CONTEXT_SUMMARY_2026-06-16.md                      | 422 ++++++++++++++++++
Makefile                                           |  33 ++
README.md                                          | 485 ++++++++++++++-------
WORKFLOW.md                                        |  94 ++++
backend/app/data_service.py                        | 103 ++++-
backend/app/main.py                                | 184 +++++---
backend/app/schemas.py                             |   8 +
docs/data-contracts.md                             |  42 ++
docs/exec-plans/active/harness-engineering.md      |  37 ++
docs/exec-plans/index.md                           |   5 +
docs/exec-plans/tech-debt.md                       |  10 +
docs/index.md                                      |  22 +
docs/product/dashboard.md                          |  32 ++
docs/quality-score.md                              |  17 +
docs/reliability.md                                |  35 ++
docs/security.md                                   |  24 +
docs/testing.md                                    |  31 ++
docs/troubleshooting.md                            |  29 ++
frontend/e2e/dashboard.spec.ts                     |  34 ++
frontend/package-lock.json                         |  64 +++
frontend/package.json                              |   2 +
frontend/playwright.config.ts                      |  41 ++
frontend/src/components/CrossAssetScatter.tsx      | 163 ++++++--
frontend/src/styles/terminal.css                   |  37 +-
frontend/vitest.config.ts                          |   7 +
scripts/check_docs.py                              |  79 ++++
scripts/run_fixture_dashboard.sh                   |  10 +
scripts/smoke_dashboard.py                         | 112 +++++
tests/fixtures/dashboard/config.json               |   6 +
tests/fixtures/dashboard/processed/series/core/AAA.csv |  19 +
tests/fixtures/dashboard/processed/series/instruments/BBB.csv |  19 +
tests/test_architecture.py                         |  68 ++++
tests/test_backend_api.py                          | 133 +++++-
```

## Overlapping Files

These files are changed locally and also changed on `origin/main`.

```text
backend/app/data_service.py
backend/app/schemas.py
frontend/package-lock.json
frontend/src/components/CrossAssetScatter.tsx
frontend/src/styles/terminal.css
```

Overlap diff stat, remote side:

```text
backend/app/data_service.py                   | 103 +++++-
backend/app/schemas.py                        |   8 +
frontend/package-lock.json                    |  64 ++++
frontend/src/components/CrossAssetScatter.tsx | 163 +++++++--
frontend/src/styles/terminal.css              |  37 +-
```

Overlap diff stat, local side:

```text
backend/app/data_service.py                   |  4 +++
backend/app/schemas.py                        |  4 +++
frontend/package-lock.json                    | 39 ---------------------------
frontend/src/components/CrossAssetScatter.tsx |  7 +++--
frontend/src/styles/terminal.css              |  2 +-
```

## High-Risk Review Notes

- `frontend/package-lock.json`: local changes delete 39 lines, while remote adds 64 lines. This is the most likely file to need regeneration with the final `package.json` state.
- `frontend/src/components/CrossAssetScatter.tsx`: remote has a large interaction/playback-related change; local edits are small but in the same file.
- `backend/app/data_service.py`: remote substantially changes data loading/readiness/caching behavior; local edits are small but should be reviewed carefully.
- `README.md`: not a working-tree overlap, but the local branch has a README commit while `origin/main` also changed README heavily. A future merge or rebase may produce a commit-level content conflict.

## Useful Commands

View current local uncommitted changes:

```bash
git diff
```

View local changes for one overlap file:

```bash
git diff -- backend/app/data_service.py
```

View remote changes for one overlap file:

```bash
git diff HEAD..origin/main -- backend/app/data_service.py
```

View all overlap files from the remote side:

```bash
git diff HEAD..origin/main -- \
  backend/app/data_service.py \
  backend/app/schemas.py \
  frontend/package-lock.json \
  frontend/src/components/CrossAssetScatter.tsx \
  frontend/src/styles/terminal.css
```

View branch divergence:

```bash
git log --oneline --left-right HEAD...origin/main
```

## Suggested Next Step

Decide what to do with the local uncommitted work before pulling:

1. Commit the local changes on this branch, then merge or rebase `origin/main`.
2. Stash the local changes, pull `origin/main`, then re-apply the stash and resolve any conflicts.
3. Split unrelated local changes into separate commits or branches before merging.

The safest path is usually to commit or stash the current working tree first, then merge/rebase `origin/main` and resolve the five overlapping files deliberately.
