"""Dashboard summary data for the local Web console."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from gitplus.config import GitPlusConfig
from gitplus.exceptions import GitCommandError
from gitplus.git.command_runner import GitCommandRunner
from gitplus.models.notification import NotificationRecord
from gitplus.models.weekly import WeeklyReport
from gitplus.models.worklog import WorklogFilters
from gitplus.storage.database import Database
from gitplus.storage.migrations.manager import CURRENT_SCHEMA_VERSION, MigrationManager
from gitplus.storage.unit_of_work import UnitOfWork
from gitplus.web.services.repository_context_service import RepositoryContextService
from gitplus.web.services.repository_web_service import (
    RepositoryWebError,
    RepositoryWebService,
)
from gitplus.weekly.date_range import WeeklyDateRangeResolver


class DashboardWebService:
    """Build non-mutating dashboard metrics."""

    def __init__(
        self,
        repository_service: RepositoryWebService,
        repository_context: RepositoryContextService,
        database: Database,
        config: GitPlusConfig,
    ) -> None:
        self.repository_service = repository_service
        self.repository_context = repository_context
        self.database = database
        self.config = config

    def summary(self) -> dict[str, object]:
        warnings: list[str] = []
        try:
            status = self.repository_service.status()
        except RepositoryWebError as exc:
            status = {
                "repository": {
                    "name": self.repository_service.root.name,
                    "root": str(self.repository_service.root),
                    "branch": None,
                    "is_clean": False,
                    "identity_configured": False,
                },
                "summary": {
                    "staged": 0,
                    "unstaged": 0,
                    "untracked": 0,
                    "conflicted": 0,
                },
                "revision": "",
            }
            warnings.append(str(exc))
        week_range = WeeklyDateRangeResolver(self.config.weekly).current_week()
        repository = None
        try:
            repository = self.repository_context.ensure_record()
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"仓库记录不可用：{str(exc)[:80]}")
        database_status = self._database_status()
        latest_weekly = None
        latest_notification = None
        worklog_count = 0
        if repository:
            try:
                with UnitOfWork(self.database) as uow:
                    reports = uow.weekly_reports.list(
                        repository_id=repository.id,
                        limit=1,
                    )
                    latest_weekly = reports[0] if reports else None
                    notifications = uow.notifications.list(
                        channel="feishu",
                        limit=1,
                    )
                    latest_notification = notifications[0] if notifications else None
                    worklog_count = uow.worklogs.count(
                        WorklogFilters(
                            repository_id=repository.id,
                            date_from=week_range.date_from,
                            date_to=week_range.date_to,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"数据库统计不可用：{str(exc)[:80]}")
        git_commit_count = self._weekly_git_commit_count(week_range.datetime_from)
        ai_ready = self.config.ai.provider == "mock" or bool(self.config.ai.api_key)
        feishu_ready = self.config.feishu.enabled and (
            bool(self.config.feishu.webhook)
            if self.config.feishu.mode == "webhook"
            else bool(
                self.config.feishu.app_id
                and self.config.feishu.app_secret
                and self.config.feishu.receive_id
            )
        )
        repository_payload = status["repository"]
        if (
            isinstance(repository_payload, dict)
            and not repository_payload.get("identity_configured")
        ):
            warnings.append("Git 用户身份未完整配置。")
        if not ai_ready:
            warnings.append("AI 凭证未配置，远程模型不可用。")
        if self.config.feishu.enabled and not feishu_ready:
            warnings.append("飞书配置未完整。")
        return {
            "repository": status["repository"],
            "git_summary": status["summary"],
            "repository_revision": status["revision"],
            "week": {
                "date_from": week_range.date_from.isoformat(),
                "date_to": week_range.date_to.isoformat(),
                "timezone": week_range.timezone,
            },
            "counts": {
                "week_commits": git_commit_count,
                "week_worklogs": worklog_count,
            },
            "weekly_report": self._weekly_payload(latest_weekly),
            "notification": self._notification_payload(latest_notification),
            "ai": {
                "provider": self.config.ai.provider,
                "model": self.config.ai.model,
                "configured": ai_ready,
            },
            "feishu": {
                "enabled": self.config.feishu.enabled,
                "mode": self.config.feishu.mode,
                "configured": feishu_ready,
            },
            "database": database_status,
            "warnings": sorted(set(warnings)),
        }

    def _weekly_git_commit_count(self, since: datetime) -> int:
        try:
            result = GitCommandRunner(
                self.repository_service.root, timeout_seconds=2
            ).run(
                [
                    "log",
                    "--since",
                    since.isoformat(),
                    "--format=%H",
                    "--",
                ],
                check=False,
            )
        except GitCommandError:
            return 0
        if result.return_code != 0:
            return 0
        return len([line for line in result.stdout.splitlines() if line.strip()])

    def _database_status(self) -> dict[str, object]:
        try:
            self.database.initialize()
            version = MigrationManager(self.database.engine).current_version()
            writable = self.database.database_path.parent.exists() and self._writable(
                self.database.database_path.parent
            )
            return {
                "ok": version == CURRENT_SCHEMA_VERSION and writable,
                "path": str(self.database.database_path),
                "schema_version": version,
                "expected_schema_version": CURRENT_SCHEMA_VERSION,
                "writable": writable,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "path": str(self.database.database_path),
                "schema_version": None,
                "expected_schema_version": CURRENT_SCHEMA_VERSION,
                "writable": False,
                "error": str(exc)[:160],
            }

    def _writable(self, path: Path) -> bool:
        probe = path / ".gitplus-write-test"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return True
        except OSError:
            return False

    def _weekly_payload(self, report: WeeklyReport | None) -> dict[str, object] | None:
        if report is None:
            return None
        return {
            "id": report.id,
            "title": report.title,
            "status": report.status,
            "version": report.version,
            "date_from": report.date_range.date_from.isoformat(),
            "date_to": report.date_range.date_to.isoformat(),
        }

    def _notification_payload(
        self, record: NotificationRecord | None
    ) -> dict[str, object] | None:
        if record is None:
            return None
        return {
            "id": record.id,
            "report_id": record.report_id,
            "status": record.status,
            "provider_mode": record.provider_mode,
            "message_type": record.message_type,
            "created_at": record.created_at.isoformat(),
            "sent_at": record.sent_at.isoformat() if record.sent_at else None,
        }
