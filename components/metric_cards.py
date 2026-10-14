"""Metric cards row."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services.swim_analytics import total_pb_seconds_improved


def render_metric_cards(full_df: pd.DataFrame, filtered_df: pd.DataFrame) -> None:
    total_swims = len(filtered_df)
    distinct_events = filtered_df[["stroke", "distance", "course"]].drop_duplicates().shape[0]
    pb_total = int(full_df["is_pb"].sum()) if not full_df.empty else 0
    pb_in_range = int(filtered_df["is_pb"].sum()) if not filtered_df.empty else 0

    cols = st.columns(4)
    cols[0].metric("🏊 Total Swims", total_swims)
    cols[1].metric("🎯 Different Events", distinct_events)
    cols[2].metric("⭐ Personal Bests (all time)", pb_total)
    cols[3].metric("🎉 PBs in Selected Range", pb_in_range)

    improvement = total_pb_seconds_improved(filtered_df)
    if improvement > 0:
        st.success(
            f"💪 Look how far you've come! You've improved by a total of "
            f"**{improvement:.2f} seconds** across your events in this view!"
        )
