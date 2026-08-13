"""Service facade for Git repository reads."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from gitplus.config import DiffConfig
from gitplus.git.diff_reader import GitDiffReader
from gitplus.git.log_reader import GitLogReader
from gitplus.git.repository import GitRepository
from gitplus.models.diff import DiffCollection
from gitplus.models.git_log import GitCommitRecord
from gitplus.models.repository import RepositoryInfo


class GitService:
    """Coordinate Git readers for CLI and future business services."""

    def __init__(self, path: Path | None = None, diff_config: DiffConfig | None = None) -> None:
        self.repository = GitRepository(path or Path.cwd())
        self.diff_config = diff_config or DiffConfig()

    def inspect_repository(self) -> RepositoryInfo:
        return self.repository.get_repository_info()

    def get_staged_diff(self) -> DiffCollection:
        return GitDiffReader(self.repository, self.diff_config).read_staged()

    def get_unstaged_diff(self) -> DiffCollection:
        return GitDiffReader(self.repository, self.diff_config).read_unstaged()

    def get_commits(
        self,
        date_from: datetime,
        date_to: datetime,
        authors: list[str] | None = None,
    ) -> list[GitCommitRecord]:
        return GitLogReader(self.repository).read(date_from, date_to, authors=authors)

