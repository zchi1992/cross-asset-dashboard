---
name: verify-dashboard
description: Validate dashboard and API changes with fixture-based unit, smoke, and Playwright checks. Use when Codex changes backend/app, dashboard, frontend, configuration loading, API contracts, UI interactions, or needs reproducible proof that the Local Asset Terminal works without real market data.
---

# Verify Dashboard

Use the smallest validation set that proves the changed behavior, then report exact commands and results.

## Workflow

1. Read `docs/testing.md` and the relevant product or data contract.
2. Confirm tests use `tests/fixtures/dashboard/`, never the ignored root `data/`.
3. Run validation by change type:
   - Documentation only: `make docs-check`.
   - Python, API, config, or data loading: `make check` and `make smoke`.
   - Frontend behavior or styling: `make check` and `make e2e`.
   - Cross-layer changes: run all three targets.
4. For direct API diagnosis, use `curl --noproxy '*'` against loopback.
5. On E2E failure, inspect `frontend/test-results/` and
   `frontend/playwright-report/` before changing code.
6. Report the command, pass/fail count, and any intentionally untested behavior.

## Required evidence

- API changes preserve existing response fields unless the task explicitly changes the contract.
- `/api/health` proves liveness; `/api/ready` proves fixture data is usable.
- Browser evidence covers loading, filtering, scatter rendering, playback, and error state.
- Build-size warnings remain visible but do not fail the first-stage harness.
