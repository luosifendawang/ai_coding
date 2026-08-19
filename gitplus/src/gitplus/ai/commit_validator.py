"""Commit message quality validation."""

from __future__ import annotations

import re

from gitplus.models.commit import CommitGenerationResult, CommitRules

LOW_QUALITY_PHRASES = [
    "update code",
    "fix bug",
    "修改代码",
    "更新文件",
    "修改部分文件",
    "调整部分逻辑",
    "全面提升",
    "显著优化",
    "大幅提高",
]


class CommitMessageValidator:
    """Validate Conventional Commit shape and basic factual quality."""

    def validate_subject(self, subject: str, rules: CommitRules) -> list[str]:
        warnings: list[str] = []
        if not re.match(r"^[a-z]+(?:\([A-Za-z0-9_-]+\))?: .+", subject):
            warnings.append("Subject 不符合 Conventional Commits 格式。")
        commit_type = subject.split("(", 1)[0].split(":", 1)[0]
        if commit_type not in rules.allowed_types:
            warnings.append(f"Commit Type 不在允许列表中：{commit_type}")
        if len(subject) > rules.subject_max_length:
            warnings.append("Subject 超过配置的最大长度。")
        if "\n" in subject:
            warnings.append("Subject 不应包含换行。")
        if subject.endswith((".", "。")):
            warnings.append("Subject 不应以句号结尾。")
        lowered = subject.lower()
        if any(phrase in lowered or phrase in subject for phrase in LOW_QUALITY_PHRASES):
            warnings.append("Subject 包含低质量或无证据表达。")
        return warnings

    def validate_result(
        self,
        result: CommitGenerationResult,
        rules: CommitRules,
        *,
        valid_files: set[str],
    ) -> list[str]:
        warnings = self.validate_subject(result.subject, rules)
        candidate_subjects = [candidate.subject for candidate in result.candidates.values()]
        if len(set(candidate_subjects)) < len(candidate_subjects) and any(
            subject != result.subject for subject in candidate_subjects
        ):
            warnings.append("三个候选版本不应完全重复。")
        for evidence in result.evidence:
            if evidence.file not in valid_files:
                warnings.append(f"Evidence 引用了不存在的文件：{evidence.file}")
        for suggestion in result.split_suggestions:
            for file in suggestion.files:
                if file not in valid_files:
                    warnings.append(f"拆分建议引用了不存在的文件：{file}")
        for item in result.body:
            if item.strip() == result.subject.strip():
                warnings.append("Body 不应重复 Subject。")
        return warnings

