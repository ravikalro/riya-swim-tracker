"""Swim time parsing and formatting utilities."""

from __future__ import annotations

import re
from typing import Optional

# Matches "SS.hh" e.g. "31.42" or "31"
_SECONDS_ONLY = re.compile(r"^\s*(\d{1,3})(?:\.(\d{1,3}))?\s*$")
# Matches "M:SS.hh" e.g. "1:08.57" or "12:34.5"
_MIN_SEC = re.compile(r"^\s*(\d{1,3}):([0-5]?\d)(?:\.(\d{1,3}))\s*$")
# Matches "H:MM:SS.hh"
_HR_MIN_SEC = re.compile(r"^\s*(\d{1,2}):([0-5]?\d):([0-5]?\d)(?:\.(\d{1,3}))\s*$")


def parse_time_to_seconds(value: object) -> Optional[float]:
    """Parse a swim time string into seconds.

    Supported formats:
      - "31.42"      -> 31.42 seconds
      - "31"         -> 31.0 seconds
      - "1:08.57"    -> 68.57 seconds
      - "1:02:03.45" -> hours:minutes:seconds

    Returns None for malformed or empty values (never treats them as zero).
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    def frac_to_seconds(frac: str) -> float:
        # ".5" means half a second, ".42" means 42 hundredths.
        # Interpret as decimal fraction.
        return float("0." + frac)

    m = _HR_MIN_SEC.match(text)
    if m:
        h, mins, secs, frac = m.groups()
        total = int(h) * 3600 + int(mins) * 60 + int(secs)
        if frac:
            total += frac_to_seconds(frac)
        return float(total)

    m = _MIN_SEC.match(text)
    if m:
        mins, secs, frac = m.groups()
        if int(secs) >= 60:
            return None
        total = int(mins) * 60 + int(secs)
        if frac:
            total += frac_to_seconds(frac)
        return float(total)

    m = _SECONDS_ONLY.match(text)
    if m:
        secs, frac = m.groups()
        total = int(secs)
        if frac:
            total += frac_to_seconds(frac)
        return float(total)

    return None


def format_seconds(seconds: Optional[float]) -> str:
    """Format seconds as a swim time string, e.g. 68.57 -> "1:08.57"."""
    if seconds is None:
        return ""
    try:
        total = float(seconds)
    except (TypeError, ValueError):
        return ""
    if total != total:  # NaN
        return ""
    if total < 0:
        return ""
    mins = int(total // 60)
    rem = total - mins * 60
    if mins > 0:
        return f"{mins}:{rem:05.2f}"
    return f"{rem:.2f}"
