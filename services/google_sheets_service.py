"""Service for reading swim results from a public Google Sheet.

Uses the Google Visualization (gviz) CSV export endpoint, which supports
reading a specific tab by name without API keys or OAuth. Requires the
spreadsheet to be shared as "Anyone with the link - Viewer".
"""

from __future__ import annotations

import io
import logging
from typing import List, Tuple

import pandas as pd
import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 20


class SheetReadError(Exception):
    """Raised when the Google Sheet cannot be read."""


def build_csv_export_url(spreadsheet_id: str, sheet_name: str) -> str:
    """Build the gviz CSV export URL for a given tab name."""
    return (
        f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={requests.utils.quote(sheet_name)}"
    )


def fetch_results_frame(
    spreadsheet_id: str,
    sheet_name: str,
    expected_columns: List[str],
) -> Tuple[pd.DataFrame, List[str]]:
    """Fetch the results tab as a DataFrame of raw strings.

    Returns (dataframe, warnings). Raises SheetReadError on failures.
    Never returns demo data.
    """
    url = build_csv_export_url(spreadsheet_id, sheet_name)
    logger.info("Fetching sheet %s tab %s", spreadsheet_id, sheet_name)
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as exc:
        raise SheetReadError(
            f"Network error while reading the spreadsheet: {exc}. "
            "Check your internet connection and try again."
        ) from exc

    if response.status_code == 404:
        raise SheetReadError(
            "Spreadsheet not found. Check the link and make sure the sheet "
            "is shared as 'Anyone with the link - Viewer'."
        )
    if response.status_code in (401, 403):
        raise SheetReadError(
            "Permission denied. Share the spreadsheet with 'Anyone with "
            "the link - Viewer', then press Refresh Data."
        )
    if not response.ok:
        raise SheetReadError(
            f"Google Sheets returned an error (HTTP {response.status_code}). "
            "Check the link and sharing settings."
        )

    try:
        frame = pd.read_csv(io.StringIO(response.text), dtype=str)
    except Exception as exc:  # noqa: BLE001
        raise SheetReadError(
            f"Could not parse the sheet as CSV: {exc}"
        ) from exc

    # Trim whitespace from column headers
    frame.columns = [str(c).strip() for c in frame.columns]

    missing = [c for c in expected_columns if c not in frame.columns]
    if missing:
        raise SheetReadError(
            "The 'Results' tab is missing required column(s): "
            + ", ".join(missing)
            + ". Expected columns: "
            + ", ".join(expected_columns)
        )

    # Replace NaN with empty strings for consistent handling
    frame = frame.fillna("")
    return frame, []
