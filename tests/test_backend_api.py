from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import data_service
from backend.app import main as main_module
from backend.app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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
            "trend_state": "主升浪",
            "monthly_trend": "up",
            "weekly_trend": "up",
            "daily_trend": "up",
            "long_candidate": True,
            "short_candidate": False,
        }
    ]

    def fake_load_rows() -> tuple[dict, ...]:
        nonlocal calls
        calls += 1
        return tuple(rows)

    monkeypatch.setattr(data_service, "load_rows", fake_load_rows)
    data_service._load_frames_cached.cache_clear()

    first = data_service._load_frames_cached(("signature-a",))
    second = data_service._load_frames_cached(("signature-a",))
    refreshed = data_service._load_frames_cached(("signature-b",))

    assert first is second
    assert refreshed is not first
    assert calls == 2


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
        main_module,
        "get_playback",
        lambda start, end: (["2026-06-28"], {"2026-06-28": items}),
    )

    response = client.get("/api/playback")

    assert response.status_code == 200
    assert response.headers["content-encoding"] == "gzip"
