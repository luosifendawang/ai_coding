"""Repository pattern implementations."""

from __future__ import annotations

import builtins
from datetime import date, datetime
from pathlib import Path
from typing import Any, ClassVar, cast
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from gitplus.exceptions import (
    DuplicateRecordError,
    RecordNotFoundError,
    RepositoryOperationError,
)
from gitplus.models.storage import CommitRecord, RepositoryRecord, RiskRecord
from gitplus.models.worklog import (
    Worklog,
    WorklogFilters,
    WorklogSource,
    WorklogType,
    WorklogUpdate,
)
from gitplus.storage.orm_models import (
    CommitRecordORM,
    RepositoryORM,
    RiskORM,
    WorklogORM,
    utc_now,
)
from gitplus.storage.serializers import JsonSerializer


def sanitize_remote_url(remote_url: str | None) -> str | None:
    if not remote_url:
        return None
    parts = urlsplit(remote_url)
    if parts.username or parts.password:
        host = parts.hostname or ""
        if parts.port:
            host = f"{host}:{parts.port}"
        return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
    return remote_url


class RepositoryRepository:
    """Persist Git repository records."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, repository_id: str) -> RepositoryRecord | None:
        orm = self.session.get(RepositoryORM, repository_id)
        return self._to_model(orm) if orm else None

    def get_by_root_path(self, root_path: str) -> RepositoryRecord | None:
        normalized = str(Path(root_path).expanduser().resolve())
        orm = self.session.execute(select(RepositoryORM).where(RepositoryORM.root_path == normalized)).scalar_one_or_none()
        return self._to_model(orm) if orm else None

    def upsert(self, repository: RepositoryRecord) -> RepositoryRecord:
        normalized = str(Path(repository.root_path).expanduser().resolve())
        existing = self.session.execute(select(RepositoryORM).where(RepositoryORM.root_path == normalized)).scalar_one_or_none()
        now = utc_now()
        if existing:
            existing.name = repository.name
            existing.remote_url = sanitize_remote_url(repository.remote_url)
            existing.updated_at = now
            existing.last_seen_at = now
            self.session.flush()
            return self._to_model(existing)
        orm = RepositoryORM(
            id=repository.id,
            name=repository.name,
            root_path=normalized,
            remote_url=sanitize_remote_url(repository.remote_url),
            created_at=repository.created_at,
            updated_at=repository.updated_at,
            last_seen_at=repository.last_seen_at or now,
        )
        self.session.add(orm)
        self.session.flush()
        return self._to_model(orm)

    def list_all(self) -> list[RepositoryRecord]:
        return [self._to_model(item) for item in self.session.execute(select(RepositoryORM)).scalars()]

    def _to_model(self, orm: RepositoryORM) -> RepositoryRecord:
        return RepositoryRecord(
            id=orm.id,
            name=orm.name,
            root_path=orm.root_path,
            remote_url=orm.remote_url,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            last_seen_at=orm.last_seen_at,
        )


class CommitRecordRepository:
    """Persist generated commit records."""

    def __init__(self, session: Session, serializer: JsonSerializer | None = None) -> None:
        self.session = session
        self.serializer = serializer or JsonSerializer()

    def create(self, record: CommitRecord) -> CommitRecord:
        orm = CommitRecordORM(
            id=record.id,
            repository_id=record.repository_id,
            commit_hash=record.commit_hash,
            branch=record.branch,
            commit_type=record.commit_type,
            scope=record.scope,
            subject=record.subject,
            body=self.serializer.dumps(record.body),
            summary=record.summary,
            files_json=self.serializer.dumps(record.files),
            insertions=record.insertions,
            deletions=record.deletions,
            confidence=record.confidence,
            confirmed_by_user=record.confirmed_by_user,
            source_type=record.source_type,
            generation_provider=record.provider_name,
            generation_model=record.model_name,
            selected_candidate=record.selected_candidate,
            should_split=record.should_split,
            split_confidence=record.split_confidence,
            verification_json=self.serializer.dumps(record.verification),
            security_summary_json=self.serializer.dumps(record.security_summary),
            content_hash=record.content_hash,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        self.session.add(orm)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DuplicateRecordError("Commit 记录重复。") from exc
        return self._to_model(orm)

    def get_by_id(self, record_id: str) -> CommitRecord | None:
        orm = self.session.get(CommitRecordORM, record_id)
        return self._to_model(orm) if orm else None

    def get_by_commit_hash(self, repository_id: str, commit_hash: str) -> CommitRecord | None:
        orm = self.session.execute(
            select(CommitRecordORM).where(
                CommitRecordORM.repository_id == repository_id,
                CommitRecordORM.commit_hash == commit_hash,
            )
        ).scalar_one_or_none()
        return self._to_model(orm) if orm else None

    def update_commit_hash(self, record_id: str, commit_hash: str) -> CommitRecord:
        orm = self.session.get(CommitRecordORM, record_id)
        if not orm:
            raise RecordNotFoundError(f"未找到 Commit 记录：{record_id}")
        orm.commit_hash = commit_hash
        orm.updated_at = utc_now()
        self.session.flush()
        return self._to_model(orm)

    def list_by_repository(
        self,
        repository_id: str,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        confirmed_only: bool = False,
        limit: int = 100,
        offset: int = 0,
        commit_type: str | None = None,
        confidence: str | None = None,
        search: str | None = None,
    ) -> list[CommitRecord]:
        conditions = [CommitRecordORM.repository_id == repository_id]
        if date_from:
            conditions.append(CommitRecordORM.created_at >= date_from)
        if date_to:
            conditions.append(CommitRecordORM.created_at <= date_to)
        if confirmed_only:
            conditions.append(CommitRecordORM.confirmed_by_user.is_(True))
        if commit_type:
            conditions.append(CommitRecordORM.commit_type == commit_type)
        if confidence:
            conditions.append(CommitRecordORM.confidence == confidence)
        if search:
            like = f"%{search}%"
            conditions.append(or_(CommitRecordORM.subject.like(like), CommitRecordORM.summary.like(like)))
        query = (
            select(CommitRecordORM)
            .where(and_(*conditions))
            .order_by(CommitRecordORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_model(item) for item in self.session.execute(query).scalars()]

    def delete(self, record_id: str) -> bool:
        orm = self.session.get(CommitRecordORM, record_id)
        if not orm:
            return False
        self.session.delete(orm)
        self.session.flush()
        return True

    def _to_model(self, orm: CommitRecordORM) -> CommitRecord:
        return CommitRecord(
            id=orm.id,
            repository_id=orm.repository_id,
            commit_hash=orm.commit_hash,
            branch=orm.branch,
            commit_type=orm.commit_type,
            scope=orm.scope,
            subject=orm.subject,
            body=self.serializer.loads(orm.body, []),
            summary=orm.summary,
            files=self.serializer.loads(orm.files_json, []),
            insertions=orm.insertions,
            deletions=orm.deletions,
            confidence=orm.confidence,
            confirmed_by_user=orm.confirmed_by_user,
            source_type=orm.source_type,
            selected_candidate=orm.selected_candidate,
            should_split=orm.should_split,
            split_confidence=orm.split_confidence,
            verification=self.serializer.loads(orm.verification_json, []),
            provider_name=orm.generation_provider,
            model_name=orm.generation_model,
            content_hash=orm.content_hash,
            security_summary=self.serializer.loads(orm.security_summary_json, {}),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class RiskRepository:
    """Persist risk findings without raw sensitive values."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_many(self, risks: list[RiskRecord]) -> list[RiskRecord]:
        objects = [RiskORM(**risk.model_dump()) for risk in risks]
        self.session.add_all(objects)
        self.session.flush()
        return [self._to_model(item) for item in objects]

    def list_by_record(self, record_id: str, record_type: str) -> list[RiskRecord]:
        rows = self.session.execute(
            select(RiskORM).where(RiskORM.record_id == record_id, RiskORM.record_type == record_type)
        ).scalars()
        return [self._to_model(item) for item in rows]

    def mark_resolved(self, risk_id: str) -> RiskRecord:
        orm = self.session.get(RiskORM, risk_id)
        if not orm:
            raise RecordNotFoundError(f"未找到风险记录：{risk_id}")
        orm.resolved = True
        orm.resolved_at = utc_now()
        self.session.flush()
        return self._to_model(orm)

    def _to_model(self, orm: RiskORM) -> RiskRecord:
        return RiskRecord(
            id=orm.id,
            record_id=orm.record_id,
            record_type=orm.record_type,
            rule_id=orm.rule_id,
            risk_level=orm.risk_level,
            risk_type=orm.risk_type,
            file_path=orm.file_path,
            line_number=orm.line_number,
            description=orm.description,
            masked_value=orm.masked_value,
            suggestion=orm.suggestion,
            blocks_remote_model=orm.blocks_remote_model,
            resolved=orm.resolved,
            resolved_at=orm.resolved_at,
            created_at=orm.created_at,
        )


