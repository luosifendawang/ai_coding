"""Risk classification helpers."""

from __future__ import annotations

from gitpulse.config import SecurityConfig
from gitpulse.models.risk import RiskLevel, SecurityFinding, SecurityScanSummary


class RiskClassifier:
    """Summarize findings and decide remote model blocking."""

    def __init__(self, config: SecurityConfig) -> None:
        self.config = config

    def should_block_remote(self, findings: list[SecurityFinding], *, scan_completed: bool) -> bool:
        if not scan_completed:
            return self.config.block_remote_on_scan_failure
        if any(finding.level == RiskLevel.CRITICAL for finding in findings):
            return True
        if self.config.block_remote_on_high_risk and any(finding.level == RiskLevel.HIGH for finding in findings):
            return True
        return bool(any(finding.blocks_remote_model for finding in findings if finding.level in {RiskLevel.HIGH, RiskLevel.CRITICAL}))

    def summarize(self, findings: list[SecurityFinding], *, files_scanned: int = 0) -> SecurityScanSummary:
        files_with_findings = {finding.file_path for finding in findings if finding.file_path}
        return SecurityScanSummary(
            low=sum(1 for finding in findings if finding.level == RiskLevel.LOW),
            medium=sum(1 for finding in findings if finding.level == RiskLevel.MEDIUM),
            high=sum(1 for finding in findings if finding.level == RiskLevel.HIGH),
            critical=sum(1 for finding in findings if finding.level == RiskLevel.CRITICAL),
            files_scanned=files_scanned,
            files_with_findings=len(files_with_findings),
            total_findings=len(findings),
        )

