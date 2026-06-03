from __future__ import annotations

import csv
import importlib.util
from collections import defaultdict
from pathlib import Path

from .utils import clean_code, ensure_dir, read_json, slugify_name, write_json

SERIES_COLUMNS = [
    "date",
    "dataset_type",
    "asset_code",
    "asset_name",
    "metric_name",
    "metric_value",
]


class ManifestStore:
    def __init__(self, state_root: Path) -> None:
        self.state_root = ensure_dir(state_root)
        self.downloads_path = self.state_root / "downloads_manifest.json"
        self.asset_registry_path = self.state_root / "asset_registry.json"
        self.downloads = read_json(self.downloads_path, [])
        self.asset_registry = read_json(self.asset_registry_path, {})

    def save(self) -> None:
        write_json(self.downloads_path, self.downloads)
        write_json(self.asset_registry_path, self.asset_registry)

    def has_file(self, file_id: str) -> bool:
        return any(
            item.get("file_id") == file_id and item.get("status") == "downloaded"
            for item in self.downloads
        )

    def upsert_download(self, row: dict) -> None:
        existing = next((item for item in self.downloads if item.get("file_id") == row["file_id"]), None)
        if existing is None:
            self.downloads.append(row)
        else:
            existing.update(row)

    def registry_key(self, dataset_type: str, asset_code: str, asset_name: str) -> str:
        return f"{dataset_type}::{asset_code}::{asset_name}"


class SeriesStore:
    def __init__(self, storage_root: Path, manifest_store: ManifestStore) -> None:
        self.storage_root = ensure_dir(storage_root)
        self.manifest_store = manifest_store
        self.backend = "parquet" if _has_parquet_support() else "csv"

    def series_dir(self, dataset_type: str) -> Path:
        return ensure_dir(self.storage_root / "series" / dataset_type)

    def raw_dir(self, as_of_date: str) -> Path:
        return ensure_dir(self.storage_root / "raw" / as_of_date)

    def append_series(self, records: list[dict[str, str]]) -> list[Path]:
        records_by_asset: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
        code_names: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in records:
            key = (row["dataset_type"], row["asset_code"], row["asset_name"])
            records_by_asset[key].append(row)
            code_names[(row["dataset_type"], row["asset_code"])].add(row["asset_name"])

        existing_code_names: dict[tuple[str, str], set[str]] = defaultdict(set)
        for registry_key in self.manifest_store.asset_registry:
            dataset_type, asset_code, asset_name = registry_key.split("::", 2)
            existing_code_names[(dataset_type, asset_code)].add(asset_name)

        written_paths: list[Path] = []
        for (dataset_type, asset_code), names in code_names.items():
            merged_names = names | existing_code_names[(dataset_type, asset_code)]
            if len(merged_names) > 1:
                self._materialize_collision(dataset_type, asset_code, merged_names)

        for key, asset_rows in records_by_asset.items():
            dataset_type, asset_code, asset_name = key
            series_path = self._resolve_series_path(dataset_type, asset_code, asset_name)
            self._append_deduplicated_rows(series_path, asset_rows)
            written_paths.append(series_path)
        self.manifest_store.save()
        return written_paths

    def _resolve_series_path(self, dataset_type: str, asset_code: str, asset_name: str) -> Path:
        registry_key = self.manifest_store.registry_key(dataset_type, asset_code, asset_name)
        if registry_key in self.manifest_store.asset_registry:
            return Path(self.manifest_store.asset_registry[registry_key])

        series_path = self._candidate_series_path(dataset_type, asset_code, asset_name)
        self.manifest_store.asset_registry[registry_key] = str(series_path)
        return series_path

    def _candidate_series_path(self, dataset_type: str, asset_code: str, asset_name: str) -> Path:
        directory = self.series_dir(dataset_type)
        ext = ".parquet" if self.backend == "parquet" else ".csv"
        base_name = clean_code(asset_code)
        collisions = [
            key
            for key in self.manifest_store.asset_registry
            if key.startswith(f"{dataset_type}::{asset_code}::")
        ]
        if not collisions:
            return directory / f"{base_name}{ext}"
        return directory / f"{base_name}__{slugify_name(asset_name)}{ext}"

    def _materialize_collision(self, dataset_type: str, asset_code: str, merged_names: set[str]) -> None:
        for asset_name in sorted(merged_names):
            registry_key = self.manifest_store.registry_key(dataset_type, asset_code, asset_name)
            current = self.manifest_store.asset_registry.get(registry_key)
            target = self.series_dir(dataset_type) / f"{clean_code(asset_code)}__{slugify_name(asset_name)}.{self.backend}"
            if current is None:
                self.manifest_store.asset_registry[registry_key] = str(target)
                continue
            current_path = Path(current)
            if current_path == target:
                continue
            if current_path.exists() and not target.exists():
                current_path.rename(target)
            self.manifest_store.asset_registry[registry_key] = str(target)

    def _append_deduplicated_rows(self, path: Path, rows: list[dict[str, str]]) -> None:
        ensure_dir(path.parent)
        if self.backend == "parquet":
            self._append_parquet_rows(path, rows)
            return

        existing_rows = self._read_csv_rows(path)
        existing_keys = {self._row_key(row) for row in existing_rows}

        for row in rows:
            row_key = self._row_key(row)
            if row_key not in existing_keys:
                existing_rows.append(row)
                existing_keys.add(row_key)

        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=SERIES_COLUMNS)
            writer.writeheader()
            writer.writerows(existing_rows)

    def _read_csv_rows(self, path: Path) -> list[dict[str, str]]:
        existing_rows: list[dict[str, str]] = []
        if path.exists():
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                existing_rows.extend(reader)
        return existing_rows

    def _append_parquet_rows(self, path: Path, rows: list[dict[str, str]]) -> None:
        import pandas as pd

        if path.exists():
            current_df = pd.read_parquet(path)
            existing_rows = current_df.to_dict(orient="records")
        else:
            existing_rows = []

        existing_keys = {self._row_key(row) for row in existing_rows}
        for row in rows:
            row_key = self._row_key(row)
            if row_key not in existing_keys:
                existing_rows.append(row)
                existing_keys.add(row_key)

        pd.DataFrame(existing_rows, columns=SERIES_COLUMNS).to_parquet(path, index=False)

    @staticmethod
    def _row_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
        return (
            row["dataset_type"],
            row["asset_code"],
            row["asset_name"],
            row["date"],
            row["metric_name"],
        )


def _has_parquet_support() -> bool:
    return bool(importlib.util.find_spec("pandas")) and bool(importlib.util.find_spec("pyarrow"))
