from __future__ import annotations

import csv
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import fcntl
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterator
from zoneinfo import ZoneInfo

from .schemas import (
    AssetMetadata,
    PortfolioAccount,
    PortfolioAssetLink,
    PortfolioPosition,
    PortfolioResponse,
    PortfolioRiskSummary,
)


SHANGHAI = ZoneInfo("Asia/Shanghai")
EXCLUDED_RISK_TYPES = {"OPT", "FOP", "BAG"}
ACCOUNT_TAGS = (
    "NetLiquidation,MaintMarginReq,SMA,ExcessLiquidity,AvailableFunds,"
    "BuyingPower,GrossPositionValue,Cushion"
)
CSV_COLUMNS = [
    "snapshot_date",
    "captured_at",
    "sync_source",
    "account_id_masked",
    "base_currency",
    "net_liquidation",
    "maint_margin_req",
    "sma",
    "excess_liquidity",
    "available_funds",
    "buying_power",
    "gross_position_value",
    "cushion",
    "conid",
    "symbol",
    "local_symbol",
    "sec_type",
    "last_trade_date_or_contract_month",
    "strike",
    "right",
    "multiplier",
    "exchange",
    "primary_exchange",
    "currency",
    "quantity",
    "market_price",
    "market_value",
    "average_cost",
    "unrealized_pnl",
    "realized_pnl",
    "option_delta",
    "option_gamma",
    "option_theta",
    "option_vega",
]


class PortfolioServiceError(RuntimeError):
    status_code = 502


class PortfolioBusyError(PortfolioServiceError):
    status_code = 409


class PortfolioUnavailableError(PortfolioServiceError):
    status_code = 503


class PortfolioTimeoutError(PortfolioServiceError):
    status_code = 504


@dataclass(frozen=True)
class PortfolioSettings:
    storage_root: Path
    state_root: Path
    account_id: str
    host: str = "127.0.0.1"
    port: int = 7496
    client_id: int = 17
    timeout_seconds: int = 30
    stale_after_hours: int = 30
    fixture_sync: bool = False

    @property
    def portfolio_dir(self) -> Path:
        override = os.environ.get("IBKR_PORTFOLIO_DATA_DIR")
        return Path(override).expanduser().resolve() if override else self.storage_root / "portfolio"

    @property
    def stop_loss_path(self) -> Path:
        return self.state_root / "ibkr_stop_losses.json"

    @property
    def alias_path(self) -> Path:
        return self.state_root / "ibkr_asset_aliases.json"

    @property
    def lock_path(self) -> Path:
        return self.state_root / "ibkr_portfolio_sync.lock"


def load_portfolio_settings(
    storage_root: Path,
    state_root: Path,
    config: dict[str, Any] | None = None,
) -> PortfolioSettings:
    local_values = _read_env_file(state_root / "ibkr.env")

    def value(name: str, default: str = "") -> str:
        return os.environ.get(name, local_values.get(name, default))

    config = config or {}
    return PortfolioSettings(
        storage_root=storage_root,
        state_root=state_root,
        account_id=value("IBKR_ACCOUNT_ID"),
        host=value("IBKR_TWS_HOST", str(config.get("host", "127.0.0.1"))),
        port=int(value("IBKR_TWS_PORT", str(config.get("port", 7496)))),
        client_id=int(value("IBKR_CLIENT_ID", str(config.get("client_id", 17)))),
        timeout_seconds=int(value("IBKR_TIMEOUT_SECONDS", str(config.get("timeout_seconds", 30)))),
        stale_after_hours=int(value("IBKR_STALE_HOURS", str(config.get("stale_after_hours", 30)))),
        fixture_sync=bool(config.get("fixture_sync", False)),
    )


