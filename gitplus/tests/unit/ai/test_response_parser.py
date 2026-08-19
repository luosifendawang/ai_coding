import pytest

from gitplus.ai.response_parser import AIResponseParser
from gitplus.exceptions import AIResponseValidationError
from gitplus.models.commit import CommitGenerationResult

VALID = """
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


def test_parser_accepts_plain_json() -> None:
    result = AIResponseParser().parse(VALID, CommitGenerationResult)

    assert result.type == "fix"


def test_parser_extracts_markdown_json_block() -> None:
    result = AIResponseParser().parse(f"```json\n{VALID}\n```", CommitGenerationResult)

    assert result.scope == "usb"


def test_parser_repairs_trailing_comma() -> None:
    content = VALID.replace('"needs_confirmation": []', '"needs_confirmation": [],')

    result = AIResponseParser().parse(content, CommitGenerationResult)

    assert result.confidence == "high"


def test_parser_accepts_common_answer_envelope() -> None:
    result = AIResponseParser().parse(f'{{"answer": {VALID}}}', CommitGenerationResult)

    assert result.subject == "fix(usb): 修复设备断开后的资源释放问题"


def test_parser_normalizes_common_llm_schema_variants() -> None:
    content = """
{
  "primary_purpose": "添加演示脚本",
  "type": "feat",
  "scope": "gitplus",
  "subject": "feat(gitplus): 添加演示脚本",
  "body": [],
  "confidence": 0.9,
  "candidates": {
    "concise": "feat(gitplus): 添加演示脚本",
    "standard": "feat(gitplus): 添加演示脚本以打印 Hello World",
    "detailed": "feat(gitplus): 添加 demo.py 演示入口"
  },
  "evidence": ["gitplus/demo.py"],
  "needs_confirmation": []
}
"""

    result = AIResponseParser().parse(content, CommitGenerationResult)

    assert result.confidence == "high"
    assert result.candidates["concise"].subject == "feat(gitplus): 添加演示脚本"
    assert result.evidence[0].file == "gitplus/demo.py"


def test_parser_normalizes_string_bodies() -> None:
    content = VALID.replace(
        '"body": ["清理断开后的连接对象"]',
        '"body": "清理断开后的连接对象"',
        1,
    )
    content = content.replace(
        '"concise": {"subject": "fix(usb): 修复资源释放问题", "body": []}',
        '"concise": {"subject": "fix(usb): 修复资源释放问题", "body": ""}',
    )
    content = content.replace(
        '"standard": {"subject": "fix(usb): 修复设备断开后的资源释放问题", "body": ["清理断开后的连接对象"]}',
        '"standard": {"subject": "fix(usb): 修复设备断开后的资源释放问题", "body": "清理断开后的连接对象"}',
    )

    result = AIResponseParser().parse(content, CommitGenerationResult)

    assert result.body == ["清理断开后的连接对象"]
    assert result.candidates["concise"].body == []
    assert result.candidates["standard"].body == ["清理断开后的连接对象"]


def test_parser_downgrades_incomplete_split_suggestion() -> None:
    content = VALID.replace(
        '"should_split": false,\n  "split_confidence": 0.0,\n  "split_suggestions": []',
        '"should_split": true,\n  "split_confidence": 0.9,\n  "split_suggestions": []',
    )

    result = AIResponseParser().parse(content, CommitGenerationResult)

    assert result.should_split is False
    assert any("未提供至少两个" in warning for warning in result.validation_warnings)
    assert any("多个独立修改主题" in item for item in result.needs_confirmation)


def test_parser_rejects_empty_or_invalid_schema() -> None:
    with pytest.raises(AIResponseValidationError):
        AIResponseParser().parse("", CommitGenerationResult)

    with pytest.raises(AIResponseValidationError):
        AIResponseParser().parse('{"type": "unknown"}', CommitGenerationResult)


def test_parser_accepts_compact_commit_message_response() -> None:
    result = AIResponseParser().parse(
        '''{
          "type": "feature",
          "scope": null,
          "subject": "feat: add commit editor",
          "body": ["Open the generated message in Vim"],
          "primary_purpose": "Add a commit editor",
          "confidence": "medium"
        }''',
        CommitGenerationResult,
    )

    assert result.type == "feat"
    assert result.candidates["standard"].subject == "feat: add commit editor"
