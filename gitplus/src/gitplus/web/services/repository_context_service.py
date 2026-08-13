"""Resolve the fixed Web repository to its persisted record."""

from __future__ import annotations

from datetime import datetime, timezone

from gitplus.models.storage import RepositoryRecord
from gitplus.storage.database import Database
from gitplus.storage.serializers import IdGenerator
from gitplus.storage.unit_of_work import UnitOfWork
from gitplus.web.services.repository_web_service import (
    RepositoryWebError,
    RepositoryWebService,
)


class RepositoryContextService:
    def __init__(
        self, repository_service: RepositoryWebService, database: Database
    ) -> None:
        self.repository_service = repository_service
        self.database = database
        self.id_generator = IdGenerator()

    def ensure_record(self) -> RepositoryRecord:
        self.database.initialize()
        try:
            info = self.repository_service.repository.get_repository_info()
        except Exception as exc:
            raise RepositoryWebError(
                "not_a_git_repository", "当前项目不是 Git 仓库。", 404
            ) from exc
        current = datetime.now(timezone.utc)
        with UnitOfWork(self.database) as uow:
            return uow.repositories.upsert(
                RepositoryRecord(
                    id=self.id_generator.new_repository_id(),
                    name=info.name,
                    root_path=str(info.root_path),
                    remote_url=info.remote_url,
                    created_at=current,
                    updated_at=current,
                    last_seen_at=current,
                )
            )
