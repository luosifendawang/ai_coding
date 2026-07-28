from pathlib import Path

import pytest

from gitpulse.exceptions import GitRepositoryError
from gitpulse.git.repository import GitRepository
from conftest import commit_file, init_repo, run_git


def test_non_git_directory_is_reported(tmp_path: Path) -> None:
    repo = GitRepository(tmp_path)

    assert repo.is_repository() is False
    with pytest.raises(GitRepositoryError):
        repo.get_root()


def test_empty_repository_has_no_head(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "empty")
    repo = GitRepository(repo_path)

    assert repo.is_repository() is True
    assert repo.get_root() == repo_path
    assert repo.get_head_commit() is None


def test_repository_info_reads_metadata(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    head = commit_file(repo_path)
    run_git(repo_path, "remote", "add", "origin", "git@example.com:org/repo.git")

    info = GitRepository(repo_path).get_repository_info()

    assert info.name == "repo"
    assert info.root_path == repo_path
    assert info.current_branch in {"master", "main"}
    assert info.head_commit == head
    assert info.git_user_name == "Test User"
    assert info.git_user_email == "test@example.com"
    assert info.remote_url == "git@example.com:org/repo.git"


def test_repository_allows_missing_user_config(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo", configure_user=False)
    repo = GitRepository(repo_path)

    assert repo.get_user_name() is None
    assert repo.get_user_email() is None


def test_repository_status_flags(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    commit_file(repo_path)
    (repo_path / "staged.txt").write_text("staged\n", encoding="utf-8")
    run_git(repo_path, "add", "staged.txt")
    (repo_path / "README.md").write_text("changed\n", encoding="utf-8")
    (repo_path / "untracked.txt").write_text("new\n", encoding="utf-8")

    repo = GitRepository(repo_path)

    assert repo.has_staged_changes() is True
    assert repo.has_unstaged_changes() is True
    assert repo.has_untracked_files() is True


def test_repository_detached_head_returns_no_branch(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    head = commit_file(repo_path)
    run_git(repo_path, "checkout", "--detach", head)

    repo = GitRepository(repo_path)

    assert repo.get_current_branch() is None
    assert repo.get_head_commit() == head
