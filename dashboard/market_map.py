from __future__ import annotations

import difflib
import sys
import time
from datetime import date as Date
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.config import load_dashboard_config
from dashboard.data_loader import available_dates, load_market_map_rows
from dashboard.plotting.market_map_plot import (
    build_market_map_figure,
    build_trajectory_figure,
)


ASSET_CATEGORIES = ["Core", "Instruments"]
FUNDING_STATUSES = ["Leveraging", "Deleveraging"]
RELATIVE_STRENGTH_STATUSES = ["Lag", "Weakening", "Improving", "Lead"]


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Asset and Positioning Monitor", layout="wide")
    _inject_dashboard_styles(st)

    dashboard_config = load_dashboard_config("config.yaml")
    market_map_config = dashboard_config.market_map
    rows = load_market_map_rows(dashboard_config.storage_root, market_map_config)
    if not rows:
        st.warning("No processed dashboard data found. Build processed series first.")
        return

    dates = available_dates(rows)
    _init_session_state(st, dates)
    _sync_current_date(st, dates)

    axis_ranges = _axis_ranges(rows)
    st.title("Asset and Positioning Monitor")

    with st.container(border=True):
        category, funding_statuses, rs_statuses, search_query = _render_filter_bar(st)

    selected_date = st.session_state["selected_date"]
    filtered_rows = _filter_rows(
        rows,
        selected_date=selected_date,
        asset_category=category,
        funding_statuses=funding_statuses,
        rs_statuses=rs_statuses,
        search_query=search_query,
    )
    matching_ids = _matching_asset_ids(filtered_rows, search_query)
    highlighted_ids = matching_ids if len(matching_ids) == 1 else set()
    _preserve_or_clear_selection(st, rows, filtered_rows, selected_date)

    st.markdown(f"**Date:** {_format_date(selected_date)}")
    selected_asset_id = st.session_state.get("selected_asset_id")
    if selected_asset_id:
        chart_col, detail_col = st.columns([4, 1.25], gap="large")
    else:
        chart_col = st.container()
        detail_col = None

    with chart_col:
        if not filtered_rows:
            st.info("No assets match the current filters.")
        else:
            event = st.plotly_chart(
                build_market_map_figure(
                    filtered_rows,
                    market_map_config,
                    highlighted_asset_ids=highlighted_ids,
                    selected_asset_id=selected_asset_id,
                    axis_ranges=axis_ranges,
                    height=620,
                ),
                width="stretch",
                key="asset_scatter",
                on_select="rerun",
                selection_mode="points",
                config={"displayModeBar": False, "responsive": True},
            )
            clicked_asset_id = _selected_asset_from_event(event)
            if clicked_asset_id and clicked_asset_id != st.session_state.get("selected_asset_id"):
                st.session_state["selected_asset_id"] = clicked_asset_id
                st.rerun()

    if detail_col is not None:
        with detail_col:
            _render_detail_panel(st, rows, selected_date, selected_asset_id, axis_ranges)

    _render_timeline(st, dates)
    _advance_playback(st, dates)


def _init_session_state(st: Any, dates: list[str]) -> None:
    defaults = {
        "asset_category": "Core",
        "funding_statuses": list(FUNDING_STATUSES),
        "rs_statuses": list(RELATIVE_STRENGTH_STATUSES),
        "asset_search": "",
        "selected_date": dates[-1],
        "date_timeline": dates[-1],
        "selected_asset_id": None,
        "timeline_playing": False,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("calendar_date", Date.fromisoformat(st.session_state["selected_date"]))


def _sync_current_date(st: Any, dates: list[str]) -> None:
    current = st.session_state.get("selected_date")
    if current not in dates:
        st.session_state["selected_date"] = dates[-1]
    if st.session_state.get("date_timeline") not in dates:
        st.session_state["date_timeline"] = st.session_state["selected_date"]
    st.session_state["calendar_date"] = Date.fromisoformat(st.session_state["selected_date"])


def _render_filter_bar(st: Any) -> tuple[str, list[str], list[str], str]:
    cat_col, funding_col, rs_col, search_col = st.columns([1.3, 1.5, 2.1, 1.9], gap="large")
    with cat_col:
        category = st.radio(
            "Asset Category",
            ASSET_CATEGORIES,
            key="asset_category",
            horizontal=True,
        )
    with funding_col:
        funding_statuses = st.multiselect(
            "Funding Status",
            FUNDING_STATUSES,
            key="funding_statuses",
            placeholder="Choose statuses",
        )
    with rs_col:
        rs_statuses = st.multiselect(
            "Relative Strength Status",
            RELATIVE_STRENGTH_STATUSES,
            key="rs_statuses",
            placeholder="Choose statuses",
        )
    with search_col:
        st.text_input(
            "Asset Search",
            key="asset_search",
            placeholder="Search asset by name or symbol",
        )
        st.button("Clear Search", on_click=_clear_search, use_container_width=True)
    return category, list(funding_statuses), list(rs_statuses), st.session_state["asset_search"]


def _clear_search() -> None:
    import streamlit as st

    st.session_state["asset_search"] = ""


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    selected_date: str,
    asset_category: str,
    funding_statuses: list[str],
    rs_statuses: list[str],
    search_query: str,
) -> list[dict[str, Any]]:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return []
    frame = frame[frame["date"] == selected_date]
    frame = frame[frame["asset_class"] == _asset_category_value(asset_category)]
    frame = frame[frame["flow_state"].isin(funding_statuses)]
    frame = frame[frame["rs_state"].isin(rs_statuses)]
    filtered = frame.to_dict("records")
    if search_query.strip():
        filtered = [row for row in filtered if _row_matches_query(row, search_query)]
    return filtered


def _matching_asset_ids(rows: list[dict[str, Any]], query: str) -> set[str]:
    if not query.strip():
        return set()
    return {str(row["asset_id"]) for row in rows if _row_matches_query(row, query)}


def _row_matches_query(row: dict[str, Any], query: str) -> bool:
    terms = [term.strip().lower() for term in query.replace(",", " ").split() if term.strip()]
    if not terms:
        return True
    symbol = str(row["asset_id"]).lower()
    name = str(row["asset_name"]).lower()
    haystack = f"{symbol} {name}"
    return all(_term_matches(term, haystack, symbol, name) for term in terms)


def _term_matches(term: str, haystack: str, symbol: str, name: str) -> bool:
    if term in haystack:
        return True
    symbol_score = difflib.SequenceMatcher(None, term, symbol).ratio()
    name_score = max((difflib.SequenceMatcher(None, term, part).ratio() for part in name.split()), default=0)
    return max(symbol_score, name_score) >= 0.72


def _preserve_or_clear_selection(
    st: Any,
    rows: list[dict[str, Any]],
    filtered_rows: list[dict[str, Any]],
    selected_date: str,
) -> None:
    selected_asset_id = st.session_state.get("selected_asset_id")
    if not selected_asset_id:
        return
    if selected_asset_id in {str(row["asset_id"]) for row in filtered_rows}:
        return
    date_rows = [row for row in rows if row["date"] == selected_date]
    if selected_asset_id in {str(row["asset_id"]) for row in date_rows}:
        st.session_state["selected_asset_id"] = None


def _selected_asset_from_event(event: Any) -> str | None:
    if not event:
        return None
    points = getattr(getattr(event, "selection", None), "points", None)
    if points is None and isinstance(event, dict):
        points = event.get("selection", {}).get("points", [])
    if not points:
        return None
    customdata = points[0].get("customdata") if isinstance(points[0], dict) else None
    if customdata and len(customdata) > 1:
        return str(customdata[1])
    return None


def _render_detail_panel(
    st: Any,
    rows: list[dict[str, Any]],
    selected_date: str,
    selected_asset_id: str | None,
    axis_ranges: dict[str, list[float]],
) -> None:
    if not selected_asset_id:
        return
    current_row = next(
        (row for row in rows if row["date"] == selected_date and str(row["asset_id"]) == selected_asset_id),
        None,
    )
    if current_row is None:
        with st.container(border=True):
            st.warning("The selected asset has no data for this date.")
            st.button("Clear Selection", on_click=_clear_selection, use_container_width=True)
        return

    accent = _trend_color(float(current_row["trend_score"]))
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="asset-summary" style="border-left-color: {accent};">
              <div class="asset-symbol">{current_row["asset_id"]}</div>
              <div class="asset-name">{current_row["asset_name"]}</div>
              <div class="asset-score">{float(current_row["trend_score"]):.2f}</div>
              <div class="asset-caption">Current Trend Score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        left, right = st.columns(2)
        left.metric("Relative Strength", f"{float(current_row['rs_score']):.2f}")
        right.metric("Leverage Score", f"{float(current_row['flow_score']):.2f}")
        st.caption(f"Funding Status: {current_row['flow_state']}")
        st.caption(f"Relative Strength Status: {current_row['rs_state']}")
        st.caption(f"Selected Date: {_format_date(selected_date)}")

    with st.container(border=True):
        st.subheader("Recent 30-Day Trajectory")
        trajectory_rows = _trajectory_rows(rows, selected_asset_id, selected_date)
        if not trajectory_rows:
            st.info("No trajectory data is available for this asset.")
        else:
            st.plotly_chart(
                build_trajectory_figure(trajectory_rows, axis_ranges=axis_ranges),
                width="stretch",
                config={"displayModeBar": False, "responsive": True},
            )
        st.button("Clear Selection", on_click=_clear_selection, use_container_width=True)


def _clear_selection() -> None:
    import streamlit as st

    st.session_state["selected_asset_id"] = None


def _trajectory_rows(rows: list[dict[str, Any]], selected_asset_id: str, selected_date: str) -> list[dict[str, Any]]:
    asset_rows = [
        row
        for row in rows
        if str(row["asset_id"]) == selected_asset_id and row["date"] <= selected_date
    ]
    return sorted(asset_rows, key=lambda row: row["date"])[-30:]


def _render_timeline(st: Any, dates: list[str]) -> None:
    with st.container(border=True):
        play_col, prev_col, next_col, slider_col, calendar_col = st.columns([0.7, 0.7, 0.7, 5.6, 1.2])
        with play_col:
            label = "Pause" if st.session_state["timeline_playing"] else "Play"
            st.button(label, on_click=_toggle_playback, use_container_width=True)
        with prev_col:
            st.button("Previous", on_click=_move_date, args=(-1, dates), use_container_width=True)
        with next_col:
            st.button("Next", on_click=_move_date, args=(1, dates), use_container_width=True)
        with slider_col:
            st.select_slider(
                "Date Timeline",
                options=dates,
                key="date_timeline",
                on_change=_timeline_changed,
                label_visibility="collapsed",
            )
        st.session_state["calendar_date"] = Date.fromisoformat(st.session_state["selected_date"])
        with calendar_col:
            st.date_input(
                "Calendar",
                key="calendar_date",
                on_change=_calendar_changed,
                args=(dates,),
            )


def _toggle_playback() -> None:
    import streamlit as st

    st.session_state["timeline_playing"] = not st.session_state["timeline_playing"]


def _timeline_changed() -> None:
    import streamlit as st

    st.session_state["selected_date"] = st.session_state["date_timeline"]


def _move_date(step: int, dates: list[str]) -> None:
    import streamlit as st

    current_index = dates.index(st.session_state["selected_date"])
    next_index = max(0, min(current_index + step, len(dates) - 1))
    st.session_state["selected_date"] = dates[next_index]
    st.session_state["date_timeline"] = dates[next_index]
    if next_index == len(dates) - 1:
        st.session_state["timeline_playing"] = False


def _calendar_changed(dates: list[str]) -> None:
    import streamlit as st

    selected = st.session_state["calendar_date"]
    if isinstance(selected, Date):
        target = selected.isoformat()
        st.session_state["selected_date"] = min(dates, key=lambda value: abs(Date.fromisoformat(value) - selected))
        st.session_state["date_timeline"] = st.session_state["selected_date"]
        if target > dates[-1] or target < dates[0]:
            st.session_state["calendar_date"] = Date.fromisoformat(st.session_state["selected_date"])


def _advance_playback(st: Any, dates: list[str]) -> None:
    if not st.session_state["timeline_playing"]:
        return
    current_index = dates.index(st.session_state["selected_date"])
    if current_index >= len(dates) - 1:
        st.session_state["timeline_playing"] = False
        return
    time.sleep(0.75)
    st.session_state["selected_date"] = dates[current_index + 1]
    st.session_state["date_timeline"] = dates[current_index + 1]
    st.rerun()


def _asset_category_value(label: str) -> str:
    return {"Core": "core", "Instruments": "instruments"}[label]


def _axis_ranges(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    from dashboard.plotting.market_map_plot import _score_axis_ranges

    return _score_axis_ranges(rows)


def _format_date(value: str) -> str:
    return Date.fromisoformat(value).strftime("%b %-d, %Y")


def _trend_color(score: float) -> str:
    if score >= 35:
        return "#16a34a"
    if score <= -35:
        return "#dc2626"
    return "#facc15"


def _inject_dashboard_styles(st: Any) -> None:
    st.markdown(
        """
        <style>
        :root {
            --primary: #2563eb;
            --surface: #ffffff;
            --border: #e2e8f0;
            --text: #0f172a;
            --muted: #64748b;
        }
        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            letter-spacing: 0;
        }
        .stApp {
            background: #f8fafc;
            color: var(--text);
        }
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1.25rem;
            max-width: 1500px;
        }
        h1 {
            font-size: 1.45rem !important;
            font-weight: 700 !important;
            margin-bottom: 0.75rem !important;
        }
        h3 {
            font-size: 1rem !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--border) !important;
            border-radius: 8px !important;
            background: var(--surface);
        }
        [data-testid="stMetric"] {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 0.45rem 0.55rem;
            background: #ffffff;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.15rem;
        }
        div[role="radiogroup"] {
            gap: 0.45rem;
        }
        div[role="radiogroup"] label {
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.35rem 0.55rem;
            background: #ffffff;
        }
        div[role="radiogroup"] label:has(input:checked) {
            border-color: var(--primary);
            background: #eff6ff;
            color: var(--primary);
        }
        .asset-summary {
            border-left: 4px solid;
            padding-left: 0.75rem;
        }
        .asset-symbol {
            font-size: 1.2rem;
            font-weight: 750;
            line-height: 1.2;
        }
        .asset-name {
            color: var(--muted);
            font-size: 0.85rem;
            margin-bottom: 0.65rem;
        }
        .asset-score {
            font-size: 1.8rem;
            font-weight: 750;
            line-height: 1;
        }
        .asset-caption {
            color: var(--muted);
            font-size: 0.8rem;
            margin-top: 0.2rem;
        }
        @media (max-width: 900px) {
            .main .block-container {
                padding-left: 0.7rem;
                padding-right: 0.7rem;
            }
            h1 {
                font-size: 1.25rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
