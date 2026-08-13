import pytest

from gitplus.ai.mock_provider import MockLLMProvider
from gitplus.ai.topic_detector import TopicDetector
from gitplus.exceptions import TopicDetectionError
from gitplus.models.commit import CommitAIFile, CommitAIRequest, CommitRules


def request() -> CommitAIRequest:
    return CommitAIRequest(
        repository="repo",
        files=[
            CommitAIFile(path="src/usb.py", status="M"),
            CommitAIFile(path="src/logger.py", status="M"),
        ],
        sanitized_diff="+safe\n",
        stats={"files_changed": 2},
        commit_rules=CommitRules(),
    )


def test_topic_detector_detects_split_topics() -> None:
    response = """
{
  "should_split": true,
  "confidence": 0.87,
  "reason": "USB 修复与日志重构相互独立",
  "topics": [
    {"id": "t1", "title": "USB 修复", "type": "fix", "scope": "usb", "files": ["src/usb.py"], "suggested_subject": "fix(usb): 修复断开处理"},
    {"id": "t2", "title": "日志重构", "type": "refactor", "scope": "logger", "files": ["src/logger.py"], "suggested_subject": "refactor(logger): 统一日志格式"}
  ],
  "ambiguous_files": [],
  "needs_confirmation": []
}
"""
    result = TopicDetector(MockLLMProvider([response])).detect(request())

    assert result.should_split is True
    assert len(result.topics) == 2


def test_topic_detector_rejects_unknown_files() -> None:
    response = """
{
  "should_split": false,
  "confidence": 0.5,
  "reason": "单一主题",
  "topics": [{"id": "t1", "title": "x", "type": "fix", "files": ["missing.py"], "suggested_subject": "fix: 修复问题"}],
  "ambiguous_files": [],
  "needs_confirmation": []
}
"""

    with pytest.raises(TopicDetectionError):
        TopicDetector(MockLLMProvider([response])).detect(request())

