from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.zsxq_pipeline.config import load_config
from src.zsxq_pipeline.pipeline import IngestionPipeline, bootstrap_directories


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.temp_dir.name)
        config_src = (ROOT / "config.yaml").read_text(encoding="utf-8")
        self.config_path = self.workdir / "config.yaml"
        self.config_path.write_text(config_src, encoding="utf-8")
        self.config = load_config(self.config_path)
        bootstrap_directories(self.config)
        self.pipeline = IngestionPipeline(self.config)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_reparse_examples_creates_core_and_instruments_outputs(self) -> None:
        result = self.pipeline.reparse_path(ROOT / "examples")
        self.assertEqual(result.parsed, 2)

        parsed_dir = self.workdir / "data" / "parsed"
        core_dir = self.workdir / "data" / "series" / "core"
        instruments_dir = self.workdir / "data" / "series" / "instruments"
        self.assertFalse(parsed_dir.exists())
        self.assertTrue(core_dir.exists())
        self.assertTrue(instruments_dir.exists())
        self.assertTrue(any(core_dir.iterdir()))
        self.assertTrue(any(instruments_dir.iterdir()))

    def test_series_output_uses_trimmed_schema_and_english_metric_names(self) -> None:
        core_file = ROOT / "examples" / "26-05-27 数据总表（趋势识别＋相对比价＋资金监控）（核心数据集）.xlsx"
        self.pipeline.reparse_path(core_file)

        series_file = self.workdir / "data" / "series" / "core" / "10Y1.csv"
        self.assertTrue(series_file.exists())
        with series_file.open("r", encoding="utf-8", newline="") as handle:
            header = handle.readline().strip().split(",")
            first_row = handle.readline().strip().split(",")
        self.assertEqual(
            header,
            ["date", "dataset_type", "asset_code", "asset_name", "metric_name", "metric_value"],
        )
        self.assertEqual(first_row[4], "daily_trend")

    def test_collision_assets_get_separate_series_files(self) -> None:
        core_file = ROOT / "examples" / "26-05-27 数据总表（趋势识别＋相对比价＋资金监控）（核心数据集）.xlsx"
        self.pipeline.reparse_path(core_file)

        core_dir = self.workdir / "data" / "series" / "core"
        self.assertTrue((core_dir / "ZN1__10_year_t_note_futures.csv").exists())
        self.assertTrue((core_dir / "ZN1__zinc_futures.csv").exists())

    def test_backfill_history_uses_since_filter_and_downloads_only_matching_files(self) -> None:
        candidates = [
            {
                "channel_id": "51112284418814",
                "post_id": "post-new",
                "file_id": "file-new",
                "filename": "26-05-27 数据总表（趋势识别＋相对比价＋资金监控）（核心数据集）.xlsx",
                "published_at": "2026-05-27T20:00:00.000+0800",
                "download_url": "https://example.com/file-new",
            },
            {
                "channel_id": "51112284418814",
                "post_id": "post-skip",
                "file_id": "file-skip",
                "filename": "不匹配的文件.xlsx",
                "published_at": "2026-05-27T19:00:00.000+0800",
                "download_url": "https://example.com/file-skip",
            },
        ]

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                pass

            def fetch_group_files_by_search(self, group_id, *, keywords, since_date, max_pages):
                self.group_id = group_id
                self.keywords = keywords
                self.since_date = since_date
                self.max_pages = max_pages
                from src.zsxq_pipeline.client import FileCandidate

                return [FileCandidate(**row) for row in candidates]

            def download_file(self, file_candidate, destination):
                source = ROOT / "examples" / file_candidate.filename
                destination.write_bytes(source.read_bytes())

        with patch("src.zsxq_pipeline.pipeline.ZsxqClient", FakeClient):
            result = self.pipeline.backfill_history(since_date="2026-05-08", max_pages=5)

        self.assertEqual(result.downloaded, 1)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.parsed, 1)
        series_file = self.workdir / "data" / "series" / "core" / "10Y1.csv"
        self.assertTrue(series_file.exists())

    def test_retry_failed_downloads_retries_manifest_failures(self) -> None:
        core_file = ROOT / "examples" / "26-05-27 数据总表（趋势识别＋相对比价＋资金监控）（核心数据集）.xlsx"
        failed_row = {
            "channel_id": "51112284418814",
            "post_id": "retry-post",
            "file_id": "retry-file-id",
            "filename": core_file.name,
            "dataset_type": "core",
            "published_at": "2026-05-27T20:00:00.000+0800",
            "downloaded_at": "",
            "raw_path": "",
            "status": "download_failed:ValueError",
            "checksum": "",
        }
        self.pipeline.manifest_store.downloads = [failed_row]
        self.pipeline.manifest_store.save()

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                pass

            def download_file(self, _file_candidate, destination):
                destination.write_bytes(core_file.read_bytes())

        with patch("src.zsxq_pipeline.pipeline.ZsxqClient", FakeClient):
            result = self.pipeline.retry_failed_downloads(min_delay_seconds=0, max_delay_seconds=0)

        self.assertEqual(result.downloaded, 1)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.parsed, 1)
        refreshed = self.pipeline.manifest_store.downloads[0]
        self.assertEqual(refreshed["status"], "downloaded")


if __name__ == "__main__":
    unittest.main()
