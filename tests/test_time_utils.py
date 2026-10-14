import math

from utils.time_utils import format_seconds, parse_time_to_seconds


def test_plain_seconds():
    assert parse_time_to_seconds("31.42") == 31.42
    assert parse_time_to_seconds("31") == 31.0


def test_minute_format():
    assert math.isclose(parse_time_to_seconds("1:08.57"), 68.57)
    assert math.isclose(parse_time_to_seconds("2:03.5"), 123.5)


def test_hour_format():
    assert math.isclose(parse_time_to_seconds("1:02:03.45"), 3723.45)


def test_whitespace_and_invalid():
    assert parse_time_to_seconds("  24.90  ") == 24.90
    assert parse_time_to_seconds("") is None
    assert parse_time_to_seconds(None) is None
    assert parse_time_to_seconds("abc") is None
    assert parse_time_to_seconds("1:99.5") is None
    assert parse_time_to_seconds("DQ") is None


def test_fraction_interpretation():
    # ".5" = half a second, not 5 hundredths
    assert math.isclose(parse_time_to_seconds("30.5"), 30.5)


def test_format_seconds():
    assert format_seconds(31.42) == "31.42"
    assert format_seconds(68.57) == "1:08.57"
    assert format_seconds(None) == ""
    assert format_seconds(-5) == ""
