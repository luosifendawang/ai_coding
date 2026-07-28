"""Rule-based security scanner."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from re import Match

from gitpulse.config import SecurityConfig
from gitpulse.models.diff import DiffCollection, FileDiff
from gitpulse.models.risk import RiskLevel, SecurityFinding, SecurityLocation, SecurityScanResult
from gitpulse.security.risk_classifier import RiskClassifier
from gitpulse.security.rule_registry import SecurityRule

LEVEL_ORDER = {
    RiskLevel.CRITICAL: 0,
    RiskLevel.HIGH: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.LOW: 3,
}


class SecretScanner:
    """Scan text and structured diffs with configured security rules."""

    def __init__(self, rules: list[SecurityRule], config: SecurityConfig) -> None:
        self.rules = rules
        self.config = config
        self._placeholder_by_value: dict[tuple[str, str], str] = {}
        self._counter_by_replacement: defaultdict[str, int] = defaultdict(int)

    def scan_text(self, text: str, *, file_path: str | None = None) -> list[SecurityFinding]:
        findings: list[SecurityFinding] = []
        seen_ranges: list[tuple[int, int]] = []
        for rule in self.rules:
            count = 0
            for match in rule.pattern.finditer(text):
                if count >= self.config.max_findings_per_rule:
                    break
                if not self._should_report(rule.id, match.group(0)):
                    continue
                if any(match.start() < end and match.end() > start for start, end in seen_ranges):
                    continue
                seen_ranges.append((match.start(), match.end()))
                count += 1
                findings.append(self._finding_from_match(rule, match, text, file_path=file_path))
        return self._sort_findings(findings)

    def scan_file_diff(self, file_diff: FileDiff) -> list[SecurityFinding]:
        if file_diff.is_binary or not file_diff.patch:
            return []
        return self.scan_text(file_diff.patch, file_path=file_diff.new_path)

    def scan_collection(self, collection: DiffCollection) -> SecurityScanResult:
        warnings: list[str] = []
        try:
            findings: list[SecurityFinding] = []
            for file in collection.files:
                findings.extend(self.scan_file_diff(file))
                if file.is_truncated:
                    warnings.append(f"文件 {file.new_path} 的 Diff 已截断，仅扫描可见内容。")
            findings = self._sort_findings(findings)
            classifier = RiskClassifier(self.config)
            summary = classifier.summarize(findings, files_scanned=len(collection.files))
            blocked = classifier.should_block_remote(findings, scan_completed=True)
            return SecurityScanResult(
                passed=summary.high == 0 and summary.critical == 0,
                scan_completed=True,
                block_remote_model=blocked,
                summary=summary,
                findings=findings,
                warnings=warnings,
            )
        except Exception as exc:
            classifier = RiskClassifier(self.config)
            return SecurityScanResult(
                passed=False,
                scan_completed=False,
                block_remote_model=classifier.should_block_remote([], scan_completed=False),
                summary=classifier.summarize([], files_scanned=0),
                errors=[f"安全扫描器执行异常：{type(exc).__name__}"],
            )

    def _finding_from_match(
        self,
        rule: SecurityRule,
        match: Match[str],
        text: str,
        *,
        file_path: str | None,
    ) -> SecurityFinding:
        line_number = text.count("\n", 0, match.start()) + 1
        line_start = text.rfind("\n", 0, match.start()) + 1
        column_start = match.start() - line_start + 1
        raw_value = match.group(0)
        placeholder = self._placeholder(rule.replacement, raw_value)
        finding_id = sha256(f"{rule.id}:{file_path}:{match.start()}:{match.end()}".encode()).hexdigest()[:16]
        return SecurityFinding(
            id=finding_id,
            rule_id=rule.id,
            rule_name=rule.name,
            category=rule.category,
            level=rule.level,
            file_path=file_path,
            line_number=line_number,
            column_start=column_start,
            column_end=column_start + len(raw_value),
            location=SecurityLocation(patch_line=line_number),
            description=rule.description,
            masked_value=placeholder,
            suggestion=rule.suggestion,
            confidence=rule.confidence,
            blocks_remote_model=rule.blocks_remote_model,
        )

    def _placeholder(self, replacement: str, raw_value: str) -> str:
        if replacement == "<PRIVATE_KEY>":
            return replacement
        key = (replacement, raw_value)
        if key not in self._placeholder_by_value:
            self._counter_by_replacement[replacement] += 1
            base = replacement.strip("<>")
            self._placeholder_by_value[key] = f"<{base}_{self._counter_by_replacement[replacement]}>"
        return self._placeholder_by_value[key]

    def _should_report(self, rule_id: str, value: str) -> bool:
        lowered = value.lower()
        if "os.getenv" in lowered or "${" in value:
            return False
        if rule_id == "api_key_in_env_name":
            assigned = value.rsplit("=", 1)[-1].rsplit(":", 1)[-1].strip().strip("\"'")
            return not assigned.replace("_", "").isalnum() or assigned != assigned.upper()
        if rule_id == "private_ipv4":
            return all(0 <= int(part) <= 255 for part in value.split("."))
        if rule_id == "database_url" and lowered.startswith("sqlite:"):
            return False
        return True

    def _sort_findings(self, findings: list[SecurityFinding]) -> list[SecurityFinding]:
        return sorted(
            findings,
            key=lambda item: (
                LEVEL_ORDER[item.level],
                item.file_path or "",
                item.line_number or 0,
                item.column_start or 0,
                item.rule_id,
            ),
        )
