"""Swim analytics: cleaning, personal bests, progression, improvements."""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd

from utils.time_utils import format_seconds, parse_time_to_seconds
from utils.validation import (
    normalize_course,
    normalize_result_type,
    normalize_stroke,
)

EXCLUDED_RESULT_TYPE_KEYWORDS = (
    "dq",
    "disqualified",
    "relay",
    "split",
    "exhibition",
    "unofficial",
    "no show",
    "scratch",
)


def clean_results(raw: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Clean and normalize the raw Results frame.

    - Parses times into seconds (`time_seconds`).
    - Parses dates (`date` is a Timestamp).
    - Normalizes stroke, course, distance, result type.
    - Adds `event` label, `is_official`, `is_pb` columns.
    - Drops malformed rows (bad time/date/distance) with warnings.
    - Marks personal bests per swimmer+stroke+distance+course.
    """
    warnings: List[str] = []
    if raw.empty:
        return _empty_frame(), warnings

    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Silently drop fully-blank template rows (no date AND no time AND no event info)
    blank_mask = (
        (df["Swim Date"].astype(str).str.strip() == "")
        & (df["Time"].astype(str).str.strip() == "")
        & (df["Stroke"].astype(str).str.strip() == "")
        & (df["Distance"].astype(str).str.strip() == "")
    )
    df = df[~blank_mask].reset_index(drop=True)
    if df.empty:
        return _empty_frame(), warnings

    df["swimmer"] = df["Swimmer Name"].astype(str).str.strip()
    df["meet"] = df["Meet Name"].astype(str).str.strip()
    df["stroke"] = df["Stroke"].map(normalize_stroke)
    df["course"] = df["Course"].map(normalize_course)
    df["distance"] = pd.to_numeric(
        df["Distance"].astype(str).str.extract(r"(\d+)", expand=False),
        errors="coerce",
    )
    df["date"] = pd.to_datetime(df["Swim Date"], errors="coerce")
    df["time_seconds"] = df["Time"].map(parse_time_to_seconds)
    df["result_type"] = df["Result Type"].map(normalize_result_type)
    df["time_display"] = df["time_seconds"].map(format_seconds)

    before = len(df)
    bad_rows = df[
        (df["swimmer"] == "")
        | df["stroke"].isna()
        | df["course"].isna()
        | df["distance"].isna()
        | df["date"].isna()
        | df["time_seconds"].isna()
    ]
    df = df.drop(bad_rows.index).reset_index(drop=True)
    if len(bad_rows) > 0:
        warnings.append(
            f"{len(bad_rows)} of {before} row(s) were skipped because they had "
            "a missing or invalid swimmer, date, distance, stroke, course, or time."
        )

    if df.empty:
        return _empty_frame(), warnings

    df["distance"] = df["distance"].astype(int)
    df["event"] = df["distance"].astype(str) + " " + df["stroke"]

    # Official for PB purposes: nothing indicating DQ/relay/split/etc.
    def _is_official(rt: str) -> bool:
        if not rt:
            return False  # missing status: don't assume official
        return not any(kw in rt for kw in EXCLUDED_RESULT_TYPE_KEYWORDS)

    df["is_official"] = df["result_type"].map(_is_official)

    df = df.sort_values(["date"]).reset_index(drop=True)
    df["is_pb"] = False

    for _, group in df.groupby(["swimmer", "stroke", "distance", "course"]):
        eligible = group[group["is_official"]]
        if eligible.empty:
            continue
        running_min = None
        for idx in eligible.sort_values("date").index:
            t = df.at[idx, "time_seconds"]
            if running_min is None or t < running_min:
                running_min = t
                df.at[idx, "is_pb"] = True

    return df, warnings


def _empty_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "swimmer", "meet", "stroke", "course", "distance", "date",
            "time_seconds", "result_type", "time_display", "event",
            "is_official", "is_pb",
        ]
    )


def personal_best_table(df: pd.DataFrame) -> pd.DataFrame:
    """One row per event+course with the best official time."""
    eligible = df[df["is_official"]]
    if eligible.empty:
        return pd.DataFrame(
            columns=["Event", "Course", "Best Time", "Date", "Meet"]
        )
    idx = eligible.groupby(["stroke", "distance", "course"])["time_seconds"].idxmin()
    best = eligible.loc[idx].copy()
    best["Event"] = best["event"]
    best["Course"] = best["course"]
    best["Best Time"] = best["time_display"]
    best["Date"] = best["date"].dt.strftime("%b %d, %Y")
    best["Meet"] = best["meet"]
    best = best.sort_values(["stroke", "distance", "course"])
    return best[["Event", "Course", "Best Time", "Date", "Meet", "stroke", "distance"]]


def running_pb_progression(df: pd.DataFrame) -> pd.DataFrame:
    """Running-best progression for a single event+course slice.

    Input should already be filtered to one stroke/distance/course/swimmer.
    Returns a frame with date and running best time, only at points where
    the record improved (step chart data).
    """
    eligible = df[df["is_official"]].sort_values("date")
    if eligible.empty:
        return pd.DataFrame(columns=["date", "best_seconds", "best_display", "meet"])
    best = None
    rows = []
    for _, row in eligible.iterrows():
        t = row["time_seconds"]
        if best is None or t < best:
            best = t
            rows.append(
                {
                    "date": row["date"],
                    "best_seconds": best,
                    "best_display": format_seconds(best),
                    "meet": row["meet"],
                }
            )
    return pd.DataFrame(rows)


def total_pb_seconds_improved(df: pd.DataFrame) -> float:
    """Total improvement (seconds) from first to current PB across events."""
    eligible = df[df["is_official"]]
    total = 0.0
    for _, group in eligible.groupby(["stroke", "distance", "course"]):
        g = group.sort_values("date")
        if len(g) >= 2:
            first_best = g.iloc[0]["time_seconds"]
            current_best = g["time_seconds"].min()
            if first_best > current_best:
                total += first_best - current_best
    return total
