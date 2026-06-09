from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from .client import SessionStore
from .config import Config, load_config
from .pipeline import IngestionPipeline, bootstrap_directories


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zsxq")
    parser.add_argument("--config", default="config.yaml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth = subparsers.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)
    auth_sub.add_parser("init")

    poll = subparsers.add_parser("poll")
    poll_sub = poll.add_subparsers(dest="poll_command", required=True)
    poll_sub.add_parser("once")

    retry = subparsers.add_parser("retry")
    retry_sub = retry.add_subparsers(dest="retry_command", required=True)
    retry_failed = retry_sub.add_parser("failed-downloads")
    retry_failed.add_argument("--min-delay-seconds", type=float, default=120.0)
    retry_failed.add_argument("--max-delay-seconds", type=float, default=360.0)

    backfill = subparsers.add_parser("backfill")
    backfill_sub = backfill.add_subparsers(dest="backfill_command", required=True)
    history = backfill_sub.add_parser("history")
    history.add_argument("--since", default="2026-05-08")
    history.add_argument("--max-pages", type=int, default=100)

    worker = subparsers.add_parser("worker")
    worker_sub = worker.add_subparsers(dest="worker_command", required=True)
    worker_sub.add_parser("run")

    reparse = subparsers.add_parser("reparse")
    reparse.add_argument("target")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    bootstrap_directories(config)
    pipeline = IngestionPipeline(config)

    if args.command == "auth" and args.auth_command == "init":
        return _auth_init(config)
    if args.command == "poll" and args.poll_command == "once":
        return _run_poll_once(config, pipeline)
    if args.command == "retry" and args.retry_command == "failed-downloads":
        result = pipeline.retry_failed_downloads(
            min_delay_seconds=args.min_delay_seconds,
            max_delay_seconds=args.max_delay_seconds,
        )
        print(
            f"downloaded={result.downloaded} skipped={result.skipped} "
            f"parsed={result.parsed} processed={result.processed}"
        )
        return 0
    if args.command == "backfill" and args.backfill_command == "history":
        result = pipeline.backfill_history(since_date=args.since, max_pages=args.max_pages)
        print(
            f"downloaded={result.downloaded} skipped={result.skipped} "
            f"parsed={result.parsed} processed={result.processed}"
        )
        return 0
    if args.command == "worker" and args.worker_command == "run":
        interval = int(config.raw.get("poll_interval_seconds", 1800))
        while True:
            try:
                _run_poll_once(config, pipeline)
            except Exception as exc:
                _log_failure(config, "worker run", exc)
            time.sleep(interval)
    if args.command == "reparse":
        result = pipeline.reparse_path(Path(args.target))
        print(f"parsed={result.parsed} processed={result.processed}")
        return 0
    return 1


def _auth_init(config) -> int:
    session_store = SessionStore(config.state_root)
    cookie = input("请输入知识星球 Cookie: ").strip()
    user_agent = input("请输入 User-Agent（直接回车使用默认值）: ").strip() or "Mozilla/5.0"
    session_store.save(cookie, user_agent)
    print(f"会话已保存到 {session_store.path}")
    return 0


def _run_poll_once(config: Config, pipeline: IngestionPipeline) -> int:
    try:
        result = pipeline.poll_once()
        validation = pipeline.validate_daily_outputs(_today())
        print(
            f"downloaded={result.downloaded} skipped={result.skipped} parsed={result.parsed} "
            f"processed={result.processed} "
            f"validated_date={validation.as_of_date} raw_files={validation.raw_files} "
            f"asset={validation.asset_code} series={validation.series_path}"
        )
        return 0
    except Exception as exc:
        if _is_pending_daily_output(exc):
            _log_pending(config, "poll once", exc)
            return 0
        _log_failure(config, "poll once", exc)
        return 1


def _today() -> str:
    return datetime.now().date().isoformat()


def _is_pending_daily_output(exc: Exception) -> bool:
    return isinstance(exc, ValueError) and str(exc).startswith("no downloaded raw files found for ")


def _log_pending(config: Config, command: str, exc: Exception) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} PENDING {command}: {exc}"
    print(message, file=sys.stderr, flush=True)
    config.logs_root.mkdir(parents=True, exist_ok=True)
    with (config.logs_root / "zsxq.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{message}\n")


def _log_failure(config: Config, command: str, exc: Exception) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{timestamp} FAIL {command}: {type(exc).__name__}: {exc}"
    print(message, file=sys.stderr, flush=True)
    config.logs_root.mkdir(parents=True, exist_ok=True)
    with (config.logs_root / "zsxq.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{message}\n")