class WorklogRepository:
    """Persist manual worklog records."""

    def __init__(self, session: Session, serializer: JsonSerializer | None = None) -> None:
        self.session = session
        self.serializer = serializer or JsonSerializer()

    def create(self, worklog: Worklog) -> Worklog:
        orm = WorklogORM(
            id=worklog.id,
            repository_id=worklog.repository_id,
            work_date=worklog.work_date,
            occurred_at=worklog.occurred_at,
            work_type=worklog.work_type,
            title=worklog.title,
            description=worklog.description,
            result=worklog.result,
            duration_minutes=worklog.duration_minutes,
            tags_json=self.serializer.dumps(worklog.tags),
            related_commit_hash=worklog.related_commit_hash,
            source=worklog.source,
            confirmed_by_user=worklog.confirmed_by_user,
            created_at=worklog.created_at,
            updated_at=worklog.updated_at,
        )
        self.session.add(orm)
        self.session.flush()
        return self._to_model(orm)

    def get_by_id(self, worklog_id: str) -> Worklog | None:
        orm = self.session.get(WorklogORM, worklog_id)
        return self._to_model(orm) if orm else None

    def update(self, worklog_id: str, changes: WorklogUpdate) -> Worklog:
        orm = self.session.get(WorklogORM, worklog_id)
        if not orm:
            raise RecordNotFoundError(f"未找到 Worklog：{worklog_id}")
        fields = changes.model_fields_set
        for field in fields:
            value = getattr(changes, field)
            if field == "tags":
                orm.tags_json = self.serializer.dumps(value or [])
            else:
                setattr(orm, field, value)
        orm.updated_at = utc_now()
        self.session.flush()
        return self._to_model(orm)

    def delete(self, worklog_id: str) -> bool:
        orm = self.session.get(WorklogORM, worklog_id)
        if not orm:
            return False
        self.session.delete(orm)
        self.session.flush()
        return True

    def list(self, filters: WorklogFilters) -> list[Worklog]:
        conditions = self._conditions(filters)
        query = select(WorklogORM)
        if conditions:
            query = query.where(and_(*conditions))
        query = (
            query.order_by(
                WorklogORM.occurred_at.desc(),
                WorklogORM.work_date.desc(),
                WorklogORM.created_at.desc(),
            )
            .limit(filters.limit)
            .offset(filters.offset)
        )
        return [
            self._to_model(item) for item in self.session.execute(query).scalars()
        ]

    def count(self, filters: WorklogFilters) -> int:
        conditions = self._conditions(filters)
        query = select(func.count()).select_from(WorklogORM)
        if conditions:
            query = query.where(and_(*conditions))
        return int(self.session.execute(query).scalar_one())

    def _conditions(self, filters: WorklogFilters) -> builtins.list[Any]:
        conditions: builtins.list[Any] = []
        if filters.repository_id:
            conditions.append(WorklogORM.repository_id == filters.repository_id)
        if filters.date_from:
            conditions.append(WorklogORM.work_date >= filters.date_from)
        if filters.date_to:
            conditions.append(WorklogORM.work_date <= filters.date_to)
        if filters.work_types:
            conditions.append(WorklogORM.work_type.in_(filters.work_types))
        if filters.confirmed_only:
            conditions.append(WorklogORM.confirmed_by_user.is_(True))
        if filters.tags:
            for tag in filters.tags:
                conditions.append(WorklogORM.tags_json.like(f'%"{tag}"%'))
        if filters.keyword:
            like = f"%{filters.keyword.strip()}%"
            conditions.append(
                or_(
                    WorklogORM.title.like(like),
                    WorklogORM.description.like(like),
                    WorklogORM.result.like(like),
                    WorklogORM.related_commit_hash.like(like),
                )
            )
        return conditions

    def _to_model(self, orm: WorklogORM) -> Worklog:
        return Worklog(
            id=orm.id,
            repository_id=orm.repository_id,
            work_date=orm.work_date,
            occurred_at=orm.occurred_at,
            work_type=cast(WorklogType, orm.work_type),
            title=orm.title,
            description=orm.description,
            result=orm.result,
            duration_minutes=orm.duration_minutes,
            tags=self.serializer.loads(orm.tags_json, []),
            related_commit_hash=orm.related_commit_hash,
            source=cast(WorklogSource, orm.source),
            confirmed_by_user=orm.confirmed_by_user,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )


