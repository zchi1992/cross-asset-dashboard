# IBKR portfolio snapshots

Status: implemented and validated.

## Decisions

- Use one-shot official TWS API connections instead of a resident subscription.
- Store one atomically replaced CSV per Shanghai calendar date.
- Run every day at 20:00 and 23:30; expose the same workflow through a manual sync API.
- Keep account IDs, stop losses, aliases, logs, and real snapshots outside version control.
- Display all contract types but exclude OPT, FOP, and BAG from Stop Loss risk.

## Completion evidence

- `make check`: 57 Python tests and 19 frontend tests passed; TypeScript/Vite build and docs-check passed.
- `make smoke`: fixture uvicorn readiness and all core APIs, including `/api/portfolio`, passed.
- `make e2e`: 3 Chromium scenarios passed, including portfolio sync, Stop Loss, and asset detail linkage.
- Live TWS validation remains external because this worktree has no installed IBKR SDK, logged-in TWS, or account ID.
