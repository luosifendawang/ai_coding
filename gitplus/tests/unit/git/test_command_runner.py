import subprocess
from pathlib import Path

import pytest

from gitplus.exceptions import GitCommandError, GitCommandTimeoutError
from gitplus.git.command_runner import GitCommandRunner


def test_runner_executes_git_command(tmp_path: Path) -> None:
    runner = GitCommandRunner(tmp_path)

    result = runner.run(["--version"])

    assert result.return_code == 0
    assert result.command == ("git", "--version")
    assert "git version" in result.stdout


def test_runner_raises_on_non_zero_exit(tmp_path: Path) -> None:
    runner = GitCommandRunner(tmp_path)

    with pytest.raises(GitCommandError) as exc_info:
        runner.run(["rev-parse", "--show-toplevel"])

    assert "rev-parse" in str(exc_info.value)
    assert str(tmp_path) in str(exc_info.value)


def test_runner_allows_non_zero_when_check_false(tmp_path: Path) -> None:
    runner = GitCommandRunner(tmp_path)

    result = runner.run(["rev-parse", "--show-toplevel"], check=False)

    assert result.return_code != 0
    assert result.stderr


def test_runner_rejects_missing_working_directory(tmp_path: Path) -> None:
    runner = GitCommandRunner(tmp_path / "missing")

    with pytest.raises(GitCommandError):
        runner.run(["--version"])


def test_runner_handles_paths_with_spaces(tmp_path: Path) -> None:
    spaced = tmp_path / "repo with spaces"
    spaced.mkdir()
    runner = GitCommandRunner(spaced)

    result = runner.run(["--version"])

    assert result.return_code == 0


def test_runner_raises_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=["git", "status"], timeout=0.001)

    monkeypatch.setattr(subprocess, "run", raise_timeout)
    runner = GitCommandRunner(tmp_path, timeout_seconds=0.001)

    with pytest.raises(GitCommandTimeoutError):
        runner.run(["status"])
