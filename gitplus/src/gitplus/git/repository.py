"""Git repository metadata helpers."""

from __future__ import annotations

from pathlib import Path

from gitplus.exceptions import GitRepositoryError
from gitplus.git.command_runner import GitCommandRunner
from gitplus.git.parser import parse_porcelain_status_z
from gitplus.models.repository import GitStatusEntry, RepositoryInfo


class GitRepository:
    """Read metadata and status from a Git repository."""

    def __init__(self, path: Path, runner: GitCommandRunner | None = None) -> None:
        self.path = Path(path)
        self.runner = runner or GitCommandRunner(self.path)

    def is_repository(self) -> bool:
        result = self.runner.run(["rev-parse", "--is-inside-work-tree"], check=False)
        return result.return_code == 0 and result.stdout.strip() == "true"

    def get_root(self) -> Path:
        result = self.runner.run(["rev-parse", "--show-toplevel"], check=False)
        if result.return_code != 0:
            raise GitRepositoryError(
                "当前目录不是 Git 仓库。\n\n请进入 Git 项目目录后重新执行，\n或运行：\n\ngit init"
            )
        return Path(result.stdout.strip())

    def get_name(self) -> str:
        return self.get_root().name

    def get_current_branch(self) -> str | None:
        result = self.runner.run(["branch", "--show-current"], check=False)
        branch = result.stdout.strip()
        return branch or None

    def get_head_commit(self) -> str | None:
        result = self.runner.run(["rev-parse", "HEAD"], check=False)
        if result.return_code != 0:
            return None
        return result.stdout.strip() or None

    def get_user_name(self) -> str | None:
        result = self.runner.run(["config", "--get", "user.name"], check=False)
        return result.stdout.strip() or None if result.return_code == 0 else None

    def get_user_email(self) -> str | None:
        result = self.runner.run(["config", "--get", "user.email"], check=False)
        return result.stdout.strip() or None if result.return_code == 0 else None

    def get_remote_url(self, remote: str = "origin") -> str | None:
        result = self.runner.run(["remote", "get-url", remote], check=False)
        return result.stdout.strip() or None if result.return_code == 0 else None

    def get_status_entries(self) -> list[GitStatusEntry]:
        result = self.runner.run(["status", "--porcelain=v1", "-z"])
        return parse_porcelain_status_z(result.stdout)

    def has_staged_changes(self) -> bool:
        return any(
            entry.index_status not in {" ", "?", "!"}
            for entry in self.get_status_entries()
        )

    def has_unstaged_changes(self) -> bool:
        return any(
            entry.worktree_status not in {" ", "?", "!"}
            for entry in self.get_status_entries()
        )

    def has_untracked_files(self) -> bool:
        return any(
            entry.index_status == "?" and entry.worktree_status == "?"
            for entry in self.get_status_entries()
        )

    def has_conflicts(self) -> bool:
        return any(entry.is_conflict for entry in self.get_status_entries())

    def get_repository_info(self) -> RepositoryInfo:
        if not self.is_repository():
            raise GitRepositoryError(
                "当前目录不是 Git 仓库。\n\n请进入 Git 项目目录后重新执行，\n或运行：\n\ngit init"
            )
        return RepositoryInfo(
            name=self.get_name(),
            root_path=self.get_root(),
            current_branch=self.get_current_branch(),
            head_commit=self.get_head_commit(),
            git_user_name=self.get_user_name(),
            git_user_email=self.get_user_email(),
            remote_url=self.get_remote_url(),
            has_staged_changes=self.has_staged_changes(),
            has_unstaged_changes=self.has_unstaged_changes(),
            has_untracked_files=self.has_untracked_files(),
            has_conflicts=self.has_conflicts(),
        )
