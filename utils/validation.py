"""Validation and normalization helpers."""

from __future__ import annotations

import re
from typing import Optional

VALID_COURSES = ("SCY", "SCM", "LCM")

_STROKE_MAP = {
    "freestyle": "Freestyle",
    "free": "Freestyle",
    "fr": "Freestyle",
    "backstroke": "Backstroke",
    "back": "Backstroke",
    "bk": "Backstroke",
    "breaststroke": "Breaststroke",
    "breast": "Breaststroke",
    "br": "Breaststroke",
    "butterfly": "Butterfly",
    "fly": "Butterfly",
    "fl": "Butterfly",
    "butterfly/im": "Butterfly",
    "im": "Individual Medley",
    "individual medley": "Individual Medley",
    "medley": "Individual Medley",
}


def extract_spreadsheet_id(url: str) -> Optional[str]:
    """Extract the spreadsheet ID from a Google Sheets URL.

    Handles ordinary sharing URLs like:
      https://docs.google.com/spreadsheets/d/<ID>/edit?usp=sharing
    Also accepts a bare spreadsheet ID.
    """
    if not url:
        return None
    text = url.strip()
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", text)
    if m:
        return m.group(1)
    # Bare ID fallback
    if re.fullmatch(r"[a-zA-Z0-9-_]{20,}", text):
        return text
    return None


def normalize_stroke(value: object) -> Optional[str]:
    """Normalize a stroke name to a canonical form."""
    if value is None:
        return None
    key = str(value).strip().lower()
    if not key:
        return None
    return _STROKE_MAP.get(key, str(value).strip().title())


def normalize_course(value: object) -> Optional[str]:
    """Normalize a course label to SCY, SCM, or LCM."""
    if value is None:
        return None
    text = str(value).strip().upper()
    aliases = {
        "SCY": "SCY", "SHORT COURSE YARDS": "SCY", "25Y": "SCY", "YARDS": "SCY",
        "SCM": "SCM", "SHORT COURSE METERS": "SCM", "25M": "SCM",
        "LCM": "LCM", "LONG COURSE METERS": "LCM", "50M": "LCM", "LONG COURSE": "LCM",
    }
    if "LONG" in text and "METER" in text:
        return "LCM"
    return aliases.get(text)


def normalize_result_type(value: object) -> str:
    """Normalize result type to a lowercase, trimmed string."""
    if value is None:
        return ""
    return str(value).strip().lower()
