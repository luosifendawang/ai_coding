from pathlib import Path
import json
import subprocess

from typer.testing import CliRunner

from gitpulse.cli import app


runner = CliRunner()


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def init_repo(path: Path) -> Path:
    path.mkdir()
    run_git(path, "init")
    run_git(path, "config", "user.name", "Test User")
    run_git(path, "config", "user.email", "test@example.com")
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    run_git(path, "add", "README.md")
    run_git(path, "commit", "-m", "initial")
    return path


def test_init_creates_database_and_repository(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert (home / ".gitpulse" / "data.db").exists()
    assert "初始化完成" in result.output


def test_worklog_cli_crud_with_isolated_database(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)
    runner.invoke(app, ["init"])

    add = runner.invoke(
        app,
        [
            "worklog",
            "add",
            "--yes",
            "--date",
            "2026-07-27",
            "--type",
            "debug",
            "--title",
            "排查 ADB 问题",
            "--result",
            "恢复",
            "--duration",
            "90",
            "--tag",
            "adb",
            "--json",
        ],
    )
    assert add.exit_code == 0
    worklog_id = json.loads(add.output)["id"]

    listed = runner.invoke(app, ["worklog", "list", "--json"])
    shown = runner.invoke(app, ["worklog", "show", worklog_id, "--json"])
    edited = runner.invoke(app, ["worklog", "edit", worklog_id, "--yes", "--duration", "120"])
    deleted = runner.invoke(app, ["worklog", "delete", worklog_id, "--yes"])

    assert worklog_id in listed.output
    assert json.loads(shown.output)["title"] == "排查 ADB 问题"
    assert edited.exit_code == 0
    assert deleted.exit_code == 0


def test_commit_save_and_history_cli(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = init_repo(tmp_path / "repo")
    (repo / "src.py").write_text("print('hello')\n", encoding="utf-8")
    run_git(repo, "add", "src.py")
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["commit", "--provider", "mock", "--save"])

    assert result.exit_code == 0
    assert "已保存工作记录" in result.output
    history = runner.invoke(app, ["history", "list", "--json"])
    assert history.exit_code == 0
    assert "record_" in history.output

