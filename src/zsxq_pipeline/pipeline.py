from __future__ import annotations

import csv
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .client import FileCandidate, SessionStore, ZsxqClient
from .config import Config
from .filtering import classify_dataset, match_filename
from .storage import ManifestStore, SeriesStore
from .utils import copy_file, ensure_dir, normalize_date, parse_date_from_filename, sha256_file
from .xlsx_parser import parse_metrics_from_workbook


@dataclass
class PipelineResult:
    downloaded: int = 0
    skipped: int = 0
    parsed: int = 0


@dataclass
class ValidationResult:
    as_of_date: str
    raw_files: int
    series_path: Path
    asset_code: str
    last_date: str


class IngestionPipeline:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.manifest_store = ManifestStore(config.state_root)
        self.series_store = SeriesStore(config.storage_root, self.manifest_store)
        self.session_store = SessionStore(config.state_root)

    def reparse_path(self, target: str | Path) -> PipelineResult:
        target_path = Path(target)
        result = PipelineResult()
        files = sorted(target_path.glob("*.xlsx")) if target_path.is_dir() else [target_path]
        for path in files:
            if path.suffix.lower() not in self.config.raw.get("file_extensions", [".xlsx", ".xls"]):
                continue
            metadata = FileCandidate(
                channel_id="local",
                post_id=path.stem,
                file_id=f"local::{path.name}",
                filename=path.name,
                published_at="",
            )
            self._ingest_local_file(path, metadata)
            result.parsed += 1
        return result

    def poll_once(self) -> PipelineResult:
        session = self.session_store.load()
        client = ZsxqClient(self.config.raw["zsxq"], session)
        result = PipelineResult()
        for group_id in self.config.raw["zsxq"].get("group_ids", []):
            for candidate in client.fetch_group_files(str(group_id)):
                if not self._should_download(candidate):
                    self._record_skip(candidate, "skipped_by_name_filter")
                    result.skipped += 1
                    continue
                if self.manifest_store.has_file(candidate.file_id):
                    result.skipped += 1
                    continue
                try:
                    downloaded_path = self._download_candidate(client, candidate)
                    self._parse_and_store(downloaded_path, candidate)
                    result.downloaded += 1
                    result.parsed += 1
                except Exception as exc:
                    self._record_skip(candidate, f"download_failed:{type(exc).__name__}")
                    self._log_failure("poll once candidate", exc, candidate)
                    result.skipped += 1
        self.manifest_store.save()
        return result

    def backfill_history(self, *, since_date: str, max_pages: int = 100) -> PipelineResult:
        session = self.session_store.load()
        client = ZsxqClient(self.config.raw["zsxq"], session)
        result = PipelineResult()
        keywords = self._history_search_keywords()
        for group_id in self.config.raw["zsxq"].get("group_ids", []):
            try:
                candidates = client.fetch_group_files_by_search(
                    str(group_id),
                    keywords=keywords,
                    since_date=since_date,
                    max_pages=max_pages,
                )
            except Exception:
                candidates = client.fetch_group_files_since(
                    str(group_id),
                    since_date=since_date,
                    max_pages=max_pages,
                )
            for candidate in candidates:
                if not self._should_download(candidate):
                    self._record_skip(candidate, "skipped_by_name_filter")
                    result.skipped += 1
                    continue
                if self.manifest_store.has_file(candidate.file_id):
                    result.skipped += 1
                    continue
                try:
                    downloaded_path = self._download_candidate(client, candidate)
                    self._parse_and_store(downloaded_path, candidate)
                    result.downloaded += 1
                    result.parsed += 1
                except Exception as exc:
                    self._record_skip(candidate, f"download_failed:{type(exc).__name__}")
                    self._log_failure("backfill history candidate", exc, candidate)
                    result.skipped += 1
        self.manifest_store.save()
        return result

    def retry_failed_downloads(
        self,
        *,
        min_delay_seconds: float = 120.0,
        max_delay_seconds: float = 360.0,
    ) -> PipelineResult:
        session = self.session_store.load()
        client = ZsxqClient(self.config.raw["zsxq"], session)
        result = PipelineResult()
        failed_rows = [
            row
            for row in self.manifest_store.downloads
            if str(row.get("status", "")).startswith("download_failed")
        ]
        failed_rows.sort(key=lambda row: row.get("published_at", ""))

        for index, row in enumerate(failed_rows):
            if index > 0 and max_delay_seconds > 0:
                delay = random.uniform(min_delay_seconds, max_delay_seconds)
                time.sleep(max(delay, 0))

            candidate = FileCandidate(
                channel_id=str(row.get("channel_id", "")),
                post_id=str(row.get("post_id", "")),
                file_id=str(row.get("file_id", "")),
                filename=str(row.get("filename", "")),
                published_at=str(row.get("published_at", "")),
            )
            try:
                downloaded_path = self._download_candidate(client, candidate)
                self._parse_and_store(downloaded_path, candidate)
                result.downloaded += 1
                result.parsed += 1
            except Exception as exc:
                self._record_skip(candidate, f"download_failed:{type(exc).__name__}")
                self._log_failure("retry failed-downloads candidate", exc, candidate)
                result.skipped += 1

        self.manifest_store.save()
        return result

    def validate_daily_outputs(self, as_of_date: str) -> ValidationResult:
        raw_rows = [
            row
            for row in self.manifest_store.downloads
            if row.get("status") == "downloaded"
            and row.get("downloaded_at") == as_of_date
            and row.get("raw_path")
            and Path(str(row.get("raw_path"))).exists()
        ]
        if not raw_rows:
            raise ValueError(f"no downloaded raw files found for {as_of_date}")

        checked_paths: set[Path] = set()
        for path_text in sorted(self.manifest_store.asset_registry.values()):
            series_path = Path(path_text)
            if series_path in checked_paths or not series_path.exists():
                continue
            checked_paths.add(series_path)
            last_row = self._read_last_series_row(series_path)
            if not last_row:
                continue
            last_date = str(last_row.get("date", ""))
            if last_date == as_of_date:
                return ValidationResult(
                    as_of_date=as_of_date,
                    raw_files=len(raw_rows),
                    series_path=series_path,
                    asset_code=str(last_row.get("asset_code", "")),
                    last_date=last_date,
                )

        raise ValueError(f"no parsed asset series has last date {as_of_date}")

    def _should_download(self, candidate: FileCandidate) -> bool:
        allowed_extensions = {ext.lower() for ext in self.config.raw.get("file_extensions", [])}
        if Path(candidate.filename).suffix.lower() not in allowed_extensions:
            return False
        return match_filename(candidate.filename, self.config.raw["filename_filter"])

    def _record_skip(self, candidate: FileCandidate, status: str) -> None:
        dataset_type = self._safe_dataset_type(candidate.filename)
        self.manifest_store.upsert_download(
            {
                "channel_id": candidate.channel_id,
                "post_id": candidate.post_id,
                "file_id": candidate.file_id,
                "filename": candidate.filename,
                "dataset_type": dataset_type,
                "published_at": candidate.published_at,
                "downloaded_at": "",
                "raw_path": "",
                "status": status,
                "checksum": "",
            }
        )

    def _download_candidate(self, client: ZsxqClient, candidate: FileCandidate) -> Path:
        dataset_type = classify_dataset(candidate.filename, self.config.raw["dataset_rules"])
        as_of_date = self._resolve_as_of_date(candidate.filename, candidate.published_at)
        raw_dir = self.series_store.raw_dir(as_of_date)
        destination = raw_dir / candidate.filename
        client.download_file(candidate, destination)
        self.manifest_store.upsert_download(
            {
                "channel_id": candidate.channel_id,
                "post_id": candidate.post_id,
                "file_id": candidate.file_id,
                "filename": candidate.filename,
                "dataset_type": dataset_type,
                "published_at": candidate.published_at,
                "downloaded_at": as_of_date,
                "raw_path": str(destination),
                "status": "downloaded",
                "checksum": sha256_file(destination),
            }
        )
        return destination

    def _ingest_local_file(self, path: Path, metadata: FileCandidate) -> None:
        if not self._should_download(metadata):
            self._record_skip(metadata, "skipped_by_name_filter")
            self.manifest_store.save()
            return
        as_of_date = self._resolve_as_of_date(metadata.filename, metadata.published_at)
        destination = self.series_store.raw_dir(as_of_date) / metadata.filename
        copy_file(path, destination)
        self.manifest_store.upsert_download(
            {
                "channel_id": metadata.channel_id,
                "post_id": metadata.post_id,
                "file_id": metadata.file_id,
                "filename": metadata.filename,
                "dataset_type": classify_dataset(metadata.filename, self.config.raw["dataset_rules"]),
                "published_at": metadata.published_at,
                "downloaded_at": as_of_date,
                "raw_path": str(destination),
                "status": "downloaded",
                "checksum": sha256_file(destination),
            }
        )
        self._parse_and_store(destination, metadata)
        self.manifest_store.save()

    def _parse_and_store(self, path: Path, metadata: FileCandidate) -> None:
        dataset_type = classify_dataset(metadata.filename, self.config.raw["dataset_rules"])
        as_of_date = self._resolve_as_of_date(metadata.filename, metadata.published_at)
        records = parse_metrics_from_workbook(
            path,
            dataset_type=dataset_type,
            as_of_date=as_of_date,
        )
        self.series_store.append_series(records)

    @staticmethod
    def _resolve_as_of_date(filename: str, published_at: str) -> str:
        return (
            parse_date_from_filename(filename)
            or normalize_date(published_at)
            or "unknown-date"
        )

    def _safe_dataset_type(self, filename: str) -> str:
        try:
            return classify_dataset(filename, self.config.raw["dataset_rules"])
        except Exception:
            return "unknown"

    def _history_search_keywords(self) -> list[str]:
        keywords: list[str] = []
        for pattern in self.config.raw["filename_filter"].get("include_patterns", []):
            text = pattern.strip()
            if not text:
                continue
            keywords.append(text)
            if "数据集" in text:
                keywords.append(text.replace("数据集", "数据"))
            if text.endswith("集"):
                keywords.append(text[:-1])
        return list(dict.fromkeys(keyword for keyword in keywords if keyword))

    def _read_last_series_row(self, path: Path) -> dict[str, str] | None:
        if path.suffix == ".parquet":
            import pandas as pd

            frame = pd.read_parquet(path)
            if frame.empty:
                return None
            row = frame.iloc[-1].to_dict()
            return {str(key): str(value) for key, value in row.items()}

        last_row: dict[str, str] | None = None
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                last_row = row
        return last_row

    def _log_failure(
        self,
        scope: str,
        exc: Exception,
        candidate: FileCandidate | None = None,
    ) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        detail = ""
        if candidate is not None:
            detail = f" file_id={candidate.file_id} filename={candidate.filename}"
        message = f"{timestamp} FAIL {scope}:{detail} {type(exc).__name__}: {exc}"
        print(message, file=sys.stderr, flush=True)
        ensure_dir(self.config.logs_root)
        with (self.config.logs_root / "zsxq.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{message}\n")


def bootstrap_directories(config: Config) -> None:
    ensure_dir(config.storage_root)
    ensure_dir(config.state_root)
    ensure_dir(config.logs_root)
