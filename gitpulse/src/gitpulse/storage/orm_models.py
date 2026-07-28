"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class MigrationORM(Base):
    __tablename__ = "migrations"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class RepositoryORM(Base, TimestampMixin):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    root_path: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    remote_url: Mapped[str | None] = mapped_column(String, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CommitRecordORM(Base, TimestampMixin):
    __tablename__ = "commit_records"
    __table_args__ = (UniqueConstraint("repository_id", "commit_hash", name="uq_commit_record_hash"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    repository_id: Mapped[str] = mapped_column(ForeignKey("repositories.id"), nullable=False, index=True)
    commit_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    branch: Mapped[str | None] = mapped_column(String)
    commit_type: Mapped[str | None] = mapped_column(String, index=True)
    scope: Mapped[str | None] = mapped_column(String)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    files_json: Mapped[str | None] = mapped_column(Text)
    insertions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[str | None] = mapped_column(String, index=True)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_type: Mapped[str] = mapped_column(String, default="generated_commit")
    generation_provider: Mapped[str | None] = mapped_column(String)
    generation_model: Mapped[str | None] = mapped_column(String)
    selected_candidate: Mapped[str | None] = mapped_column(String)
    should_split: Mapped[bool] = mapped_column(Boolean, default=False)
    split_confidence: Mapped[float | None] = mapped_column(Float)
    verification_json: Mapped[str | None] = mapped_column(Text)
    security_summary_json: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True, index=True)


class WorklogORM(Base, TimestampMixin):
    __tablename__ = "worklogs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    repository_id: Mapped[str | None] = mapped_column(ForeignKey("repositories.id"), nullable=True, index=True)
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    work_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    tags_json: Mapped[str | None] = mapped_column(Text)
    confirmed_by_user: Mapped[bool] = mapped_column(Boolean, default=True)


class RiskORM(Base):
    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    record_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    record_type: Mapped[str] = mapped_column(String, nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String)
    risk_level: Mapped[str] = mapped_column(String, nullable=False, index=True)
    risk_type: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String)
    line_number: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    masked_value: Mapped[str | None] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)
    blocks_remote_model: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class WeeklyReportORM(Base, TimestampMixin):
    __tablename__ = "weekly_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    repository_id: Mapped[str | None] = mapped_column(ForeignKey("repositories.id"), nullable=True, index=True)
    date_from: Mapped[str] = mapped_column(String, nullable=False)
    date_to: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str | None] = mapped_column(Text)
    source_json: Mapped[str | None] = mapped_column(Text)
    source_coverage: Mapped[float] = mapped_column(Float, default=0.0)
    generator: Mapped[str] = mapped_column(String, default="rule_based")
    status: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_report_id: Mapped[str | None] = mapped_column(String)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationRecordORM(Base):
    __tablename__ = "notification_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("weekly_reports.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False, index=True)
    message_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    payload_summary: Mapped[str | None] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False)
    removed_sections_json: Mapped[str | None] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    http_status: Mapped[int | None] = mapped_column(Integer)
    response_code: Mapped[str | None] = mapped_column(String)
    response_message: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String)
    error_type: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    forced: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
