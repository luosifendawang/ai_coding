from __future__ import annotations

import subprocess
from pathlib import Path

from gitplus.config import SecurityConfig, WebDiffConfig
from gitplus.web.services.diff_web_service import DiffWebService
from gitplus.web.services.repository_web_service import RepositoryWebService


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def repository(path: Path) -> Path:
    path.mkdir()
    git(path, "init")
    git(path, "config", "user.name", "Test User")
    git(path, "config", "user.email", "test@example.com")
    (path / "README.md").write_text("start\n", encoding="utf-8")
    git(path, "add", "--", "README.md")
    git(path, "commit", "-m", "chore: initialize")
    return path


def service(root: Path, *, max_diff_chars: int = 200_000) -> DiffWebService:
    return DiffWebService(
        RepositoryWebService(root),
        WebDiffConfig(max_diff_chars=max_diff_chars),
        SecurityConfig(),
    )


def test_reads_staged_and_unstaged_diff(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "README.md").write_text("staged\n", encoding="utf-8")
    git(root, "add", "--", "README.md")
    staged = service(root).read("README.md", "staged")
    (root / "README.md").write_text("unstaged\n", encoding="utf-8")
    unstaged = service(root).read("README.md", "unstaged")

    assert "+staged" in staged["diff"]
    assert "+unstaged" in unstaged["diff"]


def test_untracked_preview_masks_secret_and_truncates(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    token = "sk-" + "a" * 32
    (root / "new.txt").write_text(token + "\n" + ("x" * 4000), encoding="utf-8")

    result = service(root, max_diff_chars=1000).read("new.txt", "unstaged")

    assert result["truncated"] is True
    assert token not in result["diff"]


def test_binary_untracked_file_does_not_return_content(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "image.bin").write_bytes(b"\x00\x01secret")

    result = service(root).read("image.bin", "unstaged")

    assert result["binary"] is True
    assert result["diff"] == ""
