"""Safe repository status and staging operations for the local Web console."""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path, PurePosixPath
from typing import ClassVar, cast

from gitplus.exceptions import GitCommandError
from gitplus.git.command_runner import GitCommandRunner
from gitplus.git.repository import GitRepository
from gitplus.models.repository import GitStatusEntry


class RepositoryWebError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class RepositoryPathValidator:
    """Keep user-selected paths inside the fixed repository."""

    def validate_relative_path(
        self,
        repository_root: Path,
        relative_path: str,
        *,
        status_paths: set[str],
    ) -> Path:
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or "\0" in relative_path
        ):
            raise RepositoryWebError("invalid_repository_path", "文件路径无效。")
        candidate = PurePosixPath(relative_path)
        if candidate.is_absolute() or relative_path.startswith("-"):
            raise RepositoryWebError("invalid_repository_path", "文件路径无效。")
        if ".git" in candidate.parts or ".." in candidate.parts:
            raise RepositoryWebError(
                "path_outside_repository", "文件路径超出当前仓库。"
            )
        normalized = candidate.as_posix()
        if normalized not in status_paths:
            raise RepositoryWebError("path_not_in_status", "文件不在当前仓库状态中。")
        root = repository_root.resolve()
        path = root.joinpath(*candidate.parts)
        resolved = path.resolve(strict=False)
        if not resolved.is_relative_to(root):
            raise RepositoryWebError(
                "path_outside_repository", "文件路径超出当前仓库。"
            )
        return path


