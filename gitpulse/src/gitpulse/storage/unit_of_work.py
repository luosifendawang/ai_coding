"""Unit of Work transaction boundary."""

from __future__ import annotations

from sqlalchemy.orm import Session

from gitpulse.storage.database import Database
from gitpulse.storage.repositories import (
    CommitRecordRepository,
    NotificationRepository,
    RepositoryRepository,
    RiskRepository,
    WeeklyReportRepository,
    WorklogRepository,
)


class UnitOfWork:
    """Create repositories around a single SQLAlchemy transaction."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.session: Session | None = None

    def __enter__(self) -> "UnitOfWork":
        self.session = self.database.create_session()
        self.repositories = RepositoryRepository(self.session)
        self.commit_records = CommitRecordRepository(self.session)
        self.risks = RiskRepository(self.session)
        self.worklogs = WorklogRepository(self.session)
        self.weekly_reports = WeeklyReportRepository(self.session)
        self.notifications = NotificationRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # type: ignore[no-untyped-def]
        if self.session is None:
            return
        if exc_type is None:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()

    def commit(self) -> None:
        if self.session is not None:
            self.session.commit()

    def rollback(self) -> None:
        if self.session is not None:
            self.session.rollback()
