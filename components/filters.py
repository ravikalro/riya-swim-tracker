"""Sidebar filter widgets for the dashboard."""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st


def swimmer_filter(df: pd.DataFrame, default_swimmer: str) -> str:
    swimmers = sorted(s for s in df["swimmer"].unique() if s)
    if not swimmers:
        return default_swimmer
    default_idx = swimmers.index(default_swimmer) if default_swimmer in swimmers else 0
    return st.sidebar.selectbox("Swimmer", swimmers, index=default_idx)


def _multiselect(label: str, options: List[str]) -> List[str]:
    return st.sidebar.multiselect(label, options=options, default=options)


def result_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render stroke/distance/course/date/meet filters and return the filtered frame."""
    if df.empty:
        return df

    if st.sidebar.button("Reset Filters"):
        st.rerun()

    strokes = sorted(df["stroke"].unique())
    distances = sorted(df["distance"].unique())
    courses = sorted(df["course"].unique())
    meets = sorted(m for m in df["meet"].unique() if m)

    sel_strokes = _multiselect("Stroke", strokes)
    sel_distances = st.sidebar.multiselect(
        "Distance", options=distances, default=distances, format_func=lambda d: f"{int(d)}"
    )
    sel_courses = _multiselect("Course", courses)
    sel_meets = _multiselect("Meet", meets)

    min_date = df["date"].min().date()
    max_date = df["date"].max().date()
    date_range: Tuple = st.sidebar.date_input(
        "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )

    df = df[
        df["stroke"].isin(sel_strokes)
        & df["distance"].isin(sel_distances)
        & df["course"].isin(sel_courses)
        & df["meet"].isin(sel_meets)
    ]
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start, end = date_range
        df = df[(df["date"].dt.date >= start) & (df["date"].dt.date <= end)]
    return df


def event_selector(df: pd.DataFrame) -> Optional[Tuple[str, int, str]]:
    """Select a single event (stroke, distance, course) for progression charts."""
    if df.empty:
        return None
    options = (
        df[["stroke", "distance", "course"]]
        .drop_duplicates()
        .sort_values(["stroke", "distance", "course"])
    )
    labels = [
        f"{int(r.distance)} {r.stroke} ({r.course})" for r in options.itertuples()
    ]
    choice = st.selectbox("Choose an event to explore", labels)
    i = labels.index(choice)
    row = options.iloc[i]
    return row["stroke"], int(row["distance"]), row["course"]
