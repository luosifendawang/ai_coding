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
    run_git(path, "config", "user.name", "Test User")
    run_git(path, "config", "user.email", "test@example.com")
    run_git(path, "config", "core.quotepath", "false")
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    run_git(path, "add", "README.md")
    run_git(path, "commit", "-m", "initial")
    return path


def stage_file(repo: Path, relative_path: str, content: str) -> None:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run_git(repo, "add", relative_path)


def test_check_command_allows_safe_staged_diff(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    stage_file(repo, "src/app.py", "print('safe')\n")
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["check"])

    assert result.exit_code == 0
    assert "风险：0" in result.output or "发现风险" in result.output


def test_check_command_json_blocks_token_without_leaking_value(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    full_key = "sk-testexample1234567890abcdef"
    stage_file(repo, "config.py", f"API_KEY = '{full_key}'\n")
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["check", "--format", "json"])

    assert result.exit_code == 1
    assert full_key not in result.output
    payload = json.loads(result.output)
    assert payload["block_remote_model"] is True
    assert payload["summary"]["high"] == 1
    assert payload["findings"][0]["masked_value"] == "<API_KEY_1>"


def test_check_command_blocks_private_key(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    stage_file(
        repo,
        "private.pem",
        "-----BEGIN PRIVATE KEY-----\nTESTKEYDATA\n-----END PRIVATE KEY-----\n",
    )
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["check", "--format", "json"])

    assert result.exit_code == 1
    assert "TESTKEYDATA" not in result.output
    payload = json.loads(result.output)
    assert payload["summary"]["critical"] == 1


def test_check_command_allows_medium_and_low_after_masking(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    stage_file(repo, "app.py", 'SERVER="10.10.0.8"\nCACHE="/home/testuser/cache"\n')
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["check", "--format", "json", "--show-low-risk"])

    assert result.exit_code == 0
    assert "10.10.0.8" not in result.output
    assert "/home/testuser" not in result.output
    payload = json.loads(result.output)
    assert payload["block_remote_model"] is False
    assert payload["summary"]["medium"] == 1
    assert payload["summary"]["low"] == 1


def test_check_command_reports_empty_staged_diff(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["check"])

    assert result.exit_code == 0
    assert "当前 Diff 为空" in result.output
