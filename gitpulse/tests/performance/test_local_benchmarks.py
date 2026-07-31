import time as time_module
from datetime import date, datetime, time, timezone
from pathlib import Path

from gitpulse.config import FeishuConfig
from gitpulse.models.weekly import WeeklyDateRange, WeeklyReport
from gitpulse.notifications.renderer import FeishuNotificationRenderer
from gitpulse.storage.database import Database
from gitpulse.storage.migrations.manager import MigrationManager


def test_database_initialize_under_basic_threshold(tmp_path: Path) -> None:
    start = time_module.perf_counter()
    database = Database(tmp_path / "perf.db")
    database.initialize()
    version = MigrationManager(database.engine).current_version()
    elapsed = time_module.perf_counter() - start

    assert version >= 1
    assert elapsed < 5
    database.dispose()


def test_notification_render_under_basic_threshold() -> None:
    now = datetime.now(timezone.utc)
    report = WeeklyReport(
        id="weekly_perf",
        title="性能测试周报",
        date_range=WeeklyDateRange(
            date_from=date(2026, 7, 27),
            date_to=date(2026, 8, 2),
            datetime_from=datetime.combine(date(2026, 7, 27), time.min, timezone.utc),
            datetime_to=datetime.combine(date(2026, 8, 2), time.max, timezone.utc),
            timezone="UTC",
            label="本周",
        ),
        source_coverage=1,
        status="confirmed",
        content_markdown="# 性能测试周报",
        generator="rule_based",
        created_at=now,
        updated_at=now,
        confirmed_at=now,
    )

    start = time_module.perf_counter()
    payload = FeishuNotificationRenderer().render(report, FeishuConfig())
    elapsed = time_module.perf_counter() - start

    assert payload.byte_size > 0
    assert elapsed < 1