class RepositoryWebService:
    """Read normalized status and serialize all Git writes with a revision."""

    _locks: ClassVar[dict[Path, threading.Lock]] = {}
    _locks_guard: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, root: Path) -> None:
        requested_root = root.resolve()
        requested_repository = GitRepository(requested_root)
        # Git status paths are always relative to the repository top level.
        # Use that same directory for writes when the Web console is opened
        # from a subdirectory of a larger repository.
        self.root = (
            requested_repository.get_root().resolve()
            if requested_repository.is_repository()
            else requested_root
        )
        self.repository = GitRepository(self.root)
        self.runner = GitCommandRunner(self.root, timeout_seconds=30)
        self.validator = RepositoryPathValidator()
        with self._locks_guard:
            self.lock = self._locks.setdefault(self.root, threading.Lock())

    def status(self) -> dict[str, object]:
        if not self.repository.is_repository():
            raise RepositoryWebError(
                "not_a_git_repository", "当前项目不是 Git 仓库。", 404
            )
        entries, raw = self._status_entries()
        info = self.repository.get_repository_info()
        files = [self._file_payload(entry) for entry in entries]
        staged = sum(bool(item["staged"]) for item in files)
        unstaged = sum(bool(item["unstaged"]) for item in files)
        untracked = sum(bool(item["untracked"]) for item in files)
        conflicted = sum(bool(item["conflicted"]) for item in files)
        revision = self._revision(raw, info.current_branch, info.head_commit)
        return {
            "repository": {
                "name": info.name,
                "root": str(info.root_path),
                "branch": info.current_branch,
                "head": info.head_commit[:8] if info.head_commit else None,
                "detached_head": info.current_branch is None
                and info.head_commit is not None,
                "is_clean": not files,
                "has_conflicts": bool(conflicted),
                "git_user_name": info.git_user_name,
                "git_user_email": info.git_user_email,
                "identity_configured": bool(info.git_user_name and info.git_user_email),
            },
            "summary": {
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
                "conflicted": conflicted,
            },
            "files": files,
            "revision": revision,
        }

    def stage(self, paths: list[str], revision: str) -> dict[str, object]:
        return self._write(paths, revision, stage=True)

    def unstage(self, paths: list[str], revision: str) -> dict[str, object]:
        return self._write(paths, revision, stage=False)

    def assert_revision(self, expected: str) -> dict[str, object]:
        current = self.status()
        if current["revision"] != expected:
            raise RepositoryWebError(
                "repository_changed",
                "仓库状态已发生变化，请刷新后重试。",
                409,
            )
        return current

    def status_paths(self) -> set[str]:
        files = cast(list[dict[str, object]], self.status()["files"])
        return {str(item["path"]) for item in files}

    def _write(
        self, paths: list[str], revision: str, *, stage: bool
    ) -> dict[str, object]:
        if not paths:
            raise RepositoryWebError("invalid_repository_path", "至少选择一个文件。")
        if len(paths) > 500:
            raise RepositoryWebError("too_many_paths", "一次最多操作 500 个文件。")
        if not self.lock.acquire(blocking=False):
            raise RepositoryWebError(
                "repository_busy", "当前仓库正在执行另一项写操作。", 409
            )
        try:
            status = self.assert_revision(revision)
            files = cast(list[dict[str, object]], status["files"])
            status_paths = {str(item["path"]) for item in files}
            for path in paths:
                self.validator.validate_relative_path(
                    self.root, path, status_paths=status_paths
                )
            if stage:
                arguments = ["add", "--", *paths]
                error_code = "git_stage_failed"
            elif status["repository"]["head"] is None:  # type: ignore[index]
                arguments = ["rm", "--cached", "--", *paths]
                error_code = "git_unstage_failed"
            else:
                arguments = ["restore", "--staged", "--", *paths]
                error_code = "git_unstage_failed"
            try:
                self.runner.run(arguments)
            except GitCommandError as exc:
                raise RepositoryWebError(error_code, str(exc)) from exc
            return self.status()
        finally:
            self.lock.release()

    def _status_entries(self) -> tuple[list[GitStatusEntry], str]:
        result = self.runner.run(
            ["status", "--porcelain=v2", "-z", "--untracked-files=all"]
        )
        return self._parse_porcelain_v2(result.stdout), result.stdout

    def _parse_porcelain_v2(self, output: str) -> list[GitStatusEntry]:
        records = output.split("\0")
        entries: list[GitStatusEntry] = []
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record or record.startswith(("#", "!")):
                continue
            kind = record[0]
            original_path = None
            if kind == "?":
                xy, path = "??", record[2:]
            elif kind == "1":
                parts = record.split(" ", 8)
                if len(parts) < 9:
                    continue
                xy, path = parts[1], parts[8]
            elif kind == "2":
                parts = record.split(" ", 9)
                if len(parts) < 10:
                    continue
                xy, path = parts[1], parts[9]
                if index < len(records):
                    original_path = records[index]
                    index += 1
            elif kind == "u":
                parts = record.split(" ", 10)
                if len(parts) < 11:
                    continue
                xy, path = parts[1], parts[10]
            else:
                continue
            entries.append(
                GitStatusEntry(
                    index_status=xy[0],
                    worktree_status=xy[1],
                    path=path,
                    original_path=original_path,
                    is_conflict=kind == "u",
                )
            )
        return entries

    def _file_payload(self, entry: GitStatusEntry) -> dict[str, object]:
        untracked = entry.index_status == "?" and entry.worktree_status == "?"
        staged = not untracked and entry.index_status not in {".", " "}
        unstaged = untracked or entry.worktree_status not in {".", " "}
        if entry.is_conflict:
            category = "conflicted"
        elif untracked:
            category = "untracked"
        elif staged and unstaged:
            category = "partially_staged"
        elif staged:
            category = "staged"
        else:
            category = "unstaged"
        return {
            "path": entry.path,
            "display_path": entry.path.replace("\n", "\\n"),
            "original_path": entry.original_path,
            "index_status": entry.index_status,
            "worktree_status": entry.worktree_status,
            "category": category,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "conflicted": entry.is_conflict,
        }

    def _revision(self, raw_status: str, branch: str | None, head: str | None) -> str:
        value = "\0".join([head or "", branch or "", raw_status])
        return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()
