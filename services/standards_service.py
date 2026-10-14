"""USA Swimming 2024-2028 Motivational Standards: loading, lookup, and
level determination.

Data lives in ``data/standards/motivational_standards.json`` (extracted from
the official PDF by ``pipeline/extract_standards.py``) so the app needs no
network access at runtime.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

LEVELS = ["B", "BB", "A", "AA", "AAA", "AAAA"]

DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "standards" / "motivational_standards.json"
)

# The app's normalized stroke names -> PDF stroke codes.
_STROKE_TO_CODE = {
    "Freestyle": "FR",
    "Backstroke": "BK",
    "Breaststroke": "BR",
    "Butterfly": "FL",
    "Individual Medley": "IM",
}

_EVENT_CODE_TO_STROKE = {v: k for k, v in _STROKE_TO_CODE.items()}


class StandardsError(Exception):
    """Raised when the standards dataset cannot be loaded or is invalid."""


@dataclass(frozen=True)
class StandardRecord:
    age_group: str
    gender: str
    distance: int
    stroke: str  # PDF code, e.g. "FR"
    course: str  # SCY / SCM / LCM
    standards: dict  # level -> seconds


@dataclass(frozen=True)
class LevelResult:
    """Comparison of one personal best against one standards row."""

    achieved: Optional[str]        # highest achieved level, or None if below B
    next_target: Optional[str]     # next level to chase, None if faster than AAAA
    seconds_to_next: Optional[float]  # positive seconds to reach next_target
    at_highest: bool               # PB is at or faster than AAAA


def load_standards(path: Optional[Path] = None) -> list[StandardRecord]:
    """Load and validate the standards dataset. Raises StandardsError on problems."""
    path = path or DATA_PATH
    if not path.exists():
        raise StandardsError(
            f"Standards dataset not found at {path}. "
            "Run `python pipeline/extract_standards.py` to generate it."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StandardsError(f"Standards dataset is not valid JSON: {exc}") from exc

    records: list[StandardRecord] = []
    for i, raw in enumerate(payload.get("records", [])):
        try:
            levels = {lv: float(raw["standards"][lv]) for lv in LEVELS}
        except (KeyError, TypeError, ValueError):
            # Malformed standards are surfaced, never silently zero-filled.
            raise StandardsError(f"Record {i} has missing or malformed standards: {raw}")
        records.append(
            StandardRecord(
                age_group=str(raw["age_group"]),
                gender=str(raw["gender"]),
                distance=int(raw["distance"]),
                stroke=str(raw["stroke"]),
                course=str(raw["course"]),
                standards=levels,
            )
        )
    return records


def load_metadata(path: Optional[Path] = None) -> dict:
    path = path or DATA_PATH
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("metadata", {})


def available_age_groups(records: list[StandardRecord]) -> list[str]:
    order = ["10 & under", "11-12", "13-14", "15-16", "17-18"]
    present = {r.age_group for r in records}
    return [a for a in order if a in present]


def lookup_standards(
    records: list[StandardRecord],
    age_group: str,
    gender: str,
    stroke_name: str,
    distance: int,
    course: str,
) -> tuple[Optional[StandardRecord], Optional[str]]:
    """Find the standards for one event.

    ``stroke_name`` is the app's normalized stroke label (e.g. "Freestyle").
    Returns ``(record, warning)``. A warning non-None means the event could
    not be mapped/found and must be flagged rather than guessed.
    """
    code = _STROKE_TO_CODE.get(stroke_name)
    if code is None:
        return None, f"Can't map stroke {stroke_name!r} to a motivational standards event."
    match = [
        r for r in records
        if r.age_group == age_group
        and r.gender == gender
        and r.stroke == code
        and r.distance == distance
        and r.course == course
    ]
    if not match:
        return None, (
            f"No {age_group} {gender} standards found for "
            f"{distance} {stroke_name} ({course}) — this event may not have a standard."
        )
    if len(match) > 1:
        return None, f"Ambiguous standards for {distance} {stroke_name} ({course}) in {age_group} {gender}."
    return match[0], None


def determine_level(pb_seconds: float, standards: dict) -> LevelResult:
    """Determine the achieved motivational level for a personal best.

    A standard is achieved when the PB is equal to or faster than it (ties count).
    ``standards`` maps level -> seconds; times must decrease B -> AAAA.
    """
    achieved: Optional[str] = None
    for level in LEVELS:  # B is slowest; later levels are faster (harder)
        std = standards.get(level)
        if std is None:
            continue
        if pb_seconds <= std:  # tie counts as achieving the level
            achieved = level

    if achieved is None:
        b = standards.get("B")
        return LevelResult(
            achieved=None,
            next_target="B",
            seconds_to_next=round(pb_seconds - b, 2) if b is not None else None,
            at_highest=False,
        )
    if achieved == LEVELS[-1]:
        return LevelResult(achieved=achieved, next_target=None,
                           seconds_to_next=None, at_highest=True)
    next_level = LEVELS[LEVELS.index(achieved) + 1]
    nxt_std = standards.get(next_level)
    return LevelResult(
        achieved=achieved,
        next_target=next_level,
        seconds_to_next=round(pb_seconds - nxt_std, 2) if nxt_std is not None else None,
        at_highest=False,
    )


def build_comparison(pb_df, records: list[StandardRecord], age_group: str,
                     gender: str = "Girls"):
    """Build one comparison row per personal-best event for an age group.

    ``pb_df`` must have columns: event, course, stroke, distance,
    time_seconds, time_display, date.
    Returns (rows: list[dict], flags: list[str]).
    """
    import pandas as pd

    rows: list[dict] = []
    flags: list[str] = []
    eligible = pb_df.dropna(subset=["time_seconds"])
    if "is_official" in eligible.columns:
        # Relay results/splits, DQs etc. are never compared to standards.
        eligible = eligible[eligible["is_official"]]
    # Never mix courses/distances: group on the full event key.
    idx = []
    for _, g in eligible.groupby(["stroke", "distance", "course"]):
        idx.append(g["time_seconds"].idxmin())
    best = eligible.loc[idx] if idx else eligible

    for _, r in best.iterrows():
        rec, warn = lookup_standards(
            records, age_group, gender, r["stroke"], int(r["distance"]), r["course"]
        )
        base = {
            "event": r["event"],
            "course": r["course"],
            "stroke": r["stroke"],
            "distance": int(r["distance"]),
            "pb_seconds": round(float(r["time_seconds"]), 2),
            "pb_display": r["time_display"],
            "pb_date": r["date"],
        }
        if rec is None:
            flags.append(warn or "Unknown mapping problem.")
            continue
        level = determine_level(float(r["time_seconds"]), rec.standards)
        row = dict(base)
        row.update(
            {
                "standards": rec.standards,
                "achieved": level.achieved,
                "next_target": level.next_target,
                "seconds_to_next": level.seconds_to_next,
                "at_highest": level.at_highest,
            }
        )
        rows.append(row)
    rows.sort(key=lambda x: (x["stroke"], x["distance"], x["course"]))
    return rows, flags
