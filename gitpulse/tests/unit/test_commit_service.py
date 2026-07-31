import subprocess
from pathlib import Path

from gitpulse.ai.mock_provider import MockLLMProvider
from gitpulse.config import AIConfig
from gitpulse.services.commit_service import CommitService


def run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def init_repo(path: Path) -> Path:
    path.mkdir()
    run_git(path, "init")
    run_git(path, "config", "user.name", "Test User")
    run_git(path, "config", "user.email", "test@example.com")
    return path


def commit_file(repo: Path) -> None:
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    run_git(repo, "add", "README.md")
    run_git(repo, "commit", "-m", "initial")


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
    "detailed": {"subject": "fix(usb): 修复设备断开后的连接资源清理问题", "body": ["清理断开后的连接对象", "补充断开状态处理"]}
  },
  "should_split": false,
  "split_confidence": 0.0,
  "split_suggestions": [],
  "evidence": [{"file": "src/usb.py", "reason": "增加断开处理"}],
  "needs_confirmation": []
}
"""


class RemoteMockProvider(MockLLMProvider):
    @property
    def is_local(self) -> bool:
        return False


def test_commit_service_generates_from_staged_diff(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo)
    (repo / "src").mkdir()
    (repo / "src/usb.py").write_text("def cleanup():\n    return True\n", encoding="utf-8")
    run_git(repo, "add", "src/usb.py")
    provider = RemoteMockProvider([RESPONSE])

    result = CommitService(path=repo, ai_config=AIConfig(provider="mock"), provider=provider).generate_commit_message()

    assert result.ai_called is True
    assert result.generation
    assert result.generation.type == "fix"
    assert provider.call_count == 1
    assert "def cleanup" in provider.requests[0].messages[1].content


def test_commit_service_blocks_remote_on_high_risk(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo)
    (repo / "config.py").write_text("API_KEY='sk-testexample1234567890abcdef'\n", encoding="utf-8")
    run_git(repo, "add", "config.py")
    provider = RemoteMockProvider([RESPONSE])

    result = CommitService(
        path=repo,
        ai_config=AIConfig(provider="openai-compatible", is_local=False),
        provider=provider,
    ).generate_commit_message()

    assert result.ai_called is False
    assert result.generation is None
    assert provider.call_count == 0
    assert result.security.block_remote_model is True


def test_commit_service_allows_local_with_sanitized_medium_risk(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    commit_file(repo)
    (repo / "app.py").write_text('SERVER="10.0.0.1"\n', encoding="utf-8")
    run_git(repo, "add", "app.py")
    provider = MockLLMProvider([RESPONSE])

    result = CommitService(path=repo, ai_config=AIConfig(provider="mock"), provider=provider).generate_commit_message()

    assert result.ai_called is True
    prompt = provider.requests[0].messages[1].content
    assert "10.0.0.1" not in prompt
    assert "<PRIVATE_IP_1>" in prompt
