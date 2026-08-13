from __future__ import annotations

import subprocess
from pathlib import Path

from typer.testing import CliRunner

from gitplus.cli import app
from gitplus.models.feishu import FeishuSendResponse
from gitplus.services.notification_service import NotificationService

runner = CliRunner()


class FakeClient:
    def send_payload(self, payload):
        return FeishuSendResponse(
            success=True, http_status=200, code=0, message="success", request_id="req"
        )

    def test_connection(self, *, send_message=False):
        return FeishuSendResponse(
            success=True, http_status=200, code=0, message="success"
        )


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


def prepare_confirmed_weekly(tmp_path: Path, monkeypatch) -> str:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)
    assert runner.invoke(app, ["init"]).exit_code == 0
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
            "--no-ai",
            "--confirm",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    import json

    return json.loads(result.output)["id"]


def test_notify_weekly_preview_and_send(tmp_path: Path, monkeypatch) -> None:
    report_id = prepare_confirmed_weekly(tmp_path, monkeypatch)
    monkeypatch.setattr(NotificationService, "_client", lambda self: FakeClient())

    preview = runner.invoke(app, ["notify", "weekly", report_id, "--preview"])
    sent = runner.invoke(app, ["notify", "weekly", report_id, "--yes", "--json"])

    assert preview.exit_code == 0, preview.output
    assert "飞书通知预览" in preview.output
    assert sent.exit_code == 0, sent.output
    assert '"status": "sent"' in sent.output


def test_weekly_send_feishu_requires_confirm(tmp_path: Path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    repo = init_repo(tmp_path / "repo")
    monkeypatch.chdir(repo)
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["weekly", "--send-feishu", "--no-ai"])

    assert result.exit_code != 0
    assert "--send-feishu" in result.output
