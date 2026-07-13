from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.portfolio_service import (
    PortfolioBusyError,
    PortfolioService,
    PortfolioServiceError,
    PortfolioSettings,
    PortfolioTimeoutError,
    PortfolioUnavailableError,
    SHANGHAI,
    _exclusive_lock,
    _finite_or_none,
    _merge_read_only_positions,
)
from backend.app.schemas import AssetMetadata


FIXTURE_CONFIG = Path(__file__).parent / "fixtures" / "dashboard" / "config.json"
NOW = datetime(2026, 7, 12, 20, 0, tzinfo=SHANGHAI)


def account() -> dict[str, object]:
    return {
        "account_id": "U1234567",
        "base_currency": "USD",
        "net_liquidation": 100_000,
        "maint_margin_req": 18_000,
        "sma": 12_000,
        "excess_liquidity": 82_000,
        "available_funds": 76_000,
        "buying_power": 150_000,
        "gross_position_value": 125_000,
        "cushion": 0.82,
    }


def positions() -> list[dict[str, object]]:
    return [
        {
            "conid": "1001",
            "symbol": "AAA",
            "local_symbol": "AAA",
            "sec_type": "STK",
            "currency": "USD",
            "quantity": 100,
            "market_price": 100,
            "market_value": 10_000,
            "average_cost": 90,
            "unrealized_pnl": 1_000,
            "realized_pnl": 200,
            "multiplier": 1,
        },
        {
            "conid": "1002",
            "symbol": "AAA",
            "local_symbol": "AAA C120",
            "sec_type": "OPT",
            "currency": "USD",
            "quantity": 2,
            "market_price": 4.5,
            "market_value": 900,
            "average_cost": 350,
            "unrealized_pnl": 200,
            "realized_pnl": 0,
            "multiplier": 100,
        },
    ]


def service(tmp_path: Path, *, fetcher=None) -> PortfolioService:
    settings = PortfolioSettings(
        storage_root=tmp_path / "data",
        state_root=tmp_path / "state",
        account_id="U1234567",
    )
    return PortfolioService(
        settings,
        assets_provider=lambda: [AssetMetadata(symbol="AAA", name="Asset A", asset_class="core")],
        fetcher=fetcher or (lambda _settings: (account(), positions())),
        now=lambda: NOW,
    )


def test_sync_creates_and_atomically_overwrites_daily_snapshot(tmp_path: Path) -> None:
    portfolio = service(tmp_path)

    first = portfolio.sync("scheduled_2000")
    second = portfolio.sync("scheduled_2330")

    assert first.source_file == "portfolio_20260712.csv"
    assert second.sync_source == "scheduled_2330"
    assert len(list((tmp_path / "data" / "portfolio").glob("*.csv"))) == 1
    assert not list((tmp_path / "data" / "portfolio").glob("*.tmp"))
    assert second.account and second.account.account_id_masked == "****4567"
    assert second.risk and second.risk.leverage_ratio == pytest.approx(1.25)
    assert second.positions[0].linked_asset is not None
    assert second.positions[1].risk_eligible is False


def test_stop_loss_is_persisted_and_recalculates_covered_risk(tmp_path: Path) -> None:
    portfolio = service(tmp_path)
    portfolio.sync("manual")

    updated = portfolio.update_stop_loss("1001", 85)

    position = updated.positions[0]
    assert position.stop_status == "active"
    assert position.planned_loss_at_stop == pytest.approx(500)
    assert position.remaining_risk_to_stop == pytest.approx(1_500)
    assert updated.risk and updated.risk.covered_position_count == 1
    assert updated.risk.eligible_position_count == 1
    assert "U1234567" not in portfolio.settings.stop_loss_path.read_text(encoding="utf-8")


def test_failed_sync_keeps_previous_snapshot(tmp_path: Path) -> None:
    portfolio = service(tmp_path)
    current = portfolio.sync("manual")
    path = portfolio.settings.portfolio_dir / str(current.source_file)
    original = path.read_bytes()
    portfolio.fetcher = lambda _settings: ({**account(), "account_id": "U7654321"}, positions())

    with pytest.raises(PortfolioServiceError):
        portfolio.sync("manual")

    assert path.read_bytes() == original


