from __future__ import annotations

from pathlib import Path

from conftest import commit_file, init_repo, run_git

from gitpulse.config import DiffConfig
from gitpulse.git.diff_reader import GitDiffReader
from gitpulse.git.repository import GitRepository
from gitpulse.models.diff import DiffSource, FileChangeStatus


def make_reader(repo_path: Path, config: DiffConfig | None = None) -> GitDiffReader:
    return GitDiffReader(GitRepository(repo_path), config or DiffConfig())


def test_read_staged_diff_for_added_file_with_chinese_path(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    commit_file(repo_path)
    target = repo_path / "中文 路径.py"
    target.write_text("print('你好')\n", encoding="utf-8")
    run_git(repo_path, "add", "中文 路径.py")

    diff = make_reader(repo_path).read_staged()

    assert diff.source == DiffSource.STAGED
    assert diff.stats.files_changed == 1
    assert diff.files[0].new_path == "中文 路径.py"
    assert diff.files[0].status == FileChangeStatus.ADDED
    assert diff.files[0].additions == 1


def test_read_unstaged_diff_for_modified_file(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    commit_file(repo_path)
    (repo_path / "README.md").write_text("hello\nworld\n", encoding="utf-8")

    diff = make_reader(repo_path).read_unstaged()

    assert diff.source == DiffSource.UNSTAGED
    assert diff.files[0].new_path == "README.md"
    assert diff.files[0].additions == 1


def test_read_commit_and_range(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    first = commit_file(repo_path, "README.md", "one\n")
    second = commit_file(repo_path, "src/app.py", "print('app')\n")

    reader = make_reader(repo_path)
    commit_diff = reader.read_commit(second)
    range_diff = reader.read_range(first, second)

    assert commit_diff.source == DiffSource.COMMIT
    assert commit_diff.target_commit == second
    assert commit_diff.files[0].new_path == "src/app.py"
    assert range_diff.source == DiffSource.RANGE
    assert range_diff.base_commit == first
    assert range_diff.target_commit == second


def test_read_diff_handles_rename_delete_binary_and_ignore(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    commit_file(repo_path, "old name.txt", "old\n")
    (repo_path / "remove.txt").write_text("remove\n", encoding="utf-8")
    (repo_path / "assets.bin").write_bytes(b"\x00\x01\x02")
    (repo_path / "package-lock.json").write_text("{}\n", encoding="utf-8")
    run_git(repo_path, "add", ".")
    run_git(repo_path, "commit", "-m", "add fixtures")

    run_git(repo_path, "mv", "old name.txt", "new name.txt")
    (repo_path / "remove.txt").unlink()
    (repo_path / "assets.bin").write_bytes(b"\x00\x01\x03")
    (repo_path / "package-lock.json").write_text('{"changed": true}\n', encoding="utf-8")
    run_git(repo_path, "add", ".")

    diff = make_reader(repo_path).read_staged()
    paths = {file.new_path for file in diff.files}

    assert "new name.txt" in paths
    assert "remove.txt" in paths
    assert "assets.bin" not in paths
    assert any(ignored.path == "assets.bin" for ignored in diff.ignored_files)
    assert any(ignored.path == "package-lock.json" for ignored in diff.ignored_files)
    renamed = next(file for file in diff.files if file.new_path == "new name.txt")
    assert renamed.is_renamed is True


def test_read_empty_staged_diff(tmp_path: Path) -> None:
    repo_path = init_repo(tmp_path / "repo")
    commit_file(repo_path)

    diff = make_reader(repo_path).read_staged()

    assert diff.files == []
    assert diff.stats.files_changed == 0