class WeeklyReportRepository:
    """Persist weekly report drafts and confirmed reports."""

    def __init__(self, session: Session, serializer: JsonSerializer | None = None) -> None:
        self.session = session
        self.serializer = serializer or JsonSerializer()

    def create(self, report: WeeklyReport, *, repository_id: str | None = None) -> WeeklyReport:
        orm = WeeklyReportORM(
            id=report.id,
            repository_id=repository_id,
            date_from=report.date_range.date_from.isoformat(),
            date_to=report.date_range.date_to.isoformat(),
            title=report.title,
            content_markdown=report.content_markdown,
            content_json=self.serializer.dumps(report.model_dump(mode="json")),
            source_json=self.serializer.dumps(self._source_labels(report)),
            source_coverage=report.source_coverage,
            generator=report.generator,
            status=report.status,
            version=report.version,
            parent_report_id=report.parent_report_id,
            confirmed_at=report.confirmed_at,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )
        self.session.add(orm)
        self.session.flush()
        return self._to_model(orm)

    def get_by_id(self, report_id: str) -> WeeklyReport | None:
        orm = self.session.get(WeeklyReportORM, report_id)
        return self._to_model(orm) if orm else None

    def get_by_id_for_repository(
        self, report_id: str, repository_id: str
    ) -> WeeklyReport | None:
        orm = self.session.execute(
            select(WeeklyReportORM).where(
                WeeklyReportORM.id == report_id,
                WeeklyReportORM.repository_id == repository_id,
            )
        ).scalar_one_or_none()
        return self._to_model(orm) if orm else None

    def update(
        self, report: WeeklyReport, *, expected_version: int
    ) -> WeeklyReport:
        orm = self.session.get(WeeklyReportORM, report.id)
        if not orm:
            raise RecordNotFoundError(f"未找到周报：{report.id}")
        if orm.version != expected_version:
            raise RepositoryOperationError(
                "周报已被其他操作修改，请重新加载。"
            )
        orm.title = report.title
        orm.content_markdown = report.content_markdown
        orm.content_json = self.serializer.dumps(
            report.model_dump(mode="json")
        )
        orm.source_json = self.serializer.dumps(
            self._source_labels(report)
        )
        orm.source_coverage = report.source_coverage
        orm.generator = report.generator
        orm.status = report.status
        orm.version = report.version
        orm.parent_report_id = report.parent_report_id
        orm.confirmed_at = report.confirmed_at
        orm.updated_at = report.updated_at
        self.session.flush()
        return self._to_model(orm)

    def delete(self, report_id: str, *, expected_version: int) -> bool:
        orm = self.session.get(WeeklyReportORM, report_id)
        if not orm:
            return False
        if orm.version != expected_version:
            raise RepositoryOperationError(
                "周报已被其他操作修改，请重新加载。"
            )
        self.session.delete(orm)
        self.session.flush()
        return True

    def get_latest_for_range(self, date_from: date, date_to: date, repository_id: str | None = None) -> WeeklyReport | None:
        conditions = [WeeklyReportORM.date_from == date_from.isoformat(), WeeklyReportORM.date_to == date_to.isoformat()]
        if repository_id:
            conditions.append(WeeklyReportORM.repository_id == repository_id)
        orm = self.session.execute(
            select(WeeklyReportORM).where(and_(*conditions)).order_by(WeeklyReportORM.version.desc()).limit(1)
        ).scalar_one_or_none()
        return self._to_model(orm) if orm else None

    def list(
        self,
        *,
        repository_id: str | None = None,
        statuses: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WeeklyReport]:
        conditions = []
        if repository_id:
            conditions.append(WeeklyReportORM.repository_id == repository_id)
        if statuses:
            conditions.append(WeeklyReportORM.status.in_(statuses))
        query = select(WeeklyReportORM)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(WeeklyReportORM.created_at.desc()).limit(limit).offset(offset)
        return [self._to_model(item) for item in self.session.execute(query).scalars()]

    def confirm(self, report_id: str, confirmed_at: datetime) -> WeeklyReport:
        orm = self.session.get(WeeklyReportORM, report_id)
        if not orm:
            raise RecordNotFoundError(f"未找到周报：{report_id}")
        if orm.source_coverage < 1:
            raise RepositoryOperationError("来源覆盖率不足，不能确认周报。")
        orm.status = "confirmed"
        orm.confirmed_at = confirmed_at
        orm.updated_at = utc_now()
        self.session.flush()
        return self._to_model(orm)

    def mark_exported(self, report_id: str) -> WeeklyReport:
        orm = self.session.get(WeeklyReportORM, report_id)
        if not orm:
            raise RecordNotFoundError(f"未找到周报：{report_id}")
        orm.status = "exported"
        orm.updated_at = utc_now()
        self.session.flush()
        return self._to_model(orm)

    def _to_model(self, orm: WeeklyReportORM) -> WeeklyReport:
        data = self.serializer.loads(orm.content_json, None)
        if not data:
            raise RepositoryOperationError("周报结构化内容缺失。")
        return WeeklyReport.model_validate(data)

    def _source_labels(self, report: WeeklyReport) -> builtins.list[str]:
        labels: builtins.list[str] = []
        for topic in report.completed:
            labels.extend(source.label for source in topic.sources)
            for item in topic.items:
                labels.extend(source.label for source in item.sources)
        for section in [report.debugging, report.testing, report.risks, report.next_week]:
            for item in section:
                labels.extend(source.label for source in item.sources)
        return sorted(set(labels))


