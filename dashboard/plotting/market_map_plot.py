from __future__ import annotations

from typing import Any


TREND_COLOR_SCALE = [
    [0.0, "#dc2626"],
    [0.5, "#facc15"],
    [1.0, "#16a34a"],
]


def build_market_map_figure(
    rows: list[dict[str, Any]],
    market_map_config: dict[str, Any],
    *,
    highlighted_asset_ids: set[str] | None = None,
    selected_asset_id: str | None = None,
    axis_ranges: dict[str, list[float]] | None = None,
    height: int = 620,
    show_colorbar: bool = True,
):
    import plotly.graph_objects as go

    highlighted_asset_ids = highlighted_asset_ids or set()
    selected_asset_id = str(selected_asset_id) if selected_asset_id else None
    axis_ranges = axis_ranges or _score_axis_ranges(rows)
    trend_range = axis_ranges.get("trend_score", [-100, 100])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[row["rs_score"] for row in rows],
            y=[row["flow_score"] for row in rows],
            mode="markers+text",
            text=[
                _label_text(row, rows, highlighted_asset_ids, selected_asset_id)
                for row in rows
            ],
            textposition="top center",
            textfont={"size": 10, "color": "#334155"},
            marker={
                "size": [
                    18 if str(row["asset_id"]) == selected_asset_id else 13
                    for row in rows
                ],
                "color": [row["trend_score"] for row in rows],
                "colorscale": TREND_COLOR_SCALE,
                "cmin": trend_range[0],
                "cmax": trend_range[1],
                "showscale": show_colorbar,
                "colorbar": {
                    "title": {"text": "Trend Strength", "side": "top"},
                    "tickmode": "array",
                    "tickvals": [
                        trend_range[0],
                        (trend_range[0] + trend_range[1]) / 2,
                        trend_range[1],
                    ],
                    "ticktext": ["Weak", "Neutral", "Strong"],
                    "len": 0.32,
                    "thickness": 12,
                    "x": 0.98,
                    "y": 0.96,
                    "xanchor": "right",
                    "yanchor": "top",
                    "outlinewidth": 0,
                },
                "opacity": [_marker_opacity(row, highlighted_asset_ids, selected_asset_id) for row in rows],
                "line": {
                    "color": [
                        _marker_line_color(row, highlighted_asset_ids, selected_asset_id)
                        for row in rows
                    ],
                    "width": [
                        _marker_line_width(row, highlighted_asset_ids, selected_asset_id)
                        for row in rows
                    ],
                },
            },
            customdata=[
                [
                    row["asset_name"],
                    row["asset_id"],
                    asset_category_label(row["asset_class"]),
                    row["date"],
                    row["rs_score"],
                    row["flow_score"],
                    row["trend_score"],
                    row["flow_state"],
                    row["rs_state"],
                ]
                for row in rows
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Symbol: %{customdata[1]}<br>"
                "Asset Category: %{customdata[2]}<br>"
                "Date: %{customdata[3]}<br>"
                "Relative Strength: %{customdata[4]:.2f}<br>"
                "Leverage Score: %{customdata[5]:.2f}<br>"
                "Trend Score: %{customdata[6]:.2f}<br>"
                "Funding Status: %{customdata[7]}<br>"
                "Relative Strength Status: %{customdata[8]}"
                "<extra></extra>"
            ),
        )
    )

    _apply_axis_ranges(fig, axis_ranges)
    _add_reference_lines(fig, axis_ranges)
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin={"l": 54, "r": 20, "t": 12, "b": 48},
        showlegend=False,
        dragmode="pan",
        xaxis_title="Relative Strength",
        yaxis_title="Leverage Score",
        hovermode="closest",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False, fixedrange=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False, fixedrange=False)
    return fig


