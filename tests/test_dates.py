from datetime import date

from samad_mcp.dates import api_week_param, persian_weekday, week_start


def test_friday_belongs_to_previous_saturday():
    assert week_start(date(2026, 11, 13)) == date(2026, 11, 7)


def test_saturday_is_its_own_week_start():
    assert week_start(date(2026, 11, 14)) == date(2026, 11, 14)


def test_next_week():
    assert week_start(date(2026, 11, 13), weeks_ahead=1) == date(2026, 11, 14)


def test_persian_weekday_names():
    assert persian_weekday(date(2026, 11, 14)) == "شنبه"
    assert persian_weekday(date(2026, 11, 13)) == "جمعه"


def test_api_week_param_format():
    assert api_week_param(date(2026, 11, 14)) == "2026-11-14 00:00:00"