from __future__ import annotations

from typing import Any

from dashboard.scoring_rules import normalized_marker_sizes


def build_market_map_figure(
    rows: list[dict[str, Any]],
    market_map_config: dict[str, Any],
    *,
    highlighted_asset_ids: set[str] | None = None,
    label_mode: str = "candidates_and_matches",
    height: int = 720,
    show_legend: bool = True,
):
    import plotly.graph_objects as go

    highlighted_asset_ids = highlighted_asset_ids or set()
    size_config = market_map_config.get("size", {})
    sizes = normalized_marker_sizes(
        [float(row["flow_score"]) for row in rows],
        min_size=float(size_config.get("min", 8)),
        max_size=float(size_config.get("max", 42)),
    )
    colors = market_map_config.get("colors", {})
    symbols = market_map_config.get("symbols", {})

    enriched: list[dict[str, Any]] = []
    for row, size in zip(rows, sizes):
        highlighted = str(row["asset_id"]) in highlighted_asset_ids
        should_label = _should_label(row, highlighted, label_mode)
        enriched.append(
            {
                **row,
                "_size": size * (1.35 if highlighted else 1),
                "_highlighted": highlighted,
                "_opacity": 1.0 if not highlighted_asset_ids or highlighted else 0.18,
                "_line_width": 2.5 if highlighted else 0.5,
                "_label": row["asset_id"] if should_label else "",
            }
        )

    fig = go.Figure()
    groups = sorted({(row["flow_state"], row["asset_class"]) for row in enriched})
    for flow_state, asset_class in groups:
        group_rows = [row for row in enriched if row["flow_state"] == flow_state and row["asset_class"] == asset_class]
        fig.add_trace(
            go.Scatter(
                x=[row["rs_score"] for row in group_rows],
                y=[row["trend_score"] for row in group_rows],
                mode="markers+text",
                name=f"{flow_state} / {asset_class}",
                text=[row["_label"] for row in group_rows],
                textposition="top center",
                textfont={"size": 11, "color": "#22313f"},
                marker={
                    "size": [row["_size"] for row in group_rows],
                    "color": colors.get(flow_state, colors.get("Neutral", "#7a869a")),
                    "symbol": symbols.get(asset_class, "circle"),
                    "opacity": [row["_opacity"] for row in group_rows],
                    "line": {
                        "color": ["#111827" if row["_highlighted"] else "#ffffff" for row in group_rows],
                        "width": [row["_line_width"] for row in group_rows],
                    },
                },
                customdata=[
                    [
                        row["asset_name"],
                        row["asset_id"],
                        row["asset_class"],
                        row["date"],
                        row["trend_score"],
                        row["trend_state"],
                        row["rs_score"],
                        row["rs_state"],
                        row["flow_score"],
                        row["flow_state"],
                        "Yes" if row["long_candidate"] else "No",
                        "Yes" if row["short_candidate"] else "No",
                    ]
                    for row in group_rows
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "Asset ID: %{customdata[1]}<br>"
                    "Asset Class: %{customdata[2]}<br>"
                    "Date: %{customdata[3]}<br><br>"
                    "Trend Score: %{customdata[4]:.2f}<br>"
                    "Trend State: %{customdata[5]}<br>"
                    "RS Score: %{customdata[6]:.2f}<br>"
                    "RS State: %{customdata[7]}<br>"
                    "Flow Score: %{customdata[8]:.2f}<br>"
                    "Flow State: %{customdata[9]}<br><br>"
                    "Long Candidate: %{customdata[10]}<br>"
                    "Short Candidate: %{customdata[11]}"
                    "<extra></extra>"
                ),
            )
        )

    quadrants = market_map_config.get("quadrants", {})
    x_midline = float(quadrants.get("x_midline", 0))
    y_midline = float(quadrants.get("y_midline", 0))
    fig.add_vline(x=x_midline, line_width=1, line_dash="dash", line_color="#9aa5b1")
    fig.add_hline(y=y_midline, line_width=1, line_dash="dash", line_color="#9aa5b1")
    _focus_axes_on_assets(fig, rows)
    _add_quadrant_labels(fig, rows)
    fig.update_layout(
        title="Market Map",
        xaxis_title="RS Score",
        yaxis_title="Trend Score",
        template="plotly_white",
        height=height,
        margin={"l": 34, "r": 12, "t": 44, "b": 36},
        legend_title_text="Flow / Asset Class",
        showlegend=show_legend,
        dragmode="pan",
    )
    fig.update_xaxes(fixedrange=False)
    fig.update_yaxes(fixedrange=False)
    return fig


def _should_label(row: dict[str, Any], highlighted: bool, label_mode: str) -> bool:
    if label_mode == "none":
        return False
    if label_mode == "matches_only":
        return highlighted
    return highlighted or bool(row["long_candidate"]) or bool(row["short_candidate"])


def _focus_axes_on_assets(fig, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    x_values = [float(row["rs_score"]) for row in rows]
    y_values = [float(row["trend_score"]) for row in rows]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)
    x_pad = max((x_max - x_min) * 0.08, 5)
    y_pad = max((y_max - y_min) * 0.08, 5)
    fig.update_xaxes(range=[x_min - x_pad, x_max + x_pad])
    fig.update_yaxes(range=[y_min - y_pad, y_max + y_pad])


def _add_quadrant_labels(fig, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    x_values = [float(row["rs_score"]) for row in rows]
    y_values = [float(row["trend_score"]) for row in rows]
    labels = [
        (max(x_values), max(y_values), "Long watch"),
        (min(x_values), max(y_values), "Repair watch"),
        (min(x_values), min(y_values), "Short watch"),
        (max(x_values), min(y_values), "Early strength"),
    ]
    for x, y, text in labels:
        fig.add_annotation(x=x, y=y, text=text, showarrow=False, font={"size": 11, "color": "#667085"})
