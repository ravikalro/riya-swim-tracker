"""Tests for the standards extraction pipeline and the extracted dataset,
validated against manually checked values from the official PDF
(USA Swimming 2024-2028 Motivational Standards, printed 10/10/2025).
"""

from __future__ import annotations

import json

import pytest

from pipeline.extract_standards import (
    LEVELS,
    PDF_PATH,
    parse_pdf,
    validate,
)
from services import standards_service as svc
from utils.time_utils import format_seconds, parse_time_to_seconds

DATA_PATH = svc.DATA_PATH

# Manually verified against the printed PDF (Girls columns, order B..AAAA).
# Covers both of Riya's age groups and all three courses.
CASES = [
    # --- 10 & under Girls, SCY (PDF page 1) ---
    ("10 & under", 50, "FR", "SCY", ["39.79", "35.99", "32.09", "30.89", "29.59", "28.29"]),
    ("10 & under", 100, "BK", "SCY", ["1:45.79", "1:33.99", "1:22.29", "1:18.39", "1:14.49", "1:10.59"]),
    ("10 & under", 50, "BR", "SCY", ["54.59", "48.69", "42.79", "40.89", "38.89", "36.89"]),
    ("10 & under", 50, "FL", "SCY", ["48.39", "42.69", "36.99", "35.09", "33.19", "31.29"]),
    ("10 & under", 100, "IM", "SCY", ["1:44.29", "1:33.19", "1:22.09", "1:18.39", "1:14.69", "1:10.99"]),
    ("10 & under", 200, "IM", "SCY", ["3:42.09", "3:18.79", "2:55.49", "2:47.69", "2:39.99", "2:32.19"]),
    # --- 10 & under Girls, SCM (PDF page 4 header section) ---
    ("10 & under", 50, "FR", "SCM", ["43.99", "39.79", "35.49", "34.09", "32.69", "31.29"]),
    ("10 & under", 100, "BK", "SCM", ["1:56.89", "1:43.89", "1:30.89", "1:26.59", "1:22.29", "1:17.99"]),
    ("10 & under", 200, "IM", "SCM", ["4:05.39", "3:39.59", "3:13.89", "3:05.29", "2:56.79", "2:48.19"]),
    # --- 10 & under Girls, LCM (PDF page 8 header section) ---
    ("10 & under", 50, "BK", "LCM", ["55.79", "49.69", "43.59", "41.59", "39.49", "37.49"]),
    ("10 & under", 100, "FL", "LCM", ["2:12.79", "1:55.39", "1:37.99", "1:32.19", "1:26.39", "1:20.59"]),
    ("10 & under", 400, "FR", "LCM", ["7:48.59", "7:01.69", "6:14.89", "5:59.29", "5:43.69", "5:27.99"]),
    # --- 11-12 Girls, SCY (PDF page 1) ---
    ("11-12", 50, "FR", "SCY", ["33.99", "31.69", "29.29", "28.09", "26.99", "25.79"]),
    ("11-12", 400, "IM", "SCY", ["6:31.69", "6:03.69", "5:35.79", "5:21.79", "5:07.79", "4:53.79"]),
    ("11-12", 1000, "FR", "SCY", ["15:02.69", "13:58.19", "12:53.79", "12:21.49", "11:49.29", "11:16.99"]),
    # --- 11-12 Girls, SCM (PDF page 5) ---
    ("11-12", 50, "FR", "SCM", ["37.59", "34.99", "32.39", "31.09", "29.79", "28.49"]),
    ("11-12", 800, "FR", "SCM", ["13:09.89", "12:13.49", "11:16.99", "10:48.79", "10:20.59", "9:52.39"]),
    # --- 11-12 Girls, LCM (PDF page 9) ---
    ("11-12", 50, "FR", "LCM", ["38.49", "35.89", "33.19", "31.89", "30.49", "29.19"]),
    ("11-12", 800, "FR", "LCM", ["13:41.59", "12:42.89", "11:44.19", "11:14.89", "10:45.49", "10:16.19"]),
]


@pytest.fixture(scope="module")
def dataset():
    assert DATA_PATH.exists(), "Run pipeline/extract_standards.py first"
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def girls_index(dataset):
    return {
        (r["age_group"], r["distance"], r["stroke"], r["course"]): r["standards"]
        for r in dataset["records"]
        if r["gender"] == "Girls"
    }


class TestMetadata:
    def test_metadata_present(self, dataset):
        meta = dataset["metadata"]
        assert meta["title"] == "USA Swimming 2024-2028 Motivational Standards"
        assert "websitedevsa.blob.core.windows.net" in meta["source_url"]
        assert meta["levels"] == LEVELS
        assert meta["extraction_date"]

    def test_pdf_versioned_with_repo(self):
        assert PDF_PATH.exists()


class TestParsing:
    def test_time_token_parsing_examples(self):
        assert parse_time_to_seconds("39.79") == pytest.approx(39.79)
        assert parse_time_to_seconds("1:30.79") == pytest.approx(90.79)
        assert parse_time_to_seconds("25:07.39") == pytest.approx(1507.39)
        assert parse_time_to_seconds("garbage") is None
        assert parse_time_to_seconds("") is None

    def test_formatter(self):
        assert format_seconds(39.79) == "39.79"
        assert format_seconds(68.57) == "1:08.57"

    def test_extraction_is_reproducible_and_clean(self):
        if not PDF_PATH.exists():
            pytest.skip("PDF not downloaded")
        records, errors = parse_pdf(PDF_PATH)
        assert errors == []
        assert validate(records) == []
        assert len(records) > 400  # no extraction errors, nothing dropped


class TestDataset:
    def test_all_age_groups_and_courses_present(self, dataset):
        for ag in ["10 & under", "11-12", "13-14", "15-16", "17-18"]:
            for course in ["SCY", "SCM", "LCM"]:
                assert any(
                    r["age_group"] == ag and r["course"] == course
                    for r in dataset["records"]
                ), f"missing {ag} {course}"

    def test_relays_excluded(self, dataset):
        assert all(r["stroke"] not in ("FR-R", "MED-R") for r in dataset["records"])

    def test_standards_strictly_faster_with_higher_level(self, dataset):
        for r in dataset["records"]:
            vals = [r["standards"][lv] for lv in LEVELS]
            assert all(a > b for a, b in zip(vals, vals[1:])), (
                f"non-monotonic: {r['age_group']} {r['gender']} "
                f"{r['distance']} {r['stroke']} {r['course']}"
            )

    def test_no_missing_or_zero_standards(self, dataset):
        for r in dataset["records"]:
            assert set(r["standards"]) == set(LEVELS)
            assert all(v > 0 for v in r["standards"].values())


@pytest.mark.parametrize(
    "age_group,distance,stroke,course,expected", CASES,
    ids=[f"{a}-{d}{s}-{c}" for a, d, s, c, _ in CASES],
)
def test_manually_checked_standard(age_group, distance, stroke, course, expected, girls_index):
    row = girls_index.get((age_group, distance, stroke, course))
    assert row is not None, f"missing {age_group} {distance} {stroke} {course}"
    for lv, exp in zip(LEVELS, expected):
        assert row[lv] == pytest.approx(parse_time_to_seconds(exp), abs=0.001), (
            f"{age_group} {distance} {stroke} {course} {lv}"
        )