class PortfolioService:
    def __init__(
        self,
        settings: PortfolioSettings,
        assets_provider: Callable[[], list[AssetMetadata]],
        fetcher: Callable[[PortfolioSettings], tuple[dict[str, Any], list[dict[str, Any]]]] | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings = settings
        self.assets_provider = assets_provider
        self.fetcher = fetcher or fetch_from_tws
        self.now = now or (lambda: datetime.now(SHANGHAI))

    def get_portfolio(self) -> PortfolioResponse:
        paths = sorted(self.settings.portfolio_dir.glob("portfolio_*.csv"), reverse=True)
        if not paths:
            return PortfolioResponse(status="no_snapshot", message="尚无持仓快照")
        for path in paths:
            try:
                return self._response_from_path(path)
            except (OSError, ValueError, csv.Error) as exc:
                _ = exc
        return PortfolioResponse(status="error", message="没有可读取的持仓快照")

    def sync(self, source: str = "manual", lock_timeout: float = 0) -> PortfolioResponse:
        if source not in {"manual", "scheduled_2000", "scheduled_2330"}:
            raise ValueError(f"unsupported sync source: {source}")
        with _exclusive_lock(self.settings.lock_path, lock_timeout):
            if self.settings.fixture_sync:
                current = self.get_portfolio()
                if current.status in {"ready", "stale"}:
                    return current.model_copy(update={"status": "ready", "sync_source": source})
                raise PortfolioUnavailableError("fixture snapshot is unavailable")
            if not self.settings.account_id:
                raise PortfolioUnavailableError("IBKR_ACCOUNT_ID 未配置")
            account, positions = self.fetcher(self.settings)
            captured_at = self.now().astimezone(SHANGHAI)
            path = self._write_snapshot(account, positions, source, captured_at)
            return self._response_from_path(path)

    def update_stop_loss(self, conid: str, stop_loss_price: float | None) -> PortfolioResponse:
        current = self.get_portfolio()
        if current.status not in {"ready", "stale"} or current.account is None:
            raise KeyError(conid)
        position = next((item for item in current.positions if item.conid == conid), None)
        if position is None:
            raise KeyError(conid)
        if not position.risk_eligible:
            raise ValueError("该合约类型不参与止损风险计算")
        if stop_loss_price is not None and (not math.isfinite(stop_loss_price) or stop_loss_price <= 0):
            raise ValueError("止损价必须是正数")
        values = _read_json_dict(self.settings.stop_loss_path)
        key = self._stop_key(conid, current.account.account_id_masked)
        if stop_loss_price is None:
            values.pop(key, None)
        else:
            values[key] = stop_loss_price
        _write_json_atomic(self.settings.stop_loss_path, values)
        return self.get_portfolio()

    def _response_from_path(self, path: Path) -> PortfolioResponse:
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError("empty snapshot")
        first = rows[0]
        captured_at_text = first.get("captured_at", "")
        captured_at = datetime.fromisoformat(captured_at_text)
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=SHANGHAI)
        account = PortfolioAccount(
            account_id_masked=first.get("account_id_masked", ""),
            base_currency=first.get("base_currency", ""),
            net_liquidation=_optional_float(first.get("net_liquidation")),
            maint_margin_req=_optional_float(first.get("maint_margin_req")),
            sma=_optional_float(first.get("sma")),
            excess_liquidity=_optional_float(first.get("excess_liquidity")),
            available_funds=_optional_float(first.get("available_funds")),
            buying_power=_optional_float(first.get("buying_power")),
            gross_position_value=_optional_float(first.get("gross_position_value")),
            cushion=_optional_float(first.get("cushion")),
        )
        stops = _read_json_dict(self.settings.stop_loss_path)
        aliases = _read_json_dict(self.settings.alias_path)
        assets = self.assets_provider()
        positions = [
            self._position_from_row(row, account, stops, aliases, assets)
            for row in rows
            if str(row.get("conid", "")).strip()
        ]
        risk = _risk_summary(account, positions)
        status = "stale" if self.now().astimezone(SHANGHAI) - captured_at > timedelta(hours=self.settings.stale_after_hours) else "ready"
        return PortfolioResponse(
            status=status,
            message=f"快照已超过 {self.settings.stale_after_hours} 小时" if status == "stale" else None,
            snapshot_date=first.get("snapshot_date") or path.stem.removeprefix("portfolio_"),
            captured_at=captured_at.isoformat(),
            sync_source=first.get("sync_source") or None,
            source_file=path.name,
            account=account,
            risk=risk,
            positions=positions,
        )

    def _position_from_row(
        self,
        row: dict[str, str],
        account: PortfolioAccount,
        stops: dict[str, Any],
        aliases: dict[str, Any],
        assets: list[AssetMetadata],
    ) -> PortfolioPosition:
        conid = str(row["conid"])
        quantity = float(row["quantity"])
        sec_type = str(row.get("sec_type", "")).upper()
        market_price = _optional_float(row.get("market_price"))
        market_value = _optional_float(row.get("market_value"))
        average_cost = _optional_float(row.get("average_cost"))
        unrealized_pnl = _optional_float(row.get("unrealized_pnl"))
        multiplier = _optional_float(row.get("multiplier"))
        stop = _optional_float(stops.get(self._stop_key(conid, account.account_id_masked)))
        risk_eligible = sec_type not in EXCLUDED_RISK_TYPES
        planned_loss, remaining_risk, stop_status = _position_risk(
            quantity=quantity,
            market_price=market_price,
            market_value=market_value,
            average_cost=average_cost,
            unrealized_pnl=unrealized_pnl,
            multiplier=multiplier,
            stop_loss=stop,
            risk_eligible=risk_eligible,
        )
        linked_asset, link_status = _link_asset(conid, row.get("symbol", ""), aliases, assets)
        nlv = account.net_liquidation
        weight = abs(market_value) / nlv if market_value is not None and nlv not in {None, 0} else None
        return PortfolioPosition(
            conid=conid,
            symbol=row.get("symbol", ""),
            local_symbol=row.get("local_symbol", ""),
            sec_type=sec_type,
            last_trade_date_or_contract_month=row.get("last_trade_date_or_contract_month", ""),
            strike=_optional_float(row.get("strike")),
            right=row.get("right", ""),
            multiplier=multiplier,
            exchange=row.get("exchange", ""),
            primary_exchange=row.get("primary_exchange", ""),
            currency=row.get("currency", ""),
            quantity=quantity,
            market_price=market_price,
            market_value=market_value,
            average_cost=average_cost,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=_optional_float(row.get("realized_pnl")),
            option_delta=_optional_float(row.get("option_delta")),
            option_gamma=_optional_float(row.get("option_gamma")),
            option_theta=_optional_float(row.get("option_theta")),
            option_vega=_optional_float(row.get("option_vega")),
            portfolio_weight=weight,
            stop_loss_price=stop,
            stop_status=stop_status,
            planned_loss_at_stop=planned_loss,
            remaining_risk_to_stop=remaining_risk,
            risk_eligible=risk_eligible,
            link_status=link_status,
            linked_asset=linked_asset,
        )

    def _write_snapshot(
        self,
        account: dict[str, Any],
        positions: list[dict[str, Any]],
        source: str,
        captured_at: datetime,
    ) -> Path:
        required = {"account_id", "base_currency", "net_liquidation"}
        missing = required - set(account)
        if missing:
            raise PortfolioServiceError(f"IBKR account summary missing: {', '.join(sorted(missing))}")
        if account["account_id"] != self.settings.account_id:
            raise PortfolioServiceError("IBKR 返回账户与配置账户不匹配")
        for index, position in enumerate(positions):
            missing_position_fields = [
                field for field in ("conid", "symbol", "sec_type", "quantity") if position.get(field) in {None, ""}
            ]
            if missing_position_fields:
                raise PortfolioServiceError(
                    f"IBKR position {index} missing: {', '.join(missing_position_fields)}"
                )
        self.settings.portfolio_dir.mkdir(parents=True, exist_ok=True)
        snapshot_date = captured_at.strftime("%Y%m%d")
        target = self.settings.portfolio_dir / f"portfolio_{snapshot_date}.csv"
        temp = target.with_suffix(".csv.tmp")
        base = {
            "snapshot_date": snapshot_date,
            "captured_at": captured_at.isoformat(),
            "sync_source": source,
            "account_id_masked": _mask_account(account["account_id"]),
            "base_currency": account["base_currency"],
            **{key: account.get(key, "") for key in CSV_COLUMNS[5:13]},
        }
        rows = [{**base, **position} for position in positions] or [base]
        try:
            with temp.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(rows)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp, 0o600)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        return target

    def _stop_key(self, conid: str, masked_account: str) -> str:
        account_scope = self.settings.account_id or masked_account
        digest = sha256(account_scope.encode("utf-8")).hexdigest()[:16]
        return f"{digest}:{conid}"


