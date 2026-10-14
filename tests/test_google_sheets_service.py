from unittest.mock import patch

import pytest
import requests

from services.google_sheets_service import (
    SheetReadError,
    build_csv_export_url,
    fetch_results_frame,
)
from utils.validation import extract_spreadsheet_id, normalize_course, normalize_stroke

EXPECTED = [
    "Swimmer Name", "Swim Date", "Meet Name", "Distance", "Stroke",
    "Course", "Time", "Result Type", "Notes", "Source URL",
]

CSV_OK = (
    "Swimmer Name,Swim Date,Meet Name,Distance,Stroke,Course,Time,Result Type,Notes,Source URL\n"
    "Riya Kalro,2025-01-01,Test Meet,50,Freestyle,SCY,35.00,Official,,\n"
)


class FakeResponse:
    def __init__(self, text="", status=200):
        self.text = text
        self.status_code = status

    @property
    def ok(self):
        return 200 <= self.status_code < 300


def test_extract_spreadsheet_id():
    sid = "1AbC_def-XyZ1234567890"
    assert extract_spreadsheet_id(
        f"https://docs.google.com/spreadsheets/d/{sid}/edit?usp=sharing"
    ) == sid
    assert extract_spreadsheet_id(f"https://docs.google.com/spreadsheets/d/{sid}") == sid
    assert extract_spreadsheet_id(sid) == sid
    assert extract_spreadsheet_id("https://example.com/nope") is None
    assert extract_spreadsheet_id("") is None


def test_build_url():
    url = build_csv_export_url("ABC123", "Results")
    assert "tqx=out:csv" in url
    assert "sheet=Results" in url
    assert "ABC123" in url


def test_fetch_success():
    with patch("services.google_sheets_service.requests.get",
               return_value=FakeResponse(CSV_OK)):
        df, _ = fetch_results_frame("ABC", "Results", EXPECTED)
    assert len(df) == 1
    assert df.iloc[0]["Swimmer Name"] == "Riya Kalro"


def test_fetch_permission_denied():
    with patch("services.google_sheets_service.requests.get",
               return_value=FakeResponse(status=403)):
        with pytest.raises(SheetReadError, match="Permission"):
            fetch_results_frame("ABC", "Results", EXPECTED)


def test_fetch_not_found():
    with patch("services.google_sheets_service.requests.get",
               return_value=FakeResponse(status=404)):
        with pytest.raises(SheetReadError, match="not found"):
            fetch_results_frame("ABC", "Results", EXPECTED)


def test_fetch_network_error():
    with patch("services.google_sheets_service.requests.get",
               side_effect=requests.exceptions.ConnectionError("down")):
        with pytest.raises(SheetReadError, match="Network"):
            fetch_results_frame("ABC", "Results", EXPECTED)


def test_fetch_missing_columns():
    with patch("services.google_sheets_service.requests.get",
               return_value=FakeResponse("A,B\n1,2\n")):
        with pytest.raises(SheetReadError, match="missing required column"):
            fetch_results_frame("ABC", "Results", EXPECTED)


def test_normalize():
    assert normalize_course("scy") == "SCY"
    assert normalize_course("Long Course Meters") == "LCM"
    assert normalize_course("banana") is None
    assert normalize_stroke("free") == "Freestyle"
    assert normalize_stroke("IM") == "Individual Medley"
