---
tracker:
  kind: linear
  api_key: $LINEAR_API_KEY
  project_slug: Cross Asset Dashboard
  required_labels:
    - symphony
  active_states:
    - Todo
    - In Progress
  terminal_states:
    - Closed
    - Cancelled
    - Canceled
    - Duplicate
    - Done
polling:
  interval_ms: 30000
workspace:
  root: .symphony/workspaces
hooks:
  after_create: |
    repository="${CROSS_ASSET_REPOSITORY:-https://github.com/zchi1992/cross-asset-dashboard.git}"
    git clone --branch main --origin origin "$repository" .
  before_run: |
    git fetch origin --prune
  timeout_ms: 120000
agent:
  # Playwright uses a fixed local port, so parallel workspaces would collide.
  max_concurrent_agents: 1
  max_turns: 12
  max_retry_backoff_ms: 300000
codex:
  command: codex app-server
  approval_policy: never
  thread_sandbox: workspace-write
  turn_sandbox_policy:
    type: workspaceWrite
    networkAccess: true
  turn_timeout_ms: 3600000
  read_timeout_ms: 5000
  stall_timeout_ms: 300000
---
# Cross Asset Dashboard issue

Work on Linear issue **{{ issue.identifier }}: {{ issue.title }}**.

Issue description:

{{ issue.description or "No description was provided. Derive the smallest safe change from the title and repository context." }}

Context:

- Linear state: `{{ issue.state }}`
- Linear branch suggestion: `{{ issue.branch_name or "not provided" }}`
- Symphony attempt: `{{ attempt or 1 }}`

## Required workflow

1. Read `AGENTS.md` first and follow all repository Git, scope, documentation,
   and validation rules. Then open only the architecture or runbook documents
   needed for this issue.
2. Inspect the current branch and worktree before editing. Never modify,
   commit, or push directly on `main` or `master`. If a task branch is needed,
   use the Linear branch suggestion only when it complies with `AGENTS.md`;
   otherwise create the prescribed `codex/YYYYMMDD-task-name` branch.
3. Keep the change focused on the issue and preserve unrelated user changes.
   Do not upgrade dependencies or perform broad formatting unless the issue
   explicitly requires it.
4. Do not depend on ignored local `data/`. Tests, smoke checks, and E2E checks
   must use `tests/fixtures/dashboard/`.
5. If dependencies are missing, run `make setup`. During implementation, run
   the narrowest relevant checks. Before handoff, run `make check`; also run
   `make smoke` for API/data-path changes and `make e2e` for UI, API-contract,
   or end-to-end behavior changes.
6. Treat acceptance criteria as incomplete until the implementation and
   required validation both pass. Record exact commands, results, and any
   residual risks in the final handoff.
7. Do not commit or push unless the Linear issue explicitly authorizes it.
   Never expose credentials, configuration secrets, or real market data in
   source, logs, tests, or the final response.

## Linear handoff

When the acceptance criteria are met, use an available Linear integration to
move the issue out of `Todo`/`In Progress` into the project's review or handoff
state (prefer `In Review` when that state exists), and remove the `symphony`
label so it is not dispatched again. Do not mark the issue `Done` unless the
issue explicitly authorizes completion.

If work is blocked, leave the repository safe and explain the exact blocker,
the last successful validation, and the smallest action needed from a human.
Move the issue to the project's blocked state when one exists; otherwise leave
a Linear comment and remove the `symphony` label to stop automatic retries.
