from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

SERIES_COLUMNS = [
    "date",
    "dataset_type",
    "asset_code",
    "asset_name",
    "metric_name",
    "metric_value",
]

TREND_FIELDS = ("monthly_trend", "weekly_trend", "daily_trend")
TREND_BAR_FIELDS = ("monthly_trend_bars", "weekly_trend_bars", "daily_trend_bars")
INPUT_FIELD_ALIASES = {
    "monthly_trend_duration": "monthly_trend_bars",
    "weekly_trend_duration": "weekly_trend_bars",
    "daily_trend_duration": "daily_trend_bars",
}
REQUIRED_FIELDS = set(TREND_FIELDS) | set(TREND_BAR_FIELDS)

TREND_VALUES = {
    "up": 1,
    "neutral": 0,
    "down": -1,
}
TREND_LABELS = {
    "up": "up",
    "neutral": "neutral",
    "down": "down",
    "1": "up",
    "0": "neutral",
    "-1": "down",
    "上行": "up",
    "上行趋势": "up",
    "无趋势": "neutral",
    "中性": "neutral",
    "震荡": "neutral",
    "下行": "down",
    "下行趋势": "down",
}

WEIGHTS = {
    "monthly": 3,
    "weekly": 2,
    "daily": 1,
}
MATURITY_BARS = {
    "monthly": 6,
    "weekly": 12,
    "daily": 20,
}

STATE_NAMES = {
    ("up", "up", "up"): "主升浪",
    ("up", "up", "neutral"): "主升整理",
    ("up", "up", "down"): "主升回调",
    ("up", "neutral", "up"): "趋势再启动",
    ("up", "neutral", "neutral"): "上行中继震荡",
    ("up", "neutral", "down"): "高位转弱预警",
    ("up", "down", "up"): "大级别回调反弹",
    ("up", "down", "neutral"): "深度调整静默",
    ("up", "down", "down"): "牛转熊风险",
    ("neutral", "up", "up"): "趋势初期 / 右侧确认",
    ("neutral", "up", "neutral"): "上行初期休整",
    ("neutral", "up", "down"): "回踩确认 / 假突破风险",
    ("neutral", "neutral", "up"): "左侧转右侧萌芽",
    ("neutral", "neutral", "neutral"): "静默",
    ("neutral", "neutral", "down"): "震荡下探",
    ("neutral", "down", "up"): "下跌后的反弹",
    ("neutral", "down", "neutral"): "下跌中继震荡",
    ("neutral", "down", "down"): "下行趋势初期",
    ("down", "up", "up"): "底部右侧早期 / 逆大势反弹",
    ("down", "up", "neutral"): "反弹休整",
    ("down", "up", "down"): "反弹失败",
    ("down", "neutral", "up"): "左侧反弹",
    ("down", "neutral", "neutral"): "低位震荡静默",
    ("down", "neutral", "down"): "下跌延续预备",
    ("down", "down", "up"): "主跌反弹",
    ("down", "down", "neutral"): "下跌中继",
    ("down", "down", "down"): "主跌浪",
}

TRANSITION_LABELS = {
    "monthly": {
        2: "月线由下行反转为上行",
        1: "月线趋势改善",
        -1: "月线趋势转弱",
        -2: "月线由上行反转为下行",
    },
    "weekly": {
        2: "周线由下行反转为上行",
        1: "周线趋势改善",
        -1: "周线趋势转弱",
        -2: "周线由上行反转为下行",
    },
    "daily": {
        2: "日线由下行反转为上行",
        1: "日线趋势改善",
        -1: "日线趋势转弱",
        -2: "日线由上行反转为下行",
    },
}

OUTPUT_FIELDS = [
    "monthly_trend",
    "weekly_trend",
    "daily_trend",
    "trend_combo",
    "state_name",
    "monthly_trend_bars",
    "weekly_trend_bars",
    "daily_trend_bars",
    "monthly_duration_multiplier",
    "weekly_duration_multiplier",
    "daily_duration_multiplier",
    "raw_current_score",
    "current_score",
    "raw_duration_score",
    "duration_score",
    "raw_transition_score",
    "transition_score",
    "decayed_transition_score",
    "raw_final_trend_score",
    "capped_final_trend_score",
    "transition_label",
]


@dataclass(frozen=True)
class AssetKey:
    dataset_type: str
    asset_code: str
    asset_name: str


def calculate_trend_score_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    """Calculate trend score derived rows from existing long-format asset rows."""
    grouped = _group_input_rows(rows)
    output_rows: list[dict[str, str]] = []
    for asset_key, rows_by_date in grouped.items():
        previous: dict[str, str] | None = None
        for date in sorted(rows_by_date):
            values = rows_by_date[date]
            missing = sorted(REQUIRED_FIELDS - set(values))
            if missing:
                asset_label = f"{asset_key.dataset_type}/{asset_key.asset_code}/{asset_key.asset_name}"
                raise ValueError(f"missing trend score fields for {asset_label} {date}: {', '.join(missing)}")

            current = {
                "monthly_trend": _normalize_trend(values["monthly_trend"]),
                "weekly_trend": _normalize_trend(values["weekly_trend"]),
                "daily_trend": _normalize_trend(values["daily_trend"]),
                "monthly_trend_bars": _parse_bars(values["monthly_trend_bars"], "monthly_trend_bars"),
                "weekly_trend_bars": _parse_bars(values["weekly_trend_bars"], "weekly_trend_bars"),
                "daily_trend_bars": _parse_bars(values["daily_trend_bars"], "daily_trend_bars"),
            }
            previous_for_transition = previous or {
                "monthly_trend": current["monthly_trend"],
                "weekly_trend": current["weekly_trend"],
                "daily_trend": current["daily_trend"],
            }
            calculated = _calculate_date_values(current, previous_for_transition)
            output_rows.extend(_to_metric_rows(asset_key, date, calculated))
            previous = current
    return output_rows


