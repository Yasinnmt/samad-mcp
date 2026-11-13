from __future__ import annotations

from datetime import date, timedelta

_SATURDAY = 5
_PERSIAN_WEEKDAYS = (
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
    "شنبه",
    "یکشنبه",
)


def week_start(today: date, weeks_ahead: int = 0) -> date:
    days_since_saturday = (today.weekday() - _SATURDAY) % 7
    return today - timedelta(days=days_since_saturday) + timedelta(weeks=weeks_ahead)


def persian_weekday(day: date) -> str:
    return _PERSIAN_WEEKDAYS[day.weekday()]


def api_week_param(start: date) -> str:
    # The backend parses "yyyy-MM-dd HH:mm:ss"; a literal "+" fails with HTTP 400.
    return f"{start.isoformat()} 00:00:00"