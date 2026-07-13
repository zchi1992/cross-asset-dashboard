from __future__ import annotations

import argparse
from datetime import date, timedelta

from src.zsxq_pipeline.config import load_config

from .pipeline import MacroPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="macro")
    parser.add_argument("--config", default="config.yaml")
    commands = parser.add_subparsers(dest="command", required=True)
    backfill = commands.add_parser("backfill")
    backfill.add_argument("--years", type=int, default=5)
    poll = commands.add_parser("poll")
    poll.add_subparsers(dest="poll_command", required=True).add_parser("once")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    today = date.today()
    if args.command == "backfill":
        start = today - timedelta(days=365 * max(1, args.years))
    else:
        start = today - timedelta(days=45)
    result = MacroPipeline(load_config(args.config)).run(start, today)
    print(" ".join(f"{key}={value}" for key, value in result.items()))
    return 0