def fetch_from_tws(settings: PortfolioSettings) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
    except ImportError as exc:
        raise PortfolioUnavailableError("未安装 IBKR 官方 Python API") from exc

    class ReadOnlyPortfolioClient(EWrapper, EClient):
        def __init__(self) -> None:
            EWrapper.__init__(self)
            EClient.__init__(self, self)
            self.ready = threading.Event()
            self.summary_done = threading.Event()
            self.positions_done = threading.Event()
            self.pnl_done = threading.Event()
            self.greeks_done = threading.Event()
            self.summary: dict[str, dict[str, dict[str, str]]] = {}
            self.positions: list[dict[str, Any]] = []
            self.pnl: dict[int, dict[str, Any]] = {}
            self.pending_pnl: set[int] = set()
            self.greeks: dict[int, dict[str, Any]] = {}
            self.pending_greeks: set[int] = set()
            self.errors: list[tuple[int, int, str]] = []

        def nextValidId(self, orderId: int) -> None:  # noqa: N802 - IBKR callback name
            # TWS sends this during the connection handshake. We deliberately do
            # not call reqIds(), because that request requires API write access.
            self.ready.set()

        def accountSummary(  # noqa: N802 - IBKR callback name
            self, reqId: int, account: str, tag: str, value: str, currency: str
        ) -> None:
            self.summary.setdefault(account, {})[tag] = {"value": value, "currency": currency}

        def accountSummaryEnd(self, reqId: int) -> None:  # noqa: N802
            self.summary_done.set()

        def position(self, account: str, contract: Any, position: Any, avgCost: float) -> None:
            self.positions.append(
                {
                    "account": account,
                    "contract": contract,
                    "position": position,
                    "averageCost": avgCost,
                }
            )

        def positionEnd(self) -> None:  # noqa: N802
            self.positions_done.set()

        def pnlSingle(  # noqa: N802
            self,
            reqId: int,
            pos: Any,
            dailyPnL: float,
            unrealizedPnL: float,
            realizedPnL: float,
            value: float,
        ) -> None:
            self.pnl[reqId] = {
                "position": pos,
                "unrealized_pnl": _finite_or_none(unrealizedPnL),
                "realized_pnl": _finite_or_none(realizedPnL),
                "market_value": _finite_or_none(value),
            }
            self.pending_pnl.discard(reqId)
            if not self.pending_pnl:
                self.pnl_done.set()

        def tickOptionComputation(  # noqa: N802
            self, reqId: int, tickType: int, tickAttrib: int, impliedVol: float,
            delta: float, optPrice: float, pvDividend: float, gamma: float,
            vega: float, theta: float, undPrice: float,
        ) -> None:
            if tickType not in {13, 83}:
                return
            self.greeks[reqId] = {
                "option_delta": _finite_or_none(delta),
                "option_gamma": _finite_or_none(gamma),
                "option_theta": _finite_or_none(theta),
                "option_vega": _finite_or_none(vega),
            }
            self.pending_greeks.discard(reqId)
            if not self.pending_greeks:
                self.greeks_done.set()

        def error(self, reqId: int, *args: Any) -> None:
            if len(args) >= 3:
                _error_time, error_code, error_string = args[:3]
            elif len(args) >= 2:
                error_code, error_string = args[:2]
            else:
                return
            code = int(error_code)
            if code in {1102, 2103, 2104, 2105, 2106, 2157, 2158}:
                return
            self.errors.append((int(reqId), code, str(error_string)))
            if int(reqId) in self.pending_pnl:
                self.pending_pnl.discard(int(reqId))
                if not self.pending_pnl:
                    self.pnl_done.set()
            if int(reqId) in self.pending_greeks:
                self.pending_greeks.discard(int(reqId))
                if not self.pending_greeks:
                    self.greeks_done.set()

    app = ReadOnlyPortfolioClient()
    worker: threading.Thread | None = None
    summary_request_id = 9001
    pnl_request_ids: list[int] = []
    greek_request_ids: list[int] = []
    deadline = time.monotonic() + settings.timeout_seconds

    def wait_for(event: threading.Event, message: str) -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not event.wait(remaining):
            raise PortfolioTimeoutError(message)

    try:
        try:
            app.connect(settings.host, settings.port, settings.client_id)
            if not app.isConnected():
                raise PortfolioUnavailableError("无法连接 TWS，请确认已登录并启用只读 Socket API")
            worker = threading.Thread(target=app.run, name="ibkr-portfolio-reader", daemon=True)
            worker.start()
            wait_for(app.ready, "IBKR 连接握手超时")

            app.reqAccountSummary(summary_request_id, "All", ACCOUNT_TAGS)
            app.reqPositions()
            wait_for(app.summary_done, "IBKR 账户摘要超时")
            wait_for(app.positions_done, "IBKR 持仓请求超时")

            selected_positions = [
                item
                for item in app.positions
                if item["account"] == settings.account_id
                and _optional_float(item.get("position")) not in {None, 0}
            ]
            for offset, item in enumerate(selected_positions):
                contract = item["contract"]
                conid = int(_item_value(contract, "conId", "conid") or 0)
                if conid <= 0:
                    continue
                request_id = 10000 + offset
                pnl_request_ids.append(request_id)
                app.pending_pnl.add(request_id)
                app.reqPnLSingle(request_id, settings.account_id, "", conid)
            if app.pending_pnl:
                wait_for(app.pnl_done, "IBKR 持仓盈亏请求超时")

            for offset, item in enumerate(selected_positions):
                contract = item["contract"]
                if str(_item_value(contract, "secType", "sec_type") or "").upper() not in {"OPT", "FOP"}:
                    continue
                request_id = 20000 + offset
                greek_request_ids.append(request_id)
                app.pending_greeks.add(request_id)
                app.reqMktData(request_id, contract, "", False, False, [])
            if app.pending_greeks:
                remaining = max(0.0, deadline - time.monotonic())
                app.greeks_done.wait(min(5.0, remaining))
        except PortfolioServiceError:
            raise
        except Exception as exc:
            raise PortfolioUnavailableError("无法连接 TWS，请确认已登录并启用只读 Socket API") from exc
    finally:
        try:
            app.cancelAccountSummary(summary_request_id)
            app.cancelPositions()
            for request_id in pnl_request_ids:
                app.cancelPnLSingle(request_id)
            for request_id in greek_request_ids:
                app.cancelMktData(request_id)
            app.disconnect()
        except Exception:
            pass
        if worker is not None:
            worker.join(timeout=1)

    fatal_errors = [
        error for error in app.errors
        if error[0] not in pnl_request_ids and error[0] not in greek_request_ids and error[1] not in {300}
    ]
    if fatal_errors:
        _request_id, code, message = fatal_errors[0]
        raise PortfolioServiceError(f"IBKR 请求失败 ({code}): {message}")
    account_values = app.summary.get(settings.account_id)
    if not isinstance(account_values, dict):
        raise PortfolioServiceError("IBKR 未返回配置账户的摘要")
    account = _normalize_account(settings.account_id, account_values)
    raw_positions = [
        item
        for item in app.positions
        if item["account"] == settings.account_id
        and _optional_float(item.get("position")) not in {None, 0}
    ]
    return account, _merge_read_only_positions(raw_positions, app.pnl, app.greeks)


