"""Safe Git command execution."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from gitpulse.exceptions import GitCommandError, GitCommandTimeoutError


@dataclass(frozen=True)
class GitCommandResult:
    command: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str


class GitCommandRunner:
    """Run read-only Git commands with timeout and structured errors."""

    def __init__(self, working_directory: Path, timeout_seconds: float = 10.0) -> None:
        self.working_directory = Path(working_directory)
        self.timeout_seconds = timeout_seconds

    def run(self, arguments: Sequence[str], *, check: bool = True) -> GitCommandResult:
        if not self.working_directory.exists():
            raise GitCommandError(f"工作目录不存在：{self.working_directory}")
        command = ("git", *tuple(arguments))
        try:
            completed = subprocess.run(
                list(command),
                cwd=self.working_directory,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise GitCommandError("未找到 git 命令，请确认 Git 已安装并在 PATH 中。") from exc
        except subprocess.TimeoutExpired as exc:
            raise GitCommandTimeoutError(
                f"Git 命令超时：{' '.join(command)}；工作目录：{self.working_directory}"
            ) from exc

        result = GitCommandResult(
            command=command,
            return_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if check and result.return_code != 0:
            safe_error = (result.stderr or result.stdout or "Git 命令执行失败").strip()
            raise GitCommandError(
                "Git 命令失败："
                f"{' '.join(command)}；工作目录：{self.working_directory}；"
                f"返回码：{result.return_code}；错误：{safe_error}"
            )
        return result

