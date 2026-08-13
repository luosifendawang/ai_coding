from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from gitplus.config import WeeklyConfig
from gitplus.exceptions import WeeklyDateRangeError
from gitplus.weekly.date_range import WeeklyDateRangeResolver


def test_current_week_monday_start() -> None:
    resolver = WeeklyDateRangeResolver(WeeklyConfig(week_start="monday", timezone="Asia/Shanghai"))
    now = datetime(2026, 7, 28, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    result = resolver.current_week(now=now)

    assert result.date_from == date(2026, 7, 27)
    assert result.date_to == date(2026, 7, 28)
    assert result.datetime_from.tzinfo is not None


def test_current_week_sunday_start() -> None:
    resolver = WeeklyDateRangeResolver(WeeklyConfig(week_start="sunday"))
    now = datetime(2026, 7, 28, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    assert resolver.current_week(now=now).date_from == date(2026, 7, 26)


def test_last_week_cross_month() -> None:
    resolver = WeeklyDateRangeResolver(WeeklyConfig())
    now = datetime(2026, 8, 3, 9, 0, tzinfo=ZoneInfo("Asia/Shanghai"))

    result = resolver.last_week(now=now)

    assert result.date_from == date(2026, 7, 27)
    assert result.date_to == date(2026, 8, 2)


def test_custom_range_and_invalid_range() -> None:
    resolver = WeeklyDateRangeResolver(WeeklyConfig())

    result = resolver.custom(date(2026, 12, 30), date(2027, 1, 2))

    assert result.date_from == date(2026, 12, 30)
    assert result.date_to == date(2027, 1, 2)
    with pytest.raises(WeeklyDateRangeError):
        resolver.custom(date(2026, 1, 2), date(2026, 1, 1))

