"""Plotly charts for the dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services.swim_analytics import personal_best_table, running_pb_progression
from utils.time_utils import format_seconds

COLOR_PRIMARY = "#1f77b4"
COLOR_PB = "#ff7f0e"
COLOR_LINE = "#2ca02c"


def _invert_yaxis(fig: go.Figure) -> None:
    fig.update_yaxes(autorange="reversed", title_text="Time (seconds)")


def render_progression_charts(event_df: pd.DataFrame, event_label: str) -> None:
    """Swim-time progression and running-PB charts for one event."""
    official = event_df[event_df["is_official"]].sort_values("date")

    if official.empty:
        st.info(
            f"No recorded swims yet for **{event_label}**. "
            "Try another event or add results to the sheet!"
        )
        return

    st.subheader(f"📈 Swim Times — {event_label}")

    fig = go.Figure()
    non_pb = official[~official["is_pb"]]
    pb = official[official["is_pb"]]

    fig.add_trace(
        go.Scatter(
            x=official["date"],
            y=official["time_seconds"],
            mode="lines",
            line=dict(color="#bbbbbb", width=2),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=non_pb["date"],
            y=non_pb["time_seconds"],
            mode="markers",
            name="Swims",
            marker=dict(size=10, color=COLOR_PRIMARY),
            customdata=list(
                zip(
                    non_pb["date"].dt.strftime("%b %d, %Y"),
                    non_pb["time_display"],
                    non_pb["meet"],
                )
            ),
            hovertemplate="%{customdata[0]}<br>Time: %{customdata[1]}<br>Meet: %{customdata[2]}<extra>Swim</extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=pb["date"],
            y=pb["time_seconds"],
            mode="markers",
            name="Personal Best ⭐",
            marker=dict(size=14, color=COLOR_PB, symbol="star"),
            customdata=list(
                zip(
                    pb["date"].dt.strftime("%b %d, %Y"),
                    pb["time_display"],
                    pb["meet"],
                )
            ),
            hovertemplate="%{customdata[0]}<br>New PB: %{customdata[1]}<br>Meet: %{customdata[2]}<extra>⭐ New Personal Best!</extra>",
        )
    )
    _invert_yaxis(fig)
    fig.update_xaxes(title_text="Date")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

    if len(pb) >= 2:
        st.balloons()
        st.success(f"🎉 **New Personal Best!** You've set {len(pb)} personal bests in this event. Keep it up, Riya!")

    # Running PB progression
    st.subheader(f"⭐ Personal Best Journey — {event_label}")
    prog = running_pb_progression(event_df)
    if prog.empty or len(prog) < 2:
        st.info(
            "Swim this event again to see your personal-best journey grow!"
        )
    else:
        fig2 = go.Figure(
            go.Scatter(
                x=prog["date"],
                y=prog["best_seconds"],
                mode="lines+markers",
                line=dict(color=COLOR_LINE, width=3, shape="hv"),
                marker=dict(size=12, symbol="star", color=COLOR_PB),
                customdata=list(
                    zip(
                        prog["date"].dt.strftime("%b %d, %Y"),
                        prog["best_display"],
                        prog["meet"],
                    )
                ),
                hovertemplate="%{customdata[0]}<br>New best: %{customdata[1]}<br>Meet: %{customdata[2]}<extra>🏅 Record improved!</extra>",
            )
        )
        _invert_yaxis(fig2)
        fig2.update_xaxes(title_text="Date")
        fig2.update_layout(height=320, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig2, use_container_width=True)

        improvement = prog["best_seconds"].iloc[0] - prog["best_seconds"].iloc[-1]
        if improvement > 0:
            st.info(
                f"🌟 You've gotten **{improvement:.2f} seconds faster** in this event "
                f"since {prog['date'].iloc[0].strftime('%b %Y')}! You're getting closer "
                "to your next milestone!"
            )


def render_pb_table(df: pd.DataFrame) -> None:
    st.subheader("🏅 Your Best Times")
    table = personal_best_table(df)
    if table.empty:
        st.info("No official results yet to compute personal bests.")
        return
    for course in sorted(table["Course"].unique()):
        st.markdown(f"**{course}**")
        sub = table[table["Course"] == course][["Event", "Best Time", "Date", "Meet"]]
        st.dataframe(sub, use_container_width=True, hide_index=True)


def render_recent_swims(df: pd.DataFrame, limit: int = 15) -> None:
    st.subheader("🕒 Recent Swims")
    if df.empty:
        st.info("No swims match the current filters. Try resetting them!")
        return
    recent = df.sort_values("date", ascending=False).head(limit).copy()
    recent["Date"] = recent["date"].dt.strftime("%b %d, %Y")
    recent["Event"] = recent["event"]
    recent["Course"] = recent["course"]
    recent["Time"] = recent["time_display"]
    recent["Meet"] = recent["meet"]
    recent["⭐ PB"] = recent["is_pb"].map({True: "⭐", False: ""})
    st.dataframe(
        recent[["Date", "Event", "Course", "Time", "Meet", "⭐ PB"]],
        use_container_width=True,
        hide_index=True,
    )
