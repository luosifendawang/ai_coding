import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from gitpulse.cli import app

runner = CliRunner()


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def init_repo(path: Path) -> Path:
    path.mkdir()
    run_git(path, "init")
    run_git(path, "config", "user.name", "Demo User")
    run_git(path, "config", "user.email", "demo@example.test")
    (path / "README.md").write_text("demo\n", encoding="utf-8")
    run_git(path, "add", "README.md")
    run_git(path, "commit", "-m", "docs(readme): 初始化演示项目")
    return path


def test_full_local_commit_worklog_weekly_flow(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)

    (repo / "device.py").write_text("def close():\n    return True\n", encoding="utf-8")
    run_git(repo, "add", "device.py")

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["doctor", "--json"]).exit_code == 0
    assert runner.invoke(app, ["check", "--format", "json"]).exit_code == 0
    commit = runner.invoke(app, ["commit", "--provider", "mock", "--save", "--json"])
    worklog = runner.invoke(
        app,
        [
            "worklog",
            "add",
            "--yes",
            "--date",
            "2026-07-28",
            "--type",
            "debug",
            "--title",
            "排查 ADB 设备离线问题",
            "--result",
            "重新授权后恢复",
            "--json",
        ],
    )
    weekly = runner.invoke(
        app,
        [
            "weekly",
            "--from",
            "2020-01-01",
            "--to",
            "2030-01-01",
            "--author",
            "demo@example.test",
            "--risk",
            "多设备场景仍需回归",
            "--plan",
            "补充 USB 模块单元测试",
            "--no-ai",
            "--confirm",
            "--json",
        ],
    )

    assert commit.exit_code == 0, commit.output
    assert worklog.exit_code == 0, worklog.output
    assert weekly.exit_code == 0, weekly.output
    payload = json.loads(weekly.output)
    assert payload["status"] == "confirmed"
    assert payload["source_coverage"] == 1.0
    assert payload["completed"]


def test_security_block_flow_does_not_call_remote_ai(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)
    (repo / "secret.py").write_text('API_KEY = "sk-testexample1234567890abcdef"\n', encoding="utf-8")
    run_git(repo, "add", "secret.py")

    result = runner.invoke(app, ["commit", "--provider", "openai-compatible", "--json"])

    assert result.exit_code == 1
    assert "sk-testexample1234567890abcdef" not in result.output
