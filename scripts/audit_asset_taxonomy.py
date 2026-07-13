#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.config import load_dashboard_config
from dashboard.data_loader import load_market_map_rows
from dashboard.taxonomy import load_asset_taxonomy, load_taxonomy_registry, normalize_asset_identity


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate taxonomy schema and optional live asset coverage")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--catalog", default=str(ROOT / "metadata" / "asset_taxonomy.csv"))
    parser.add_argument("--registry", default=str(ROOT / "metadata" / "taxonomy_registry.json"))
    parser.add_argument("--catalog-only", action="store_true")
    args = parser.parse_args()

    registry = load_taxonomy_registry(args.registry)
    catalog = load_asset_taxonomy(args.catalog, registry)
    result: dict[str, object] = {
        "catalog_count": len(catalog),
        "catalog_unclassified_count": sum(
            metadata["primary_category"] == "unclassified" for metadata in catalog.values()
        ),
        "catalog_missing_region_count": sum(not metadata["regions"] for metadata in catalog.values()),
        "missing_count": 0,
        "extra_count": 0,
        "missing": [],
        "extra": [],
    }
    failed = bool(result["catalog_unclassified_count"] or result["catalog_missing_region_count"])

    if not args.catalog_only:
        config = load_dashboard_config(args.config)
        rows = load_market_map_rows(config.storage_root, config.market_map)
        live_keys = {
            normalize_asset_identity(row["asset_class"], row["asset_id"], row["asset_name"])
            for row in rows
        }
        catalog_keys = set(catalog)
        missing = sorted(live_keys - catalog_keys)
        extra = sorted(catalog_keys - live_keys)
        result.update(
            {
                "live_asset_count": len(live_keys),
                "missing_count": len(missing),
                "extra_count": len(extra),
                "missing": ["::".join(key) for key in missing[:50]],
                "extra": ["::".join(key) for key in extra[:50]],
            }
        )
        failed = failed or bool(missing)

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
