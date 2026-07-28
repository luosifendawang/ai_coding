from gitpulse.ai.commit_validator import CommitMessageValidator
from gitpulse.models.commit import CommitCandidate, CommitGenerationResult, CommitRules


def make_result(subject: str) -> CommitGenerationResult:
    return CommitGenerationResult(
        primary_purpose="修复 USB 问题",
        type="fix",
        scope="usb",
        subject=subject,
        body=["清理连接对象"],
        confidence="high",
        candidates={
            "concise": CommitCandidate(subject="fix(usb): 修复资源释放问题"),
            "standard": CommitCandidate(subject="fix(usb): 修复设备断开后的资源释放问题", body=["清理连接对象"]),
            "detailed": CommitCandidate(subject="fix(usb): 修复设备断开后的连接清理问题", body=["清理连接对象"]),
        },
        evidence=[{"file": "src/usb.py", "reason": "增加连接清理"}],
    )


def test_validator_accepts_conventional_subject() -> None:
    warnings = CommitMessageValidator().validate_subject("fix(usb): 修复设备断开后的资源释放问题", CommitRules())

    assert warnings == []


def test_validator_flags_low_quality_subject() -> None:
    warnings = CommitMessageValidator().validate_subject("chore: update code", CommitRules())

    assert warnings


def test_validator_checks_evidence_files() -> None:
    warnings = CommitMessageValidator().validate_result(make_result("fix(usb): 修复资源释放问题"), CommitRules(), valid_files={"src/main.py"})

    assert any("Evidence" in warning for warning in warnings)