def test_empty_portfolio_still_writes_account_snapshot(tmp_path: Path) -> None:
    portfolio = service(tmp_path, fetcher=lambda _settings: (account(), []))

    response = portfolio.sync("manual")

    assert response.account is not None
    assert response.positions == []


def test_read_only_position_merge_uses_pnl_value_without_order_requests() -> None:
    class Contract:
        conId = 1001
        symbol = "AAA"
        localSymbol = "AAA"
        secType = "STK"
        multiplier = "1"
        currency = "USD"

    merged = _merge_read_only_positions(
        [{"account": "U1234567", "contract": Contract(), "position": 100, "averageCost": 90}],
        {10000: {"market_value": 10_000, "unrealized_pnl": 1_000, "realized_pnl": 200}},
        {20000: {"option_delta": 0.5, "option_gamma": 0.02, "option_theta": -0.1, "option_vega": 0.3}},
    )

    assert merged[0]["market_price"] == pytest.approx(100)
    assert merged[0]["market_value"] == pytest.approx(10_000)
    assert merged[0]["average_cost"] == pytest.approx(90)
    assert merged[0]["option_delta"] == pytest.approx(0.5)


def test_read_only_position_merge_keeps_position_when_pnl_is_unavailable() -> None:
    class Contract:
        conId = 1002
        symbol = "BBB"
        localSymbol = "BBB"
        secType = "STK"
        multiplier = ""
        currency = "USD"

    merged = _merge_read_only_positions(
        [{"account": "U1234567", "contract": Contract(), "position": 25, "averageCost": 40}],
        {},
    )

    assert merged[0]["conid"] == "1002"
    assert merged[0]["quantity"] == 25
    assert merged[0]["market_value"] is None


def test_ibkr_unset_double_is_treated_as_missing() -> None:
    assert _finite_or_none(1.7976931348623157e308) is None


def test_cross_process_lock_reports_busy(tmp_path: Path) -> None:
    path = tmp_path / "state" / "portfolio.lock"
    with _exclusive_lock(path, 0):
        with pytest.raises(PortfolioBusyError):
            with _exclusive_lock(path, 0):
                pass


def test_portfolio_api_reads_fixture_syncs_and_updates_stop_loss(tmp_path: Path) -> None:
    portfolio = service(tmp_path)
    portfolio.sync("scheduled_2000")
    client = TestClient(create_app(FIXTURE_CONFIG, portfolio_service=portfolio))

    response = client.get("/api/portfolio")
    assert response.status_code == 200
    assert response.json()["positions"][0]["symbol"] == "AAA"

    sync_response = client.post("/api/portfolio/sync")
    assert sync_response.status_code == 200
    assert sync_response.json()["sync_source"] == "manual"

    stop_response = client.put(
        "/api/portfolio/positions/1001/stop-loss",
        json={"stop_loss_price": 85},
    )
    assert stop_response.status_code == 200
    assert stop_response.json()["positions"][0]["planned_loss_at_stop"] == 500

    missing = client.put(
        "/api/portfolio/positions/9999/stop-loss",
        json={"stop_loss_price": 85},
    )
    assert missing.status_code == 404


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (PortfolioBusyError("busy"), 409),
        (PortfolioUnavailableError("offline"), 503),
        (PortfolioServiceError("failed"), 502),
        (PortfolioTimeoutError("timeout"), 504),
    ],
)
def test_manual_sync_maps_service_errors_to_http_status(tmp_path: Path, error: Exception, status_code: int) -> None:
    portfolio = service(tmp_path)
    portfolio.sync = lambda *_args, **_kwargs: (_ for _ in ()).throw(error)  # type: ignore[method-assign]
    client = TestClient(create_app(FIXTURE_CONFIG, portfolio_service=portfolio))

    response = client.post("/api/portfolio/sync")

    assert response.status_code == status_code


def test_launchd_installer_schedules_both_daily_runs() -> None:
    script = (Path(__file__).parents[1] / "scripts" / "install_ibkr_portfolio_launchd.sh").read_text(
        encoding="utf-8"
    )

    assert "com.chizhi.ibkr.portfolio-snapshot" in script
    assert "<integer>20</integer>" in script
    assert "<integer>23</integer>" in script
    assert "<integer>30</integer>" in script
    assert "IBKR_PYTHON_BIN" in script
    assert "CROSS_ASSET_CONFIG_PATH" in script
