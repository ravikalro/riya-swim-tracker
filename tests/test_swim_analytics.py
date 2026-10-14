import pandas as pd

from services.swim_analytics import (
    clean_results,
    personal_best_table,
    running_pb_progression,
)

COLS = [
    "Swimmer Name", "Swim Date", "Meet Name", "Distance", "Stroke",
    "Course", "Time", "Result Type", "Notes", "Source URL",
]


def make_row(swimmer="Riya Kalro", date="2025-01-01", meet="Test Meet",
             distance="50", stroke="Freestyle", course="SCY",
             time="35.00", rt="Official"):
    return dict(zip(COLS, [swimmer, date, meet, distance, stroke, course,
                           time, rt, "", ""]))


def build_frame(rows):
    return pd.DataFrame(rows, columns=COLS)


def test_clean_and_pb_marks():
    rows = [
        make_row(date="2025-01-01", time="36.00"),
        make_row(date="2025-02-01", time="35.50"),
        make_row(date="2025-03-01", time="35.80"),  # slower, no PB
        make_row(date="2025-04-01", time="34.90"),
    ]
    df, warnings = clean_results(build_frame(rows))
    assert not warnings
    assert df["is_pb"].tolist() == [True, True, False, True]


def test_courses_are_not_mixed():
    rows = [
        make_row(date="2025-01-01", course="SCY", time="35.00"),
        make_row(date="2025-02-01", course="LCM", time="40.00"),
        make_row(date="2025-03-01", course="LCM", time="39.00"),
    ]
    df, _ = clean_results(build_frame(rows))
    pbs = df[df["is_pb"]]
    # SCY 35.00 (first of course), LCM 40.00 (first of course), LCM 39.00 (improved)
    assert len(pbs) == 3
    # Explicit: check the LCM 40.00 is PB (first of that course), not compared against 35
    lcm_first = df[(df["course"] == "LCM") & (df["time_seconds"] == 40.0)]
    assert bool(lcm_first["is_pb"].iloc[0])
    scy = df[df["course"] == "SCY"]
    assert bool(scy["is_pb"].all())


def test_dq_and_missing_status_excluded():
    rows = [
        make_row(date="2025-01-01", time="36.00", rt="Official"),
        make_row(date="2025-02-01", time="30.00", rt="DQ"),
        make_row(date="2025-03-01", time="29.00", rt=""),  # missing status
        make_row(date="2025-04-01", time="35.00", rt="Official"),
    ]
    df, _ = clean_results(build_frame(rows))
    official_pbs = df[df["is_pb"]]
    assert 30.00 not in official_pbs["time_seconds"].values
    assert 29.00 not in official_pbs["time_seconds"].values
    # 35.00 improves on 36.00 -> PB
    assert 35.00 in official_pbs["time_seconds"].values


def test_malformed_rows_skipped_with_warning():
    rows = [
        make_row(date="2025-01-01", time="bogus"),
        make_row(date="not-a-date", time="35.00"),
        make_row(date="2025-01-01", time="35.00"),
    ]
    df, warnings = clean_results(build_frame(rows))
    assert len(df) == 1
    assert warnings  # warning emitted


def test_empty_sheet():
    df, warnings = clean_results(build_frame([]))
    assert df.empty
    assert not warnings


def test_tied_pb_not_double_counted():
    rows = [
        make_row(date="2025-01-01", time="35.00"),
        make_row(date="2025-02-01", time="35.00"),  # tie: NOT a new PB
    ]
    df, _ = clean_results(build_frame(rows))
    assert int(df["is_pb"].sum()) == 1


def test_running_pb_progression():
    rows = [
        make_row(date="2025-01-01", time="36.00"),
        make_row(date="2025-02-01", time="35.00"),
        make_row(date="2025-03-01", time="35.50"),
    ]
    df, _ = clean_results(build_frame(rows))
    prog = running_pb_progression(df)
    assert list(prog["best_seconds"]) == [36.0, 35.0]


def test_personal_best_table():
    rows = [
        make_row(date="2025-01-01", stroke="Freestyle", distance="50", course="SCY", time="36.00"),
        make_row(date="2025-02-01", stroke="Freestyle", distance="50", course="SCY", time="34.00"),
        make_row(date="2025-01-15", stroke="Backstroke", distance="100", course="LCM", time="1:20.00"),
    ]
    df, _ = clean_results(build_frame(rows))
    table = personal_best_table(df)
    assert len(table) == 2
    free = table[table["Event"] == "50 Freestyle"].iloc[0]
    assert free["Best Time"] == "34.00"
    assert free["Course"] == "SCY"