def _merge_read_only_positions(
    positions: list[dict[str, Any]],
    pnl_by_request_id: dict[int, dict[str, Any]],
    greeks_by_request_id: dict[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for offset, item in enumerate(positions):
        normalized = _normalize_portfolio_item(item)
        pnl = pnl_by_request_id.get(10000 + offset, {})
        normalized.update(pnl)
        normalized.update((greeks_by_request_id or {}).get(20000 + offset, {}))
        quantity = _optional_float(normalized.get("quantity"))
        market_value = _optional_float(normalized.get("market_value"))
        multiplier = _optional_float(normalized.get("multiplier")) or 1.0
        if quantity not in {None, 0} and market_value is not None and multiplier:
            normalized["market_price"] = market_value / (quantity * multiplier)
        result.append(normalized)
    return result


def _finite_or_none(value: Any) -> float | None:
    parsed = _optional_float(value)
    # IBKR uses the maximum IEEE-754 double as its unset-value sentinel.
    return parsed if parsed is not None and math.isfinite(parsed) and abs(parsed) < 1e307 else None


def _normalize_account(account_id: str, values: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "NetLiquidation": "net_liquidation",
        "MaintMarginReq": "maint_margin_req",
        "SMA": "sma",
        "ExcessLiquidity": "excess_liquidity",
        "AvailableFunds": "available_funds",
        "BuyingPower": "buying_power",
        "GrossPositionValue": "gross_position_value",
        "Cushion": "cushion",
    }
    result: dict[str, Any] = {"account_id": account_id, "base_currency": ""}
    for source, target in mapping.items():
        entry = values.get(source, {})
        raw_value = entry.get("value") if isinstance(entry, dict) else entry
        currency = entry.get("currency", "") if isinstance(entry, dict) else ""
        result[target] = _optional_float(raw_value)
        if currency and not result["base_currency"]:
            result["base_currency"] = currency
    if result["net_liquidation"] is None or not result["base_currency"]:
        raise PortfolioServiceError("IBKR 账户摘要不完整")
    return result


def _normalize_portfolio_item(item: Any) -> dict[str, Any]:
    contract = _item_value(item, "contract")
    return {
        "conid": str(_item_value(contract, "conId", "conid") or ""),
        "symbol": str(_item_value(contract, "symbol") or ""),
        "local_symbol": str(_item_value(contract, "localSymbol", "local_symbol") or ""),
        "sec_type": str(_item_value(contract, "secType", "sec_type") or ""),
        "last_trade_date_or_contract_month": str(_item_value(contract, "lastTradeDateOrContractMonth") or ""),
        "strike": _item_value(contract, "strike"),
        "right": str(_item_value(contract, "right") or ""),
        "multiplier": _item_value(contract, "multiplier"),
        "exchange": str(_item_value(contract, "exchange") or ""),
        "primary_exchange": str(_item_value(contract, "primaryExchange", "primary_exchange") or ""),
        "currency": str(_item_value(contract, "currency") or ""),
        "quantity": _item_value(item, "position"),
        "market_price": _item_value(item, "marketPrice", "market_price"),
        "market_value": _item_value(item, "marketValue", "market_value"),
        "average_cost": _item_value(item, "averageCost", "avgCost", "average_cost"),
        "unrealized_pnl": _item_value(item, "unrealizedPNL", "unrealized_pnl"),
        "realized_pnl": _item_value(item, "realizedPNL", "realized_pnl"),
        "option_delta": _item_value(item, "option_delta"),
        "option_gamma": _item_value(item, "option_gamma"),
        "option_theta": _item_value(item, "option_theta"),
        "option_vega": _item_value(item, "option_vega"),
    }


def _item_value(item: Any, *names: str) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return None


def _position_risk(
    *,
    quantity: float,
    market_price: float | None,
    market_value: float | None,
    average_cost: float | None,
    unrealized_pnl: float | None,
    multiplier: float | None,
    stop_loss: float | None,
    risk_eligible: bool,
) -> tuple[float | None, float | None, str]:
    if not risk_eligible:
        return None, None, "not_applicable"
    if stop_loss is None:
        return None, None, "missing"
    if quantity == 0 or market_price in {None, 0}:
        return None, None, "unavailable"
    factor = None
    if market_value is not None:
        factor = abs(market_value) / (abs(quantity) * abs(market_price))
    if not factor and multiplier is not None and multiplier > 0:
        factor = multiplier
    if not factor or not math.isfinite(factor):
        return None, None, "unavailable"
    entry_price = average_cost
    if unrealized_pnl is not None:
        entry_price = market_price - unrealized_pnl / (quantity * factor)
    if entry_price is None or not math.isfinite(entry_price):
        return None, None, "unavailable"
    pnl_at_stop = (stop_loss - entry_price) * quantity * factor
    planned_loss = max(-pnl_at_stop, 0)
    remaining = max((market_price - stop_loss) * quantity * factor, 0)
    breached = (quantity > 0 and market_price <= stop_loss) or (quantity < 0 and market_price >= stop_loss)
    return planned_loss, remaining, "breached" if breached else "active"


def _risk_summary(account: PortfolioAccount, positions: list[PortfolioPosition]) -> PortfolioRiskSummary:
    nlv = account.net_liquidation
    eligible = [item for item in positions if item.risk_eligible]
    covered = [item for item in eligible if item.planned_loss_at_stop is not None]
    eligible_mv = sum(abs(item.market_value or 0) for item in eligible)
    covered_mv = sum(abs(item.market_value or 0) for item in covered)
    position_values = [abs(item.market_value or 0) for item in positions]

    def ratio(value: float | None) -> float | None:
        return value / nlv if value is not None and nlv not in {None, 0} else None

    return PortfolioRiskSummary(
        leverage_ratio=ratio(account.gross_position_value),
        maintenance_margin_ratio=ratio(account.maint_margin_req),
        excess_liquidity_ratio=ratio(account.excess_liquidity),
        largest_position_concentration=ratio(max(position_values, default=0)),
        planned_loss_at_stop=sum(item.planned_loss_at_stop or 0 for item in covered),
        remaining_risk_to_stop=sum(item.remaining_risk_to_stop or 0 for item in covered),
        eligible_position_count=len(eligible),
        covered_position_count=len(covered),
        eligible_market_value=eligible_mv,
        covered_market_value=covered_mv,
        coverage_ratio=covered_mv / eligible_mv if eligible_mv else None,
    )


def _link_asset(
    conid: str,
    symbol: str,
    aliases: dict[str, Any],
    assets: list[AssetMetadata],
) -> tuple[PortfolioAssetLink | None, str]:
    alias = aliases.get(conid)
    candidates: list[AssetMetadata]
    if isinstance(alias, dict):
        target_symbol = str(alias.get("symbol", "")).strip().upper()
        target_class = str(alias.get("asset_class", "")).strip().lower()
        candidates = [
            asset
            for asset in assets
            if asset.symbol.strip().upper() == target_symbol and asset.asset_class.strip().lower() == target_class
        ]
    else:
        normalized = symbol.strip().upper()
        candidates = [asset for asset in assets if asset.symbol.strip().upper() == normalized]
    identities = {(item.asset_class, item.symbol, item.name): item for item in candidates}
    if len(identities) == 1:
        asset = next(iter(identities.values()))
        return PortfolioAssetLink(symbol=asset.symbol, name=asset.name, asset_class=asset.asset_class), "linked"
    return None, "ambiguous" if identities else "unlinked"


@contextmanager
def _exclusive_lock(path: Path, timeout: float) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise PortfolioBusyError("已有持仓同步正在运行") from exc
                time.sleep(0.1)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        values[key.strip()] = raw_value.strip().strip("\"'")
    return values


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _mask_account(account_id: str) -> str:
    return f"****{account_id[-4:]}" if len(account_id) >= 4 else "****"
