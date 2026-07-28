"""Git diff reading helpers."""

from __future__ import annotations

from gitpulse.config import DiffConfig
from gitpulse.git.parser import parse_git_patch, parse_numstat_z
from gitpulse.git.repository import GitRepository
from gitpulse.models.diff import DiffCollection, DiffSource, DiffStats, IgnoredFile
from gitpulse.security.diff_truncator import DiffTruncator
from gitpulse.security.file_filter import FileFilter


class GitDiffReader:
    """Read and structure Git diffs without mutating repository state."""

    def __init__(self, repository: GitRepository, config: DiffConfig) -> None:
        self.repository = repository
        self.config = config
        self.file_filter = FileFilter(config)
        self.truncator = DiffTruncator(config)

    def read_staged(self) -> DiffCollection:
        return self._read(
            DiffSource.STAGED,
            patch_args=["diff", "--cached", "--no-ext-diff", "--binary", "--find-renames", "--find-copies"],
            numstat_args=["diff", "--cached", "--numstat", "-z", "--find-renames", "--find-copies"],
        )

    def read_unstaged(self) -> DiffCollection:
        return self._read(
            DiffSource.UNSTAGED,
            patch_args=["diff", "--no-ext-diff", "--binary", "--find-renames", "--find-copies"],
            numstat_args=["diff", "--numstat", "-z", "--find-renames", "--find-copies"],
        )

    def read_commit(self, commit: str) -> DiffCollection:
        return self._read(
            DiffSource.COMMIT,
            patch_args=["show", "--format=", "--patch", "--no-ext-diff", "--binary", "--find-renames", commit],
            numstat_args=["show", "--format=", "--numstat", "-z", "--find-renames", commit],
            target_commit=commit,
        )

    def read_range(self, base_commit: str, target_commit: str) -> DiffCollection:
        return self._read(
            DiffSource.RANGE,
            patch_args=["diff", "--no-ext-diff", "--binary", "--find-renames", "--find-copies", base_commit, target_commit],
            numstat_args=["diff", "--numstat", "-z", "--find-renames", "--find-copies", base_commit, target_commit],
            base_commit=base_commit,
            target_commit=target_commit,
        )

    def _read(
        self,
        source: DiffSource,
        *,
        patch_args: list[str],
        numstat_args: list[str],
        base_commit: str | None = None,
        target_commit: str | None = None,
    ) -> DiffCollection:
        patch = self.repository.runner.run(patch_args).stdout
        numstat = self.repository.runner.run(numstat_args).stdout
        stats_by_path = parse_numstat_z(numstat)
        files = parse_git_patch(patch)

        ignored_files: list[IgnoredFile] = []
        kept_files = []
        for file in files:
            if file.new_path in stats_by_path:
                file.additions, file.deletions = stats_by_path[file.new_path]
            should_ignore, reason = self.file_filter.should_ignore(file.new_path, file.is_binary)
            if should_ignore:
                ignored_files.append(IgnoredFile(path=file.new_path, reason=reason or "ignored"))
                continue
            kept_files.append(file)

        collection = DiffCollection(
            source=source,
            base_commit=base_commit,
            target_commit=target_commit,
            files=kept_files,
            ignored_files=ignored_files,
            original_total_chars=sum(len(file.patch) for file in files),
        )
        collection.stats = DiffStats(
            files_changed=len(kept_files),
            insertions=sum(file.additions for file in kept_files),
            deletions=sum(file.deletions for file in kept_files),
            total_patch_chars=sum(len(file.patch) for file in kept_files),
        )
        return self.truncator.truncate(collection)

