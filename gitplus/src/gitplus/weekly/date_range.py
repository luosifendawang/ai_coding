"""Weekly report date range resolution."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from gitplus.config import WeeklyConfig
from gitplus.exceptions import WeeklyDateRangeError
from gitplus.models.weekly import WeeklyDateRange


class WeeklyDateRangeResolver:
    """Resolve current, last, and custom weekly date ranges."""

    def __init__(self, config: WeeklyConfig) -> None:
        self.config = config
        self.timezone = ZoneInfo(config.timezone)

    def current_week(self, *, now: datetime | None = None) -> WeeklyDateRange:
        local_now = self._local_now(now)
        start = self._week_start_for(local_now.date())
        return self._build(
            start,
            local_now.date(),
            datetime.combine(start, time.min, self.timezone),
            local_now,
            "本周",
        )

    def last_week(self, *, now: datetime | None = None) -> WeeklyDateRange:
        local_now = self._local_now(now)
        current_start = self._week_start_for(local_now.date())
        start = current_start - timedelta(days=7)
        end = current_start - timedelta(days=1)
        return self._build(
            start,
            end,
            datetime.combine(start, time.min, self.timezone),
            datetime.combine(end, time.max, self.timezone),
            "上周",
        )

    def custom(self, date_from: date, date_to: date) -> WeeklyDateRange:
        if date_to < date_from:
            raise WeeklyDateRangeError("周报结束日期不能早于开始日期。")
        return self._build(
            date_from,
            date_to,
            datetime.combine(date_from, time.min, self.timezone),
            datetime.combine(date_to, time.max, self.timezone),
            f"{date_from.isoformat()} 至 {date_to.isoformat()}",
        )

    def _local_now(self, now: datetime | None) -> datetime:
        value = now or datetime.now(self.timezone)
        if value.tzinfo is None:
            return value.replace(tzinfo=self.timezone)
        return value.astimezone(self.timezone)

    def _week_start_for(self, current: date) -> date:
        weekday = current.weekday()
        offset = weekday if self.config.week_start == "monday" else (weekday + 1) % 7
        return current - timedelta(days=offset)

    def _build(
        self,
        date_from: date,
        date_to: date,
        datetime_from: datetime,
        datetime_to: datetime,
        label: str,
    ) -> WeeklyDateRange:
        return WeeklyDateRange(
            date_from=date_from,
            date_to=date_to,
            datetime_from=datetime_from,
            datetime_to=datetime_to,
            timezone=self.config.timezone,
            label=label,
        )
