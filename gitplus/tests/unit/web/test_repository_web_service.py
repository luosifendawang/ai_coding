from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gitplus.web.services.repository_web_service import (
    RepositoryPathValidator,
    RepositoryWebError,
    RepositoryWebService,
)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def repository(path: Path, *, initial_commit: bool = True) -> Path:
    path.mkdir()
    git(path, "init")
    git(path, "config", "user.name", "Test User")
    git(path, "config", "user.email", "test@example.com")
    if initial_commit:
        (path / "README.md").write_text("start\n", encoding="utf-8")
        git(path, "add", "--", "README.md")
        git(path, "commit", "-m", "chore: initialize")
    return path


def test_status_classifies_staged_unstaged_untracked_and_partial(
    tmp_path: Path,
) -> None:
    root = repository(tmp_path / "repo")
    (root / "README.md").write_text("staged\n", encoding="utf-8")
    git(root, "add", "--", "README.md")
    (root / "README.md").write_text("partial\n", encoding="utf-8")
    (root / "新 文件.txt").write_text("new\n", encoding="utf-8")

    status = RepositoryWebService(root).status()
    files = {item["path"]: item for item in status["files"]}

    assert files["README.md"]["category"] == "partially_staged"
    assert files["新 文件.txt"]["untracked"] is True
    assert status["summary"] == {
        "staged": 1,
        "unstaged": 2,
        "untracked": 1,
        "conflicted": 0,
    }


def test_stage_and_unstage_require_current_revision(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "file.txt").write_text("content\n", encoding="utf-8")
    service = RepositoryWebService(root)
    initial = service.status()

    staged = service.stage(["file.txt"], str(initial["revision"]))
    assert staged["summary"]["staged"] == 1

    with pytest.raises(RepositoryWebError, match="仓库状态已发生变化"):
        service.unstage(["file.txt"], str(initial["revision"]))

    unstaged = service.unstage(["file.txt"], str(staged["revision"]))
    assert unstaged["summary"]["untracked"] == 1
    assert (root / "file.txt").exists()


def test_unstage_in_repository_without_head_keeps_worktree_file(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo", initial_commit=False)
    (root / "first.txt").write_text("content\n", encoding="utf-8")
    service = RepositoryWebService(root)
    staged = service.stage(["first.txt"], str(service.status()["revision"]))

    service.unstage(["first.txt"], str(staged["revision"]))

    assert (root / "first.txt").read_text(encoding="utf-8") == "content\n"
    assert git(root, "status", "--porcelain") == "?? first.txt"


@pytest.mark.parametrize(
    "path,code",
    [
        ("", "invalid_repository_path"),
        ("/etc/passwd", "invalid_repository_path"),
        ("../outside", "path_outside_repository"),
        (".git/config", "path_outside_repository"),
        ("--force", "invalid_repository_path"),
        ("not-in-status.txt", "path_not_in_status"),
    ],
)
def test_path_validator_rejects_unsafe_paths(
    tmp_path: Path, path: str, code: str
) -> None:
    root = repository(tmp_path / "repo")

    with pytest.raises(RepositoryWebError) as raised:
        RepositoryPathValidator().validate_relative_path(
            root, path, status_paths={"README.md"}
        )

    assert raised.value.code == code


def test_path_validator_rejects_symlink_escape(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (root / "link.txt").symlink_to(outside)

    with pytest.raises(RepositoryWebError) as raised:
        RepositoryPathValidator().validate_relative_path(
            root, "link.txt", status_paths={"link.txt"}
        )

    assert raised.value.code == "path_outside_repository"
