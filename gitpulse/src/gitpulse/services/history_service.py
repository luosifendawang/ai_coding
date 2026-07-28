"""History query service."""

from __future__ import annotations

from gitpulse.models.history import CommitHistoryFilters
from gitpulse.models.storage import CommitRecord
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork
from gitpulse.exceptions import RecordNotFoundError


class HistoryService:
    """Query persisted commit records."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def list_commit_records(self, filters: CommitHistoryFilters) -> list[CommitRecord]:
        with UnitOfWork(self.database) as uow:
            repository_id = filters.repository_id
            if repository_id is None:
                repositories = uow.repositories.list_all()
                if not repositories:
                    return []
                repository_id = repositories[0].id
            return uow.commit_records.list_by_repository(
                repository_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                confirmed_only=filters.confirmed_only,
                limit=filters.limit,
                offset=filters.offset,
                commit_type=filters.commit_type,
                confidence=filters.confidence,
                search=filters.search,
            )

    def get_commit_record(self, record_id: str) -> CommitRecord:
        with UnitOfWork(self.database) as uow:
            record = uow.commit_records.get_by_id(record_id)
            if not record:
                raise RecordNotFoundError(f"未找到历史记录：{record_id}")
            return record

