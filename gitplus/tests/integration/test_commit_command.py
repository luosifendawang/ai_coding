import json
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from gitplus.cli import app
from gitplus.config import AIConfig, GitPlusConfig

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


def test_commit_command_json_with_mock_provider(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    (repo / "src.py").write_text("print('hello')\n", encoding="utf-8")
    run_git(repo, "add", "src.py")
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["commit", "--provider", "mock", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ai_called"] is True
    assert payload["generation"]["candidates"]["concise"]["subject"]


def test_commit_command_empty_staged_diff_exits_nonzero(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["commit", "--provider", "mock"])

    assert result.exit_code == 1
    assert "当前暂存区没有代码变更" in result.output


def test_commit_command_security_block_does_not_leak_secret(tmp_path: Path, monkeypatch) -> None:
    repo = init_repo(tmp_path / "repo")
    secret = "sk-testexample1234567890abcdef"
    (repo / "config.py").write_text(f"API_KEY='{secret}'\n", encoding="utf-8")
    monkeypatch.setattr(
        "gitplus.cli.load_config",
        lambda: GitPlusConfig(ai=AIConfig(base_url="https://api.example.test/v1", is_local=False)),
    )
    run_git(repo, "add", "config.py")
    monkeypatch.chdir(repo)

    result = runner.invoke(app, ["commit", "--json"])

    assert result.exit_code == 1
    assert secret not in result.output
    payload = json.loads(result.output)
    assert payload["ai_called"] is False
    assert payload["security"]["block_remote_model"] is True
