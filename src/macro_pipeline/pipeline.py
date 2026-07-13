from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Callable

import requests

from src.zsxq_pipeline.config import Config

from .providers import (
    UnconfiguredSource,
    fetch_china,
    fetch_ecb,
    fetch_fred_credit,
    fetch_japan,
    fetch_ofr,
    fetch_uk,
    fetch_us_treasury,
)


CURVE_FIELDS = ["date", "region", "region_name", "tenor_years", "value", "unit", "curve_type", "source_id", "source_name", "source_url"]
CREDIT_FIELDS = ["date", "series_id", "label", "value", "unit", "frequency", "source_id", "source_name", "source_url"]


class MacroPipeline:
    def __init__(self, config: Config, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "cross-asset-dashboard/1.0 macro-monitor"})

    def run(self, start: date, end: date) -> dict[str, int]:
        processed_root = self.config.storage_root / "processed" / "macro"
        raw_root = self.config.storage_root / "raw" / "macro"
        state_path = self.config.state_root / "macro_sources.json"
        processed_root.mkdir(parents=True, exist_ok=True)
        raw_root.mkdir(parents=True, exist_ok=True)
        self.config.state_root.mkdir(parents=True, exist_ok=True)

        curve_rows: list[dict[str, str]] = []
        credit_rows: list[dict[str, str]] = []
        states = {item.get("source_id"): item for item in _read_json_list(state_path)}
        providers: list[tuple[str, str, Callable, str]] = [
            ("us_treasury", "US Treasury", fetch_us_treasury, "curve"),
            ("ecb", "ECB", fetch_ecb, "curve"),
            ("chinabond", "财政部 / 中债", fetch_china, "curve"),
            ("japan_mof", "Japan MOF", fetch_japan, "curve"),
            ("boe", "Bank of England", fetch_uk, "curve"),
            ("fred", "FRED", fetch_fred_credit, "credit"),
            ("ofr", "Office of Financial Research", fetch_ofr, "credit"),
        ]
        for source_id, source_name, provider, kind in providers:
            try:
                rows, raw = provider(self.session, start, end)
                _write_raw(raw_root, source_id, raw)
                (curve_rows if kind == "curve" else credit_rows).extend(rows)
                latest = max((row["date"] for row in rows), default=None)
                lagging = latest is None or latest < (end - timedelta(days=4)).isoformat()
                states[source_id] = _state(
                    source_id,
                    source_name,
                    "lagging" if lagging else "fresh",
                    latest,
                    "latest observation is outside the daily freshness window" if lagging else None,
                )
            except UnconfiguredSource as exc:
                states[source_id] = _state(source_id, source_name, "unconfigured", None, str(exc))
            except Exception as exc:
                previous = states.get(source_id, {})
                states[source_id] = {
                    **_state(source_id, source_name, "error", previous.get("latest_observation_at"), f"{type(exc).__name__}: {exc}"),
                    "last_success_at": previous.get("last_success_at"),
                }

        _upsert_csv(processed_root / "curve_points.csv", curve_rows, CURVE_FIELDS, ("date", "region", "tenor_years"))
        _upsert_csv(processed_root / "credit.csv", credit_rows, CREDIT_FIELDS, ("date", "series_id"))
        _atomic_json(state_path, sorted(states.values(), key=lambda item: item["source_id"]))
        return {"curve_rows": len(curve_rows), "credit_rows": len(credit_rows), "sources": len(providers)}


def _state(source_id, source_name, status, latest, message):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "source_id": source_id,
        "source_name": source_name,
        "status": status,
        "last_success_at": now if status in {"fresh", "lagging"} else None,
        "latest_observation_at": latest,
        "message": message,
    }


def _write_raw(root: Path, source_id: str, payload: bytes) -> None:
    target_dir = root / source_id
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    (target_dir / f"{stamp}.bin").write_bytes(payload)


def _upsert_csv(path: Path, new_rows, fields, keys):
    rows = []
    if path.exists():
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    merged = {tuple(row.get(key, "") for key in keys): row for row in rows}
    for row in new_rows:
        merged[tuple(row.get(key, "") for key in keys)] = row
    ordered = sorted(merged.values(), key=lambda row: tuple(row.get(key, "") for key in keys))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(ordered)
    temporary.replace(path)


def _atomic_json(path: Path, value) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _read_json_list(path: Path):
    if not path.exists():
        return []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []
