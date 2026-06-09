from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.config import load_dashboard_config
from dashboard.data_loader import (
    available_dates,
    filter_market_map_rows,
    load_market_map_rows,
    matching_asset_ids,
)
from dashboard.plotting.market_map_plot import build_market_map_figure
from dashboard.ui.filters import score_bounds


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Market Map", layout="wide")
    _inject_mobile_styles(st)
    st.title("Market Map")

    dashboard_config = load_dashboard_config("config.yaml")
    market_map_config = dashboard_config.market_map
    rows = load_market_map_rows(dashboard_config.storage_root, market_map_config)
    if not rows:
        st.warning("No processed Market Map data found. Build processed series first.")
        return

    dates = available_dates(rows)
    selected_date = st.select_slider("Date", options=dates, value=dates[-1])
    date_rows = filter_market_map_rows(rows, date=selected_date)

    with st.expander("Filters", expanded=True):
        search_query = st.text_input("Search asset_id / asset_name", placeholder="ES1, gold, BTC...")
        control_left, control_right = st.columns(2)
        asset_classes = sorted({row["asset_class"] for row in date_rows})
        selected_asset_class = control_left.radio("Asset Class", ["All", *asset_classes], horizontal=True)

        flow_states = sorted({row["flow_state"] for row in date_rows})
        selected_flow_states = control_right.multiselect("Flow State", flow_states, default=flow_states)

        trend_bounds = score_bounds(date_rows, "trend_score", (-100, 100))
        rs_bounds = score_bounds(date_rows, "rs_score", (-100, 120))
        flow_bounds = score_bounds(date_rows, "flow_score", (-5, 5))
        selected_trend = st.slider("Trend Score", trend_bounds[0], trend_bounds[1], trend_bounds)
        selected_rs = st.slider("RS Score", rs_bounds[0], rs_bounds[1], rs_bounds)
        selected_flow = st.slider("Flow Score", flow_bounds[0], flow_bounds[1], flow_bounds)

        display_left, display_right = st.columns(2)
        mobile_compact = display_left.toggle("Phone friendly", value=True)
        label_mode = display_right.selectbox(
            "Labels",
            ["matches_only", "candidates_and_matches", "none"],
            index=0,
            format_func=lambda value: {
                "matches_only": "Search matches only",
                "candidates_and_matches": "Candidates + matches",
                "none": "No labels",
            }[value],
        )
    filtered_rows = filter_market_map_rows(
        date_rows,
        asset_classes=set(asset_classes if selected_asset_class == "All" else [selected_asset_class]),
        flow_states=set(selected_flow_states),
        trend_range=selected_trend,
        rs_range=selected_rs,
        flow_range=selected_flow,
    )
    highlighted = matching_asset_ids(filtered_rows, search_query)

    left, middle, right = st.columns(3)
    left.metric("Assets", len(filtered_rows))
    middle.metric("Long Candidates", sum(1 for row in filtered_rows if row["long_candidate"]))
    right.metric("Short Candidates", sum(1 for row in filtered_rows if row["short_candidate"]))

    figure = build_market_map_figure(
        filtered_rows,
        market_map_config,
        highlighted_asset_ids=highlighted,
        label_mode=label_mode,
        height=520 if mobile_compact else 720,
        show_legend=not mobile_compact,
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config={
            "displayModeBar": not mobile_compact,
            "scrollZoom": True,
            "responsive": True,
        },
    )
    _render_mobile_tables(st, filtered_rows, highlighted)


def _inject_mobile_styles(st) -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
        :root {
            --md-primary: #0b57d0;
            --md-primary-container: #d3e3fd;
            --md-on-primary: #ffffff;
            --md-on-surface: #1f1f1f;
            --md-outline: #747775;
        }
        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: "Roboto", "Noto Sans SC", Arial, sans-serif;
            letter-spacing: 0;
        }
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1.5rem;
            max-width: 1180px;
        }
        h1 {
            color: var(--md-on-surface);
            font-weight: 500;
            letter-spacing: 0;
        }
        [data-testid="stMetric"] {
            border: 1px solid #e4e7ec;
            border-radius: 8px;
            padding: 0.6rem 0.75rem;
            background: #ffffff;
        }
        [data-testid="stSidebar"] [aria-selected="true"],
        [data-testid="stSidebar"] [aria-current="page"],
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: var(--md-primary-container) !important;
            color: var(--md-primary) !important;
        }
        div[role="radiogroup"] {
            gap: 0.75rem;
        }
        div[role="radiogroup"] label {
            color: var(--md-on-surface);
            font-weight: 700;
        }
        div[role="radiogroup"] [data-testid="stMarkdownContainer"] p {
            font-size: 1rem;
        }
        div[role="radiogroup"] label > div:first-child {
            border-color: #11131d !important;
        }
        div[role="radiogroup"] label:has(input:checked) > div:first-child {
            border-color: #6750f8 !important;
            background: #6750f8 !important;
            box-shadow: inset 0 0 0 5px #ffffff;
        }
        [data-baseweb="slider"] div {
            border-radius: 999px;
        }
        [data-baseweb="slider"] [role="slider"] {
            background-color: #fbbc04 !important;
            border-color: #fbbc04 !important;
            box-shadow: none !important;
        }
        [data-baseweb="slider"] [role="slider"] + div,
        [data-baseweb="slider"] div[style*="background-color"] {
            background-color: #fbbc04;
        }
        @media (max-width: 760px) {
            .main .block-container {
                padding-left: 0.55rem;
                padding-right: 0.55rem;
            }
            h1 {
                font-size: 1.35rem !important;
                margin-bottom: 0.5rem !important;
            }
            [data-testid="stExpander"] {
                border-radius: 8px;
            }
            [data-testid="stMetric"] {
                padding: 0.45rem 0.55rem;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.05rem;
            }
            [data-testid="stHorizontalBlock"] {
                gap: 0.45rem;
            }
            [data-testid="stPlotlyChart"] {
                margin-left: -0.35rem;
                margin-right: -0.35rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_mobile_tables(st, rows: list[dict], highlighted: set[str]) -> None:
    if highlighted:
        matched_rows = [row for row in rows if str(row["asset_id"]) in highlighted]
        st.dataframe(_table_rows(matched_rows), width="stretch", height=min(260, 42 + 36 * max(len(matched_rows), 1)))
        return

    candidates = [
        row
        for row in rows
        if row["long_candidate"] or row["short_candidate"]
    ]
    if candidates:
        candidates = sorted(candidates, key=lambda row: (not row["long_candidate"], -abs(row["flow_score"])))[:20]
        with st.expander("Candidate list", expanded=False):
            st.dataframe(_table_rows(candidates), width="stretch", height=320)


def _table_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "ID": row["asset_id"],
            "Name": row["asset_name"],
            "Trend": round(float(row["trend_score"]), 2),
            "RS": round(float(row["rs_score"]), 2),
            "Flow": round(float(row["flow_score"]), 2),
            "Flow State": row["flow_state"],
            "Long": row["long_candidate"],
            "Short": row["short_candidate"],
        }
        for row in rows
    ]


if __name__ == "__main__":
    main()