class NotificationStateMachine:
    """Validate notification status transitions."""

    allowed: ClassVar[dict[str, set[str]]] = {
        "pending": {"previewed", "duplicate_blocked", "cancelled"},
        "previewed": {"confirmed", "cancelled"},
        "confirmed": {"sending", "cancelled"},
        "sending": {"sent", "failed", "unknown"},
        "unknown": {"sending", "sent", "failed"},
        "failed": {"sending"},
        "sent": set(),
        "cancelled": set(),
        "duplicate_blocked": set(),
    }

    def can_transition(self, current: str, target: str) -> bool:
        return target == current or target in self.allowed.get(current, set())

    def transition(self, current: str, target: str) -> str:
        if not self.can_transition(current, target):
            raise RepositoryOperationError(f"非法通知状态转换：{current} -> {target}")
        return target


class NotificationRepository:
    """Persist notification audit records."""

    def __init__(
        self,
        session: Session,
        serializer: JsonSerializer | None = None,
        state_machine: NotificationStateMachine | None = None,
    ) -> None:
        self.session = session
        self.serializer = serializer or JsonSerializer()
        self.state_machine = state_machine or NotificationStateMachine()

    def create(self, record: NotificationRecord) -> NotificationRecord:
        orm = NotificationRecordORM(
            id=record.id,
            report_id=record.report_id,
            report_version=record.report_version,
            channel=record.channel,
            provider_mode=record.provider_mode,
            message_type=record.message_type,
            status=record.status,
            content_hash=record.content_hash,
            target_digest=record.target_digest,
            feishu_message_id=record.feishu_message_id,
            payload_summary=record.payload_summary,
            byte_size=record.byte_size,
            truncated=record.truncated,
            removed_sections_json=self.serializer.dumps(record.removed_sections),
            attempt_count=record.attempt_count,
            http_status=record.http_status,
            response_code=record.response_code,
            response_message=record.response_message,
            request_id=record.request_id,
            error_type=record.error_type,
            error_message=record.error_message,
            forced=record.forced,
            sent_at=record.sent_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
        self.session.add(orm)
        self.session.flush()
        return self._to_model(orm)

    def get_by_id(self, notification_id: str) -> NotificationRecord | None:
        orm = self.session.get(NotificationRecordORM, notification_id)
        return self._to_model(orm) if orm else None

    def update_status(
        self,
        notification_id: str,
        *,
        status: str,
        attempt_count: int | None = None,
        http_status: int | None = None,
        response_code: str | None = None,
        response_message: str | None = None,
        request_id: str | None = None,
        feishu_message_id: str | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        sent_at: datetime | None = None,
    ) -> NotificationRecord:
        orm = self.session.get(NotificationRecordORM, notification_id)
        if not orm:
            raise RecordNotFoundError(f"未找到通知记录：{notification_id}")
        orm.status = self.state_machine.transition(orm.status, status)
        if attempt_count is not None:
            orm.attempt_count = attempt_count
        orm.http_status = http_status
        orm.response_code = response_code
        orm.response_message = response_message
        orm.request_id = request_id
        orm.feishu_message_id = feishu_message_id
        orm.error_type = error_type
        orm.error_message = error_message
        orm.sent_at = sent_at
        orm.updated_at = utc_now()
        self.session.flush()
        return self._to_model(orm)

    def find_recent_by_hash(
        self,
        content_hash: str,
        *,
        channel: str,
        since: datetime,
        statuses: list[str] | None = None,
    ) -> list[NotificationRecord]:
        conditions = [
            NotificationRecordORM.content_hash == content_hash,
            NotificationRecordORM.channel == channel,
            NotificationRecordORM.created_at >= since,
        ]
        if statuses:
            conditions.append(NotificationRecordORM.status.in_(statuses))
        query = select(NotificationRecordORM).where(and_(*conditions)).order_by(NotificationRecordORM.created_at.desc())
        return [self._to_model(item) for item in self.session.execute(query).scalars()]

    def list_by_report(self, report_id: str) -> list[NotificationRecord]:
        query = (
            select(NotificationRecordORM)
            .where(NotificationRecordORM.report_id == report_id)
            .order_by(NotificationRecordORM.created_at.desc())
        )
        return [self._to_model(item) for item in self.session.execute(query).scalars()]

    def find_sent_by_fingerprint(
        self,
        content_hash: str,
        *,
        target_digest: str,
        statuses: list[str] | None = None,
    ) -> list[NotificationRecord]:
        conditions = [
            NotificationRecordORM.content_hash == content_hash,
            NotificationRecordORM.target_digest == target_digest,
        ]
        if statuses:
            conditions.append(NotificationRecordORM.status.in_(statuses))
        query = (
            select(NotificationRecordORM)
            .where(and_(*conditions))
            .order_by(NotificationRecordORM.created_at.desc())
        )
        return [self._to_model(item) for item in self.session.execute(query).scalars()]

    def list(
        self,
        *,
        status: str | None = None,
        channel: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationRecord]:
        conditions = []
        if status:
            conditions.append(NotificationRecordORM.status == status)
        if channel:
            conditions.append(NotificationRecordORM.channel == channel)
        if date_from:
            conditions.append(NotificationRecordORM.created_at >= date_from)
        if date_to:
            conditions.append(NotificationRecordORM.created_at <= date_to)
        query = select(NotificationRecordORM)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(NotificationRecordORM.created_at.desc()).limit(limit).offset(offset)
        return [self._to_model(item) for item in self.session.execute(query).scalars()]

    def _to_model(self, orm: NotificationRecordORM) -> NotificationRecord:
        return NotificationRecord(
            id=orm.id,
            report_id=orm.report_id,
            report_version=orm.report_version,
            channel=orm.channel,  # type: ignore[arg-type]
            provider_mode=orm.provider_mode,  # type: ignore[arg-type]
            message_type=orm.message_type,  # type: ignore[arg-type]
            status=orm.status,  # type: ignore[arg-type]
            content_hash=orm.content_hash,
            target_digest=orm.target_digest,
            feishu_message_id=orm.feishu_message_id,
            payload_summary=orm.payload_summary,
            byte_size=orm.byte_size,
            truncated=orm.truncated,
            removed_sections=self.serializer.loads(orm.removed_sections_json, []),
            attempt_count=orm.attempt_count,
            http_status=orm.http_status,
            response_code=orm.response_code,
            response_message=orm.response_message,
            request_id=orm.request_id,
            error_type=orm.error_type,
            error_message=orm.error_message,
            forced=orm.forced,
            sent_at=orm.sent_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )
