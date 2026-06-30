from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app import data_service
from backend.app import main as main_module


FIXTURE_CONFIG = Path(__file__).parent / "fixtures" / "dashboard" / "config.json"
client = TestClient(main_module.create_app(FIXTURE_CONFIG))


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"]


def test_readiness_reports_fixture_data() -> None:
    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "reason": None,
        "date_count": 2,
        "asset_count": 2,
        "latest_date": "2026-06-28",
    }


def test_readiness_distinguishes_empty_data_from_liveness(tmp_path) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"storage_root": ".", "dashboard": {"market_map": {}}}),
        encoding="utf-8",
    )
    empty_client = TestClient(main_module.create_app(config_path))

    assert empty_client.get("/api/health").status_code == 200
    readiness = empty_client.get("/api/ready")
    assert readiness.status_code == 503
    assert readiness.json()["reason"] == "no_processed_data"


def test_create_app_reads_config_path_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(data_service.CONFIG_PATH_ENV, str(FIXTURE_CONFIG))

    environment_client = TestClient(main_module.create_app())

    assert environment_client.get("/api/ready").status_code == 200


def test_config_endpoint_has_terminal_defaults() -> None:
    response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["funding_states"] == ["Leveraging", "Deleveraging"]
    assert payload["rs_states"] == ["Lag", "Weakening", "Improving", "Lead"]
    assert payload["playback"]["default_speed"] == 1


def test_dates_assets_snapshot_and_playback_contracts() -> None:
    dates_response = client.get("/api/dates")

    assert dates_response.status_code == 200
    dates = dates_response.json()["dates"]
    assert dates == sorted(dates)
    assert dates

    assets_response = client.get("/api/assets")
    assert assets_response.status_code == 200
    assert assets_response.json()["assets"]

    snapshot_response = client.get("/api/snapshot", params={"date": dates[-1]})
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()
    assert snapshot["date"] == dates[-1]
    assert snapshot["items"]
    assert {"symbol", "funding_score", "funding_state", "rs_score", "rs_state", "trend_score"} <= set(
        snapshot["items"][0]
    )

    playback_response = client.get("/api/playback", params={"start": dates[-2], "end": dates[-1]})
    assert playback_response.status_code == 200
    playback = playback_response.json()
    assert playback["dates"] == dates[-2:]
    assert set(playback["frames"]) == set(dates[-2:])


def test_snapshot_rejects_unknown_date() -> None:
    response = client.get("/api/snapshot", params={"date": "1900-01-01"})

    assert response.status_code == 404


def test_playback_frames_are_cached_by_data_signature(monkeypatch) -> None:
    calls = 0
    rows = [
        {
            "date": "2026-06-28",
            "asset_id": "AAA",
            "asset_name": "Asset A",
            "asset_class": "core",
            "trend_score": 75,
            "rs_score": 82,
            "rs_state": "Lead",
            "flow_score": 55,
            "flow_state": "Leveraging",
            "leverage_value": 55,
            "leverage_velocity": 4,
            "leverage_velocity_score": 67,
            "trend_state": "主升浪",
            "monthly_trend": "up",
            "weekly_trend": "up",
            "daily_trend": "up",
            "long_candidate": True,
            "short_candidate": False,
        }
    ]

    def fake_load_rows(config_path: str, signature: tuple) -> tuple[dict, ...]:
        nonlocal calls
        calls += 1
        return tuple(rows)

    monkeypatch.setattr(data_service, "_load_rows_cached", fake_load_rows)
    data_service._load_frames_cached.cache_clear()

    first = data_service._load_frames_cached("config.json", ("signature-a",))
    second = data_service._load_frames_cached("config.json", ("signature-a",))
    refreshed = data_service._load_frames_cached("config.json", ("signature-b",))

    assert first is second
    assert refreshed is not first
    assert calls == 2


def test_data_signature_changes_when_processed_file_changes(tmp_path) -> None:
    source_dir = tmp_path / "processed" / "series" / "core"
    source_dir.mkdir(parents=True)
    source_path = source_dir / "AAA.csv"
    source_path.write_text("first", encoding="utf-8")
    market_map_config = {"dataset_types": ["core"]}

    first = data_service._data_signature(tmp_path, market_map_config)
    source_path.write_text("second-version", encoding="utf-8")
    second = data_service._data_signature(tmp_path, market_map_config)

    assert second != first


def test_large_playback_response_is_gzipped(monkeypatch) -> None:
    items = [
        {
            "symbol": f"ASSET-{index}",
            "asset_name": f"Asset {index}",
            "asset_class": "core",
            "trend_score": 75,
            "rs_score": 82,
            "rs_state": "Lead",
            "funding_score": 55,
            "funding_state": "Leveraging",
            "leverage_value": 55,
            "leverage_velocity": 4,
            "leverage_velocity_score": 67,
            "trend_state": "主升浪",
            "monthly_trend": "up",
            "weekly_trend": "up",
            "daily_trend": "up",
            "long_candidate": True,
            "short_candidate": False,
        }
        for index in range(100)
    ]
    monkeypatch.setattr(
        main_module.data_service,
        "get_playback",
        lambda start, end, config_path: (
            ["2026-06-28"],
            {"2026-06-28": items},
        ),
    )

    response = client.get("/api/playback")

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
