"""Security processing service."""

from __future__ import annotations

from gitplus.config import SecurityConfig
from gitplus.models.diff import DiffCollection
from gitplus.models.risk import SecurityScanResult
from gitplus.security.privacy_masker import PrivacyMasker
from gitplus.security.risk_classifier import RiskClassifier
from gitplus.security.rule_registry import RuleRegistry
from gitplus.security.secret_scanner import SecretScanner


class SecurityService:
    """Run scan, masking, summary, and remote-block decisions for a diff."""

    def __init__(self, config: SecurityConfig | None = None) -> None:
        self.config = config or SecurityConfig()
        self.rules = RuleRegistry(self.config).get_rules()
        self.scanner = SecretScanner(self.rules, self.config)
        self.masker = PrivacyMasker(self.config, self.rules)
        self.classifier = RiskClassifier(self.config)

    def process_diff(self, collection: DiffCollection) -> SecurityScanResult:
        if not self.config.enabled:
            summary = self.classifier.summarize([], files_scanned=len(collection.files))
            return SecurityScanResult(
                passed=True,
                scan_completed=True,
                block_remote_model=False,
                summary=summary,
                sanitized_diff="\n".join(file.patch for file in collection.files),
            )

        result = self.scanner.scan_collection(collection)
        if not result.scan_completed:
            return result
        masked = self.masker.mask_collection(collection, result.findings)
        result.sanitized_diff = masked.masked_text
        result.summary = self.classifier.summarize(result.findings, files_scanned=len(collection.files))
        # High-risk credentials are replaced with stable placeholders before the
        # diff is sent to an AI provider.  They should remain visible as findings
        # for the user, but must not make ordinary commit-message generation
        # unusable.  Only critical material (for example, a private key) stays
        # blocked because a lossy mask cannot provide a safe enough guarantee.
        result.block_remote_model = result.summary.critical > 0
        result.passed = result.summary.high == 0 and result.summary.critical == 0
        return result

