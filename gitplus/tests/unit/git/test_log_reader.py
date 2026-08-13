from datetime import datetime, timedelta, timezone
from pathlib import Path

from conftest import commit_file, init_repo, run_git

from gitplus.git.log_reader import GitLogReader
from gitplus.git.repository import GitRepository


def reader(repo_path: Path) -> GitLogReader:
    return GitLogReader(GitRepository(repo_path))


def test_log_reader_reads_date_range_and_chinese_message(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    commit_file(repo_path, "README.md", "hello\n")
    run_git(repo_path, "commit", "--allow-empty", "-m", "修复中文问题", "-m", "多行说明")

    records = reader(repo_path).read(
        datetime.now(timezone.utc) - timedelta(days=1),
        datetime.now(timezone.utc) + timedelta(days=1),
    )

    assert records[0].subject == "修复中文问题"
    assert "多行说明" in records[0].body
    assert records[0].author_email == "test@example.com"
    assert records[0].commit_hash


def test_log_reader_filters_by_exact_author_email(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    commit_file(repo_path, "one.txt", "one\n")
    run_git(repo_path, "config", "user.email", "other@example.com")
    commit_file(repo_path, "two.txt", "two\n")

    records = reader(repo_path).read(
        datetime.now(timezone.utc) - timedelta(days=1),
        datetime.now(timezone.utc) + timedelta(days=1),
        authors=["test@example.com"],
    )

    assert len(records) == 1
    assert records[0].author_email == "test@example.com"
    assert records[0].changed_files == ["one.txt"]


def test_log_reader_limits_results(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    for index in range(3):
        commit_file(repo_path, f"{index}.txt", f"{index}\n")

    records = reader(repo_path).read(
        datetime.now(timezone.utc) - timedelta(days=1),
        datetime.now(timezone.utc) + timedelta(days=1),
        max_count=2,
    )

    assert len(records) == 2


def test_log_reader_handles_empty_commit(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    run_git(repo_path, "commit", "--allow-empty", "-m", "empty commit")

    records = reader(repo_path).read(
        datetime.now(timezone.utc) - timedelta(days=1),
        datetime.now(timezone.utc) + timedelta(days=1),
    )

    assert records[0].subject == "empty commit"
    assert records[0].changed_files == []
    assert records[0].insertions == 0
    assert records[0].deletions == 0

