"""Weekly data collection."""

from __future__ import annotations

from dataclasses import dataclass

from gitpulse.config import WeeklyConfig
from gitpulse.exceptions import WeeklyCollectionError
from gitpulse.git.log_reader import GitLogReader
from gitpulse.models.diff import DiffCollection
from gitpulse.models.weekly import (
    WeeklyCommitInput,
    WeeklyDateRange,
    WeeklyGenerationInput,
    WeeklyUncommittedInput,
    WeeklyWorklogInput,
)
from gitpulse.models.worklog import WorklogFilters
from gitpulse.services.git_service import GitService
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class WeeklyCollectRequest:
    date_range_label: str = "current"
    authors: list[str] | None = None
    include_uncommitted: bool = False


class WeeklyDataCollector:
    """Collect Git commits, confirmed commit records, and worklogs."""

    def __init__(
        self,
        *,
        database: Database,
        git_service: GitService,
        config: WeeklyConfig,
    ) -> None:
        self.database = database
        self.git_service = git_service
        self.config = config

    def collect(
        self,
        date_range: WeeklyDateRange,
        *,
        authors: list[str] | None = None,
        include_uncommitted: bool = False,
    ) -> WeeklyGenerationInput:
        repository_info = self.git_service.inspect_repository()
        author_emails = self._authors(authors, repository_info.git_user_email)
        git_records = GitLogReader(self.git_service.repository).read(
            date_range.datetime_from,
            date_range.datetime_to,
            authors=author_emails,
            max_count=self.config.max_commits,
        )
        with UnitOfWork(self.database) as uow:
            repo_record = uow.repositories.get_by_root_path(str(repository_info.root_path))
            repository_id = repo_record.id if repo_record else "repo_current"
            commit_records = uow.commit_records.list_by_repository(
                repository_id,
                date_from=date_range.datetime_from,
                date_to=date_range.datetime_to,
                confirmed_only=True,
                limit=self.config.max_commits,
            )
            worklogs = uow.worklogs.list(
                WorklogFilters(
                    repository_id=None,
                    date_from=date_range.date_from,
                    date_to=date_range.date_to,
                    limit=self.config.max_worklogs,
                )
            )
        commits = [
            WeeklyCommitInput(
                commit_hash=record.commit_hash,
                short_hash=record.short_hash,
                repository_id=repository_id,
                repository_name=repository_info.name,
                branch=repository_info.current_branch,
                author_email=record.author_email,
                committed_at=record.committed_at,
                subject=record.subject,
                body=record.body,
                files=record.changed_files,
                insertions=record.insertions,
                deletions=record.deletions,
            )
            for record in git_records
            if self.config.include_merge_commits or len(record.parents) <= 1
        ]
        uncommitted = (
            self._collect_uncommitted(repository_id, repository_info.name, repository_info.current_branch)
            if include_uncommitted
            else []
        )
        return WeeklyGenerationInput(
            date_range=date_range,
            commits=commits,
            commit_records=commit_records,
            worklogs=[
                WeeklyWorklogInput(
                    id=item.id,
                    repository_id=item.repository_id,
                    repository_name=repository_info.name if item.repository_id == repository_id else None,
                    work_date=item.work_date,
                    work_type=item.work_type,
                    title=item.title,
                    description=item.description,
                    result=item.result,
                    duration_minutes=item.duration_minutes,
                    tags=item.tags,
                )
                for item in worklogs
            ],
            uncommitted_changes=uncommitted,
        )

    def _authors(self, override: list[str] | None, git_email: str | None) -> list[str]:
        emails = override or ([git_email] if git_email else [])
        normalized = sorted({email.strip().lower() for email in emails if email and email.strip()})
        if not normalized:
            raise WeeklyCollectionError("未配置 Git 用户邮箱，无法准确筛选个人提交。")
        return normalized

    def _collect_uncommitted(
        self,
        repository_id: str,
        repository_name: str,
        branch: str | None,
    ) -> list[WeeklyUncommittedInput]:
        entries: list[WeeklyUncommittedInput] = []
        staged = self.git_service.get_staged_diff()
        unstaged = self.git_service.get_unstaged_diff()
        entries.extend(self._uncommitted_from_diff(repository_id, repository_name, branch, "暂存区", staged))
        entries.extend(self._uncommitted_from_diff(repository_id, repository_name, branch, "工作区", unstaged))
        untracked = [
            entry.path
            for entry in self.git_service.repository.get_status_entries()
            if entry.index_status == "?" and entry.worktree_status == "?"
        ]
        if untracked:
            entries.append(
                WeeklyUncommittedInput(
                    repository_id=repository_id,
                    repository_name=repository_name,
                    branch=branch,
                    summary=f"未跟踪文件待确认：{', '.join(sorted(untracked)[:10])}",
                    files=sorted(untracked),
                    confidence="medium",
                    confirmed_by_user=False,
                )
            )
        return entries

    def _uncommitted_from_diff(
        self,
        repository_id: str,
        repository_name: str,
        branch: str | None,
        label: str,
        diff: DiffCollection,
    ) -> list[WeeklyUncommittedInput]:
        if diff.stats.files_changed == 0:
            return []
        files = [file.new_path for file in diff.files]
        summary = f"{label}存在 {diff.stats.files_changed} 个未提交变更文件"
        return [
            WeeklyUncommittedInput(
                repository_id=repository_id,
                repository_name=repository_name,
                branch=branch,
                summary=summary,
                files=files,
                confidence="medium",
                confirmed_by_user=False,
            )
        ]
