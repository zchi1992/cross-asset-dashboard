from __future__ import annotations

import argparse
import json

from . import data_service
from .portfolio_service import PortfolioService, PortfolioServiceError, load_portfolio_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Create one IBKR portfolio snapshot")
    parser.add_argument(
        "--source",
        choices=["manual", "scheduled_2000", "scheduled_2330"],
        default="manual",
    )
    parser.add_argument("--lock-timeout", type=float, default=60)
    parser.add_argument("--config")
    args = parser.parse_args()

    config_path = data_service.resolve_config_path(args.config)
    storage_root, state_root, portfolio_config = data_service.get_portfolio_context(config_path)
    service = PortfolioService(
        load_portfolio_settings(storage_root, state_root, portfolio_config),
        assets_provider=lambda: data_service.get_asset_identities(config_path),
    )
    try:
        response = service.sync(args.source, lock_timeout=args.lock_timeout)
    except PortfolioServiceError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "status": response.status,
                "snapshot_date": response.snapshot_date,
                "captured_at": response.captured_at,
                "source_file": response.source_file,
                "position_count": len(response.positions),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