def build_trajectory_figure(
    rows: list[dict[str, Any]],
    *,
    axis_ranges: dict[str, list[float]] | None = None,
    height: int = 280,
):
    import plotly.graph_objects as go

    axis_ranges = axis_ranges or _score_axis_ranges(rows)
    fig = go.Figure()
    if rows:
        fig.add_trace(
            go.Scatter(
                x=[row["rs_score"] for row in rows],
                y=[row["flow_score"] for row in rows],
                mode="lines+markers",
                line={"color": "#2563eb", "width": 2},
                marker={
                    "size": [8 if index not in {0, len(rows) - 1} else 12 for index, _ in enumerate(rows)],
                    "color": [
                        "#94a3b8" if index == 0 else "#16a34a" if index == len(rows) - 1 else "#2563eb"
                        for index, _ in enumerate(rows)
                    ],
                    "line": {"color": "#ffffff", "width": 1},
                },
                customdata=[
                    [row["date"], row["rs_score"], row["flow_score"], row["trend_score"]]
                    for row in rows
                ],
                hovertemplate=(
                    "Date: %{customdata[0]}<br>"
                    "Relative Strength: %{customdata[1]:.2f}<br>"
                    "Leverage Score: %{customdata[2]:.2f}<br>"
                    "Trend Score: %{customdata[3]:.2f}"
                    "<extra></extra>"
                ),
            )
        )

    _apply_axis_ranges(fig, axis_ranges)
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin={"l": 40, "r": 10, "t": 8, "b": 38},
        showlegend=False,
        xaxis_title="Relative Strength",
        yaxis_title="Leverage Score",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=False)
    return fig


def asset_category_label(value: str) -> str:
    if value == "core":
        return "Core"
    if value == "instruments":
        return "Instruments"
    return str(value).strip().title()


def _score_axis_ranges(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    return {
        "rs_score": _score_range([float(row["rs_score"]) for row in rows], default=[0, 100]),
        "flow_score": _score_range([float(row["flow_score"]) for row in rows], default=[0, 100]),
        "trend_score": _score_range([float(row["trend_score"]) for row in rows], default=[-100, 100]),
    }


def _score_range(values: list[float], *, default: list[float]) -> list[float]:
    if not values:
        return list(default)
    low = min(values)
    high = max(values)
    if default == [-100, 100] and -100 <= low and high <= 100:
        return [-100, 100]
    if 0 <= low and high <= 100:
        return [0, 100]
    if low == high:
        return [low - 1, high + 1]
    padding = max((high - low) * 0.08, 1)
    return [low - padding, high + padding]


def _apply_axis_ranges(fig: Any, axis_ranges: dict[str, list[float]]) -> None:
    fig.update_xaxes(range=axis_ranges.get("rs_score", [0, 100]))
    fig.update_yaxes(range=axis_ranges.get("flow_score", [0, 100]))


def _add_reference_lines(fig: Any, axis_ranges: dict[str, list[float]]) -> None:
    x_range = axis_ranges.get("rs_score", [0, 100])
    y_range = axis_ranges.get("flow_score", [0, 100])
    x_mid = 50 if x_range == [0, 100] else (x_range[0] + x_range[1]) / 2
    y_mid = 50 if y_range == [0, 100] else (y_range[0] + y_range[1]) / 2
    fig.add_vline(x=x_mid, line_width=1, line_dash="dot", line_color="#cbd5e1")
    fig.add_hline(y=y_mid, line_width=1, line_dash="dot", line_color="#cbd5e1")


def _marker_opacity(row: dict[str, Any], highlighted_asset_ids: set[str], selected_asset_id: str | None) -> float:
    asset_id = str(row["asset_id"])
    if asset_id == selected_asset_id:
        return 1.0
    if highlighted_asset_ids:
        return 1.0 if asset_id in highlighted_asset_ids else 0.28
    return 0.9


def _label_text(
    row: dict[str, Any],
    rows: list[dict[str, Any]],
    highlighted_asset_ids: set[str],
    selected_asset_id: str | None,
) -> str:
    asset_id = str(row["asset_id"])
    if asset_id == selected_asset_id or asset_id in highlighted_asset_ids:
        return asset_id
    if len(rows) <= 80:
        return asset_id
    return ""


def _marker_line_color(row: dict[str, Any], highlighted_asset_ids: set[str], selected_asset_id: str | None) -> str:
    asset_id = str(row["asset_id"])
    if asset_id == selected_asset_id:
        return "#1d4ed8"
    if asset_id in highlighted_asset_ids:
        return "#0f172a"
    return "#ffffff"


def _marker_line_width(row: dict[str, Any], highlighted_asset_ids: set[str], selected_asset_id: str | None) -> float:
    asset_id = str(row["asset_id"])
    if asset_id == selected_asset_id:
        return 4
    if asset_id in highlighted_asset_ids:
        return 3
    return 0.8
