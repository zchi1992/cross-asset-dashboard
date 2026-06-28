---
name: diagnose-data-freshness
description: Trace dashboard data freshness across downloads, parsed series, processed series, and API output. Use when recent data is missing, `/api/ready` reports no processed data, a poll appears successful but the dashboard is stale, or Codex must identify the earliest broken pipeline stage before proposing a fix.
---

# Diagnose Data Freshness

Find the earliest stage where expected data disappears. Do not treat parsed data as proof that dashboard data is current.

## Workflow

1. Read `ARCHITECTURE.md`, `docs/data-contracts.md`, and
   `docs/troubleshooting.md`.
2. Establish the expected date and dataset type.
3. Inspect stages in order:
   - Download truth: `state/downloads_manifest.json` and `data/raw/<date>/`.
   - Parsed long series: `data/series/core/` and `data/series/instruments/`.
   - Derived dashboard input: `data/processed/series/core/` and
     `data/processed/series/instruments/`.
   - API output: `/api/ready`, `/api/dates`, and `/api/playback`.
4. Compare file timestamps, the maximum `date` in CSVs, and required metric names.
5. Use `curl --noproxy '*'` for loopback checks so local proxy failures do not
   masquerade as application failures.
6. Report the earliest broken boundary, concrete evidence, and the narrowest
   repair. Run polling or rebuild processed data only when the user asks to
   change state or the task explicitly includes repair.

## Failure classification

- No raw file: download is pending, filtered, unauthorized, or failed.
- Raw exists but series is stale: parsing/classification boundary failed.
- Series exists but processed is stale: derived-signal refresh failed.
- Processed is current but API is stale: config path, cache signature, or service
  instance is wrong.
- API is current but browser is stale: frontend request, persisted filters, or
  browser cache is wrong.
