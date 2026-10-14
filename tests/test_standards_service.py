"""Tests for motivational standards lookup and level determination."""

from __future__ import annotations

import pandas as pd
import pytest

from services import standards_service as svc

STDS = {"B": 50.00, "BB": 45.00, "A": 40.00, "AA": 38.00, "AAA": 36.00, "AAAA": 34.00}


def _records():
    return [
        svc.StandardRecord(
            age_group="10 & under", gender="Girls", distance=50, stroke="FR",
            course="SCY", standards=STDS,
        ),
        svc.StandardRecord(
            age_group="11-12", gender="Girls", distance=50, stroke="FR",
            course="SCY", standards={"B": 48.0, "BB": 44.0, "A": 39.0, "AA": 37.0, "AAA": 35.0, "AAAA": 33.0},
        ),
    ]


class TestDeterminLevel:
    def test_below_b_shows_time_to_b(self):
        r = svc.determine_level(52.5, STDS)
        assert r.achieved is None
        assert r.next_target == "B"
        assert r.seconds_to_next == pytest.approx(2.5)
        assert not r.at_highest

    def test_exact_tie_achieves_level(self):
        r = svc.determine_level(40.00, STDS)
        assert r.achieved == "A"
        assert r.next_target == "AA"
        assert r.seconds_to_next == pytest.approx(2.0)

    def test_just_faster_than_level(self):
        r = svc.determine_level(39.99, STDS)
        assert r.achieved == "A"

    def test_faster_than_aaaa(self):
        r = svc.determine_level(33.50, STDS)
        assert r.achieved == "AAAA"
        assert r.at_highest
        assert r.next_target is None
        assert r.seconds_to_next is None

    def test_exact_aaaa_is_highest(self):
        r = svc.determine_level(34.00, STDS)
        assert r.at_highest

    def test_missing_standard_level_is_skipped(self):
        partial = {"B": 50.0, "A": 40.0}
        r = svc.determine_level(45.0, partial)
        assert r.achieved == "B"
        assert r.next_target == "BB"  # next defined order element
        assert r.seconds_to_next is None  # BB missing => can't compute


class TestLookup:
    def test_maps_normalized_stroke_names(self):
        rec, warn = svc.lookup_standards(_records(), "10 & under", "Girls", "Freestyle", 50, "SCY")
        assert warn is None
        assert rec is not None and rec.stroke == "FR"

    def test_unmappable_stroke_is_flagged(self):
        rec, warn = svc.lookup_standards(_records(), "10 & under", "Girls", "Sidestroke", 50, "SCY")
        assert rec is None and warn

    def test_course_mismatch_never_returns_another_course(self):
        rec, warn = svc.lookup_standards(_records(), "10 & under", "Girls", "Freestyle", 50, "LCM")
        assert rec is None and "No 10 & under" in warn

    def test_distance_mismatch_is_flagged(self):
        rec, warn = svc.lookup_standards(_records(), "10 & under", "Girls", "Freestyle", 5000, "SCY")
        assert rec is None and warn

    def test_age_groups_have_different_standards(self):
        r10, _ = svc.lookup_standards(_records(), "10 & under", "Girls", "Freestyle", 50, "SCY")
        r12, _ = svc.lookup_standards(_records(), "11-12", "Girls", "Freestyle", 50, "SCY")
        assert r10.standards != r12.standards


class TestBuildComparison:
    def _df(self):
        return pd.DataFrame(
            [
                # official swims
                {"event": "50 Freestyle", "stroke": "Freestyle", "distance": 50, "course": "SCY",
                 "time_seconds": 40.0, "time_display": "40.00", "date": pd.Timestamp("2025-05-01"),
                 "is_official": True},
                # slower second swim same event -> PB must win
                {"event": "50 Freestyle", "stroke": "Freestyle", "distance": 50, "course": "SCY",
                 "time_seconds": 42.0, "time_display": "42.00", "date": pd.Timestamp("2025-06-01"),
                 "is_official": True},
                # non-official fastest -> must be excluded
                {"event": "50 Freestyle", "stroke": "Freestyle", "distance": 50, "course": "SCY",
                 "time_seconds": 30.0, "time_display": "30.00", "date": pd.Timestamp("2025-04-01"),
                 "is_official": False},  # e.g. a relay split
                # another event, slower than B
                {"event": "100 Backstroke", "stroke": "Backstroke", "distance": 100, "course": "SCY",
                 "time_seconds": 99.0, "time_display": "1:39.00", "date": pd.Timestamp("2025-05-01"),
                 "is_official": True},
            ]
        )

    def test_excludes_unofficial_and_uses_pb(self):
        rows, flags = svc.build_comparison(self._df(), _records(), "10 & under")
        fr = [r for r in rows if r["stroke"] == "Freestyle"]
        assert len(fr) == 1
        assert fr[0]["pb_seconds"] == 40.0  # not the 30.0 split
        assert fr[0]["achieved"] == "A"

    def test_unmappable_event_is_flagged_not_guessed(self):
        rows, flags = svc.build_comparison(self._df(), _records(), "10 & under")
        assert any("100 Backstroke" in f or "Backstroke" in f for f in flags)
        assert all(r["stroke"] != "Backstroke" for r in rows)

    def test_missing_pb_missing_from_rows(self):
        # Event with no result at all must not appear.
        rows, _ = svc.build_comparison(
            self._df()[self._df()["distance"] == 50], _records(), "10 & under"
        )
        assert {r["distance"] for r in rows} == {50}
