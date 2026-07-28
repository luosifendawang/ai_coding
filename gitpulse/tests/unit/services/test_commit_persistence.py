from pathlib import Path

from gitpulse.ai.mock_provider import MockLLMProvider
from gitpulse.config import AIConfig
from gitpulse.services.commit_record_service import CommitConfirmationRequest, CommitRecordService
from gitpulse.services.commit_service import CommitService
from gitpulse.storage.database import Database


RESPONSE = """
{
  "primary_purpose": "修复 USB 资源释放问题",
  "type": "fix",
  "scope": "usb",
  "subject": "fix(usb): 修复设备断开后的资源释放问题",
  "body": ["清理断开后的连接对象"],
  "confidence": "high",
  "candidates": {
    "concise": {"subject": "fix(usb): 修复资源释放问题", "body": []},
    "standard": {"subject": "fix(usb): 修复设备断开后的资源释放问题", "body": ["清理断开后的连接对象"]},
    "detailed": {"subject": "fix(usb): 修复设备断开后的连接资源清理问题", "body": ["清理断开后的连接对象"]}
  },
  "should_split": false,
  "split_confidence": 0.0,
  "split_suggestions": [],
  "evidence": [{"file": "src/usb.py", "reason": "增加断开处理"}],
  "needs_confirmation": []
}
"""


def run_git(repo: Path, *args: str) -> None:
    import subprocess

    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_commit_record_service_saves_confirmed_generation(tmp_path: Path) -> None:
    db = Database(tmp_path / "test.db")
    db.initialize()
    repo = tmp_path / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.name", "Test User")
    run_git(repo, "config", "user.email", "test@example.com")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    run_git(repo, "add", "README.md")
    run_git(repo, "commit", "-m", "initial")
    (repo / "src").mkdir()
    (repo / "src/usb.py").write_text("def cleanup():\n    return True\n", encoding="utf-8")
    run_git(repo, "add", "src/usb.py")

    result = CommitService(path=repo, ai_config=AIConfig(provider="mock"), provider=MockLLMProvider([RESPONSE])).generate_commit_message()
    candidate = result.generation.candidates["standard"]  # type: ignore[union-attr]
    saved = CommitRecordService(db).save_confirmed_record(
        CommitConfirmationRequest(
            result=result,
            selected_candidate="standard",
            final_subject=candidate.subject,
            final_body=candidate.body,
        )
    )

    assert saved.confirmed_by_user is True
    assert saved.commit_hash is None
    assert saved.subject == candidate.subject
    assert saved.files == ["src/usb.py"]
    db.dispose()

