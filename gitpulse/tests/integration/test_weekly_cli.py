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
    run_git(path, "commit", "-m", "feat(readme): 初始化项目说明")
    return path


def test_weekly_cli_generates_json_and_markdown_export(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)

    init = runner.invoke(app, ["init"])
    assert init.exit_code == 0

    result = runner.invoke(
        app,
        [
            "weekly",
            "--from",
            "2020-01-01",
            "--to",
            "2030-01-01",
            "--author",
            "test@example.com",
            "--risk",
            "发布前继续观察配置兼容性",
            "--plan",
            "补充飞书机器人发送",
            "--no-ai",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["completed"]
    assert payload["risks"][0]["sources"][0]["source_type"] == "user_note"

    (repo / "TODO.md").write_text("next\n", encoding="utf-8")
    output = tmp_path / "weekly.md"
    exported = runner.invoke(
        app,
        [
            "weekly",
            "--from",
            "2020-01-01",
            "--to",
            "2030-01-01",
            "--author",
            "test@example.com",
            "--no-ai",
            "--include-uncommitted",
            "--output",
            str(output),
        ],
    )

    assert exported.exit_code == 0, exported.output
    assert "周报已导出" in exported.output
    markdown = output.read_text(encoding="utf-8")
    assert "来源：commit:" in markdown
    assert "未跟踪文件待确认" in markdown