def _group_input_rows(rows: Iterable[dict[str, str]]) -> dict[AssetKey, dict[str, dict[str, str]]]:
    grouped: dict[AssetKey, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        metric_name = str(row.get("metric_name", "")).strip()
        normalized_metric = INPUT_FIELD_ALIASES.get(metric_name, metric_name)
        if normalized_metric not in REQUIRED_FIELDS:
            continue
        key = AssetKey(
            dataset_type=str(row.get("dataset_type", "")),
            asset_code=str(row.get("asset_code", "")),
            asset_name=str(row.get("asset_name", "")),
        )
        date = str(row.get("date", ""))
        grouped[key][date][normalized_metric] = str(row.get("metric_value", ""))
    return grouped


def _calculate_date_values(current: dict[str, str | float], previous: dict[str, str | float]) -> dict[str, str | float]:
    monthly = str(current["monthly_trend"])
    weekly = str(current["weekly_trend"])
    daily = str(current["daily_trend"])
    trends = {
        "monthly": monthly,
        "weekly": weekly,
        "daily": daily,
    }
    bars = {
        "monthly": float(current["monthly_trend_bars"]),
        "weekly": float(current["weekly_trend_bars"]),
        "daily": float(current["daily_trend_bars"]),
    }
    values = {level: TREND_VALUES[trend] for level, trend in trends.items()}
    previous_values = {
        "monthly": TREND_VALUES[str(previous["monthly_trend"])],
        "weekly": TREND_VALUES[str(previous["weekly_trend"])],
        "daily": TREND_VALUES[str(previous["daily_trend"])],
    }

    duration_multipliers = {
        level: _duration_multiplier(trends[level], bars[level], MATURITY_BARS[level])
        for level in ("monthly", "weekly", "daily")
    }
    raw_current_score = sum(values[level] * WEIGHTS[level] for level in ("monthly", "weekly", "daily"))
    current_score = raw_current_score / 6 * 100
    raw_duration_score = sum(
        values[level] * WEIGHTS[level] * duration_multipliers[level]
        for level in ("monthly", "weekly", "daily")
    )
    duration_score = raw_duration_score / 12 * 100

    changes = {
        level: values[level] - previous_values[level]
        for level in ("monthly", "weekly", "daily")
    }
    raw_transition_score = sum(changes[level] * WEIGHTS[level] for level in ("monthly", "weekly", "daily"))
    transition_score = raw_transition_score / 12 * 100
    decayed_transition_score = transition_score
    raw_final_trend_score = duration_score + 0.4 * decayed_transition_score
    capped_final_trend_score = max(-100, min(100, raw_final_trend_score))
    combo = (monthly, weekly, daily)

    return {
        "monthly_trend": monthly,
        "weekly_trend": weekly,
        "daily_trend": daily,
        "trend_combo": "/".join(combo),
        "state_name": STATE_NAMES[combo],
        "monthly_trend_bars": bars["monthly"],
        "weekly_trend_bars": bars["weekly"],
        "daily_trend_bars": bars["daily"],
        "monthly_duration_multiplier": duration_multipliers["monthly"],
        "weekly_duration_multiplier": duration_multipliers["weekly"],
        "daily_duration_multiplier": duration_multipliers["daily"],
        "raw_current_score": raw_current_score,
        "current_score": current_score,
        "raw_duration_score": raw_duration_score,
        "duration_score": duration_score,
        "raw_transition_score": raw_transition_score,
        "transition_score": transition_score,
        "decayed_transition_score": decayed_transition_score,
        "raw_final_trend_score": raw_final_trend_score,
        "capped_final_trend_score": capped_final_trend_score,
        "transition_label": _transition_label(changes),
    }


def _normalize_trend(value: str) -> str:
    text = str(value).strip()
    normalized = TREND_LABELS.get(text)
    if normalized is None:
        normalized = TREND_LABELS.get(text.lower())
    if normalized is None:
        raise ValueError(f"unsupported trend value: {value}")
    return normalized


def _parse_bars(value: str, field_name: str) -> float:
    try:
        bars = float(str(value).strip())
    except ValueError as exc:
        raise ValueError(f"invalid {field_name}: {value}") from exc
    if bars < 0:
        raise ValueError(f"invalid {field_name}: {value}")
    return bars


def _duration_multiplier(trend: str, bars: float, maturity_bars: int) -> float:
    if trend == "neutral":
        return 0.0
    return 1 + min(math.sqrt(bars / maturity_bars), 1)


def _transition_label(changes: dict[str, int]) -> str:
    labels = [
        TRANSITION_LABELS[level][change]
        for level in ("monthly", "weekly", "daily")
        if (change := changes[level]) != 0
    ]
    return "；".join(labels) if labels else "状态未变化"


def _to_metric_rows(asset_key: AssetKey, date: str, values: dict[str, str | float]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for field in OUTPUT_FIELDS:
        rows.append(
            {
                "date": date,
                "dataset_type": asset_key.dataset_type,
                "asset_code": asset_key.asset_code,
                "asset_name": asset_key.asset_name,
                "metric_name": field,
                "metric_value": _format_value(values[field]),
            }
        )
    return rows


def _format_value(value: str | float) -> str:
    if isinstance(value, str):
        return value
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}"
