"""Weekly report fact validation."""

from __future__ import annotations

from typing import Literal, cast

from gitpulse.models.weekly import (
    WeeklyGenerationInput,
    WeeklyReportDraft,
    WeeklyReportItem,
    WeeklyValidationIssue,
    WeeklyValidationResult,
)
from gitpulse.weekly.source_resolver import SourceResolver

FORBIDDEN_PHRASES = [
    "全面提升",
    "显著提高",
    "大幅优化",
    "性能提升 30%",
    "获得一致好评",
    "提前完成全部工作",
    "高质量完成",
    "优秀完成",
]


class WeeklyFactValidator:
    """Validate sources, confidence, and forbidden unsupported claims."""

    def validate(self, draft: WeeklyReportDraft, generation_input: WeeklyGenerationInput) -> WeeklyValidationResult:
        resolver = SourceResolver(generation_input)
        issues: list[WeeklyValidationIssue] = []
        formal_items = self._formal_items(draft)
        sourced = 0
        blocked: list[str] = []
        requires: list[str] = []
        for section, item in formal_items:
            if item.sources:
                source_issues = resolver.validate_sources(item.sources)
                if not source_issues:
                    sourced += 1
                for source_issue in source_issues:
                    issues.append(
                        WeeklyValidationIssue(
                            level="error",
                            issue_type="invalid_source",
                            section=section,
                            item_id=item.id,
                            content=item.content,
                            reason=source_issue.reason,
                        )
                    )
                    blocked.append(item.id)
            else:
                issues.append(
                    WeeklyValidationIssue(
                        level="error",
                        issue_type="missing_source",
                        section=section,
                        item_id=item.id,
                        content=item.content,
                        reason="正式内容缺少来源",
                    )
                )
                blocked.append(item.id)
            if item.confidence == "low":
                issues.append(
                    WeeklyValidationIssue(
                        level="error",
                        issue_type="low_confidence",
                        section=section,
                        item_id=item.id,
                        content=item.content,
                        reason="低可信内容不能直接进入正式周报",
                    )
                )
                blocked.append(item.id)
            if item.confidence == "medium" and not item.confirmed_by_user:
                issues.append(
                    WeeklyValidationIssue(
                        level="warning",
                        issue_type="needs_confirmation",
                        section=section,
                        item_id=item.id,
                        content=item.content,
                        reason="中可信内容需要用户确认",
                    )
                )
                requires.append(item.id)
            if any(phrase in item.content for phrase in FORBIDDEN_PHRASES):
                issues.append(
                    WeeklyValidationIssue(
                        level="error",
                        issue_type="unsupported_claim",
                        section=section,
                        item_id=item.id,
                        content=item.content,
                        reason="包含无证据的夸大或量化表达",
                    )
                )
                blocked.append(item.id)
        total = len(formal_items)
        coverage = 1.0 if total == 0 else sourced / total
        status = cast(
            Literal["pass", "warning", "fail"],
            "fail"
            if any(issue.level == "error" for issue in issues)
            else ("warning" if issues else "pass"),
        )
        return WeeklyValidationResult(
            status=status,
            source_coverage=coverage,
            issues=issues,
            blocked_item_ids=sorted(set(blocked)),
            requires_confirmation_ids=sorted(set(requires)),
        )

    def _formal_items(self, draft: WeeklyReportDraft) -> list[tuple[str, WeeklyReportItem]]:
        items: list[tuple[str, WeeklyReportItem]] = []
        for topic in draft.completed:
            items.extend(("completed", item) for item in topic.items)
        sections = [
            ("debugging", draft.debugging),
            ("testing", draft.testing),
            ("risks", draft.risks),
            ("next_week", draft.next_week),
        ]
        for name, section in sections:
            items.extend((name, item) for item in section)
        return items
