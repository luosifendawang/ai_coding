from gitplus.config import SecurityConfig
from gitplus.models.risk import RiskCategory, RiskLevel, SecurityFinding
from gitplus.security.risk_classifier import RiskClassifier


def finding(level: RiskLevel) -> SecurityFinding:
    return SecurityFinding(
        id="id",
        rule_id="rule",
        rule_name="Rule",
        category=RiskCategory.SECRET,
        level=level,
        description="desc",
        blocks_remote_model=level in {RiskLevel.HIGH, RiskLevel.CRITICAL},
    )


def test_classifier_blocks_critical_and_high_by_default() -> None:
    classifier = RiskClassifier(SecurityConfig())

    assert classifier.should_block_remote([finding(RiskLevel.CRITICAL)], scan_completed=True) is True
    assert classifier.should_block_remote([finding(RiskLevel.HIGH)], scan_completed=True) is True
    assert classifier.should_block_remote([finding(RiskLevel.MEDIUM)], scan_completed=True) is False


def test_classifier_blocks_scan_failure_by_default() -> None:
    assert RiskClassifier(SecurityConfig()).should_block_remote([], scan_completed=False) is True


def test_classifier_summarizes_findings() -> None:
    summary = RiskClassifier(SecurityConfig()).summarize(
        [finding(RiskLevel.LOW), finding(RiskLevel.MEDIUM), finding(RiskLevel.HIGH)],
        files_scanned=2,
    )

    assert summary.low == 1
    assert summary.medium == 1
    assert summary.high == 1
    assert summary.total_findings == 3
    assert summary.files_scanned == 2

