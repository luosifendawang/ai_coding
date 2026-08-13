"""Weekly report business service."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from gitplus.ai.weekly_fallback import RuleBasedWeeklyGenerator
from gitplus.config import WeeklyConfig
from gitplus.exceptions import (
    EmptyWeeklyDataError,
    SensitiveContentError,
    WeeklyExportError,
    WeeklyValidationError,
)
from gitplus.exporters import (
    JsonWeeklyExporter,
    MarkdownWeeklyExporter,
    TextWeeklyExporter,
)
from gitplus.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitplus.models.weekly import (
    WeeklyDateRange,
    WeeklyGenerationInput,
    WeeklyReport,
    WeeklyReportDraft,
    WeeklyUserNote,
)
from gitplus.services.git_service import GitService
from gitplus.services.security_service import SecurityService
from gitplus.storage.database import Database
from gitplus.storage.unit_of_work import UnitOfWork
from gitplus.weekly.cleaner import WeeklyDataCleaner
from gitplus.weekly.collector import WeeklyDataCollector
from gitplus.weekly.date_range import WeeklyDateRangeResolver
from gitplus.weekly.fact_validator import WeeklyFactValidator


class WeeklyDraftGenerator(Protocol):
    def generate(self, generation_input: WeeklyGenerationInput) -> WeeklyReportDraft:
        """Generate a weekly report draft."""


@dataclass(frozen=True)
class WeeklyGenerateRequest:
    range_kind: Literal["current", "last", "custom"] = "current"
    date_from: date | None = None
    date_to: date | None = None
    authors: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    plans: list[str] = field(default_factory=list)
    include_uncommitted: bool = False
    confirm: bool = False


@dataclass(frozen=True)
class WeeklyGenerationOutcome:
    report: WeeklyReport
    warnings: list[str] = field(default_factory=list)


class WeeklyService:
    """Generate, validate, persist, and export weekly reports."""

    def __init__(
        self,
        database: Database,
        *,
        git_service: GitService | None = None,
        config: WeeklyConfig | None = None,
        generator: WeeklyDraftGenerator | None = None,
        fallback_generator: RuleBasedWeeklyGenerator | None = None,
        validator: WeeklyFactValidator | None = None,
        security_service: SecurityService | None = None,
        cleaner: WeeklyDataCleaner | None = None,
    ) -> None:
        self.database = database
        self.git_service = git_service or GitService()
        self.config = config or WeeklyConfig()
        self.generator = generator
        self.fallback_generator = fallback_generator or RuleBasedWeeklyGenerator(config=self.config)
        self.validator = validator or WeeklyFactValidator()
        self.security_service = security_service or SecurityService()
        self.cleaner = cleaner or WeeklyDataCleaner()

    def generate(self, request: WeeklyGenerateRequest, *, use_ai: bool = False) -> WeeklyReport:
        generation_input = self.collect(request)
        return self.generate_from_input(
            generation_input,
            use_ai=use_ai,
            confirm=request.confirm,
        ).report

    def collect(self, request: WeeklyGenerateRequest) -> WeeklyGenerationInput:
        date_range = self.resolve_date_range(request)
        return self._collect(date_range, request)

    def resolve_date_range(self, request: WeeklyGenerateRequest) -> WeeklyDateRange:
        return self._date_range(request)

    def generate_from_input(
        self,
        generation_input: WeeklyGenerationInput,
        *,
        use_ai: bool = False,
        confirm: bool = False,
    ) -> WeeklyGenerationOutcome:
        generation_input = self._clean_generation_input(generation_input)
        if not self._has_work(generation_input):
            raise EmptyWeeklyDataError(
                "本周期内没有可用于周报的 Commit、CommitRecord、Worklog 或用户补充。"
            )
        warnings: list[str] = []
        draft = None
        if use_ai and self.generator:
            sanitized_input, blocked = self._sanitized_input(generation_input)
            if blocked:
                warnings.append(
                    "检测到高风险敏感信息，未调用 AI，已使用规则模式生成。"
                )
            elif sanitized_input is not None:
                try:
                    draft = self.generator.generate(sanitized_input)
                except Exception:  # noqa: BLE001 - provider boundary must fall back
                    warnings.append("AI 整理失败，已自动回退到规则模式。")
        elif use_ai:
            warnings.append("AI 周报生成器未配置，已使用规则模式生成。")
        if draft is None:
            draft = self.fallback_generator.generate(generation_input)
        self._exclude_low_confidence(draft)
        validation = self.validator.validate(draft, generation_input)
        if validation.status == "fail":
            if use_ai and draft.generator != "rule_based":
                warnings.append("AI 内容未通过来源校验，已使用规则模式重新生成。")
                draft = self.fallback_generator.generate(generation_input)
                self._exclude_low_confidence(draft)
                validation = self.validator.validate(draft, generation_input)
            if validation.status == "fail":
                reasons = "；".join(
                    issue.reason
                    for issue in validation.issues
                    if issue.level == "error"
                )
                raise WeeklyValidationError("周报事实校验失败：" + reasons)
        draft.source_coverage = validation.source_coverage
        report = self._to_report(
            draft, status="confirmed" if confirm else "draft"
        )
        report.content_markdown = MarkdownWeeklyExporter().render(report)
        self._check_sensitive_report(report)
        return WeeklyGenerationOutcome(report=report, warnings=warnings)

    def save(self, report: WeeklyReport, *, repository_id: str | None = None) -> WeeklyReport:
        with UnitOfWork(self.database) as uow:
            return uow.weekly_reports.create(report, repository_id=repository_id)

    def export(self, report: WeeklyReport, output_format: str, output_path: Path, *, overwrite: bool = False) -> Path:
        if output_format == "markdown":
            return MarkdownWeeklyExporter().export(report, output_path, overwrite=overwrite)
        if output_format == "text":
            return TextWeeklyExporter().export(report, output_path, overwrite=overwrite)
        if output_format == "json":
            return JsonWeeklyExporter().export(report, output_path, overwrite=overwrite)
        raise WeeklyExportError("--format 仅支持 markdown、text 或 json")

    def render(self, report: WeeklyReport, output_format: str) -> str:
        if output_format == "markdown":
            return MarkdownWeeklyExporter().render(report)
        if output_format == "text":
            return TextWeeklyExporter().render(report)
        if output_format == "json":
            return JsonWeeklyExporter().render(report)
        raise WeeklyExportError("--format 仅支持 markdown、text 或 json")

    def validate_safe_report(self, report: WeeklyReport) -> None:
        self._check_sensitive_report(report)

    def _date_range(self, request: WeeklyGenerateRequest) -> WeeklyDateRange:
        resolver = WeeklyDateRangeResolver(self.config)
        if request.range_kind == "last":
            return resolver.last_week()
        if request.range_kind == "custom":
            if request.date_from is None or request.date_to is None:
                raise WeeklyValidationError("自定义周报日期需要同时提供 --from 和 --to。")
            return resolver.custom(request.date_from, request.date_to)
        return resolver.current_week()

    def _collect(self, date_range: WeeklyDateRange, request: WeeklyGenerateRequest) -> WeeklyGenerationInput:
        collector = WeeklyDataCollector(database=self.database, git_service=self.git_service, config=self.config)
        collected = collector.collect(
            date_range,
            authors=request.authors or None,
            include_uncommitted=request.include_uncommitted,
        )
        return collected.model_copy(
            update={
                "risks": [
                    WeeklyUserNote(id=f"risk_{index}", note_type="risk", content=value)
                    for index, value in enumerate(request.risks, start=1)
                ],
                "next_week_plans": [
                    WeeklyUserNote(id=f"plan_{index}", note_type="plan", content=value)
                    for index, value in enumerate(request.plans, start=1)
                ],
            }
        )

    def _generate_draft(self, generation_input: WeeklyGenerationInput, *, use_ai: bool) -> WeeklyReportDraft:
        if use_ai and self.generator:
            try:
                return self.generator.generate(generation_input)
            except Exception:  # noqa: BLE001 - preserve rule fallback for providers
                return self.fallback_generator.generate(generation_input)
        return self.fallback_generator.generate(generation_input)

    def _clean_generation_input(
        self, generation_input: WeeklyGenerationInput
    ) -> WeeklyGenerationInput:
        accepted = self.cleaner.accepted_source_labels(generation_input)
        commits = [
            item
            for item in generation_input.commits
            if f"commit:{item.commit_hash[:8]}" in accepted
        ]
        records = [
            item
            for item in generation_input.commit_records
            if f"record:{item.id}" in accepted
        ]
        worklogs = [
            item
            for item in generation_input.worklogs
            if f"worklog:{item.id}" in accepted
        ]
        uncommitted = [
            item
            for item in generation_input.uncommitted_changes
            if f"uncommitted:{item.repository_id}:{item.summary}" in accepted
        ]
        user_notes = [
            item
            for item in generation_input.user_notes
            if f"user_note:{item.id}" in accepted
        ]
        return generation_input.model_copy(
            update={
                "commits": commits,
                "commit_records": records,
                "worklogs": worklogs,
                "uncommitted_changes": uncommitted,
                "user_notes": user_notes,
            }
        )

    def _sanitized_input(
        self, generation_input: WeeklyGenerationInput
    ) -> tuple[WeeklyGenerationInput | None, bool]:
        content = json.dumps(
            generation_input.model_dump(mode="json"), ensure_ascii=False
        )
        result = self.security_service.process_diff(
            DiffCollection(
                source=DiffSource.STAGED,
                files=[
                    FileDiff.with_extension(
                        new_path="weekly-input.json",
                        status=FileChangeStatus.MODIFIED,
                        patch=content,
                    )
                ],
            )
        )
        if not result.scan_completed or result.summary.high or result.summary.critical:
            return None, True
        try:
            return (
                WeeklyGenerationInput.model_validate_json(
                    result.sanitized_diff
                ),
                False,
            )
        except ValueError:
            return None, True

    def _exclude_low_confidence(self, draft: WeeklyReportDraft) -> None:
        for topic in draft.completed:
            topic.items = [
                item for item in topic.items if item.confidence != "low"
            ]
        draft.completed = [topic for topic in draft.completed if topic.items]
        draft.debugging = [
            item for item in draft.debugging if item.confidence != "low"
        ]
        draft.testing = [
            item for item in draft.testing if item.confidence != "low"
        ]
        draft.risks = [
            item for item in draft.risks if item.confidence != "low"
        ]
        draft.next_week = [
            item for item in draft.next_week if item.confidence != "low"
        ]
        draft.needs_confirmation = [
            item
            for item in draft.needs_confirmation
            if item.confidence != "low"
        ]

    def _to_report(self, draft: WeeklyReportDraft, *, status: str) -> WeeklyReport:
        current = datetime.now(timezone.utc)
        return WeeklyReport(
            id=draft.id,
            title=draft.title,
            date_range=draft.date_range,
            completed=draft.completed,
            debugging=draft.debugging,
            testing=draft.testing,
            risks=draft.risks,
            next_week=draft.next_week,
            source_coverage=draft.source_coverage,
            status=status,
            content_markdown="",
            generator=draft.generator,
            created_at=draft.created_at,
            updated_at=current,
            confirmed_at=current if status == "confirmed" else None,
        )

    def _has_work(self, generation_input: WeeklyGenerationInput) -> bool:
        return bool(
            generation_input.commits
            or generation_input.commit_records
            or generation_input.worklogs
            or generation_input.uncommitted_changes
            or generation_input.user_notes
            or generation_input.risks
            or generation_input.next_week_plans
        )

    def _check_sensitive_report(self, report: WeeklyReport) -> None:
        collection = DiffCollection(
            source=DiffSource.STAGED,
            files=[
                FileDiff.with_extension(
                    new_path="weekly-report.md",
                    status=FileChangeStatus.MODIFIED,
                    patch=report.content_markdown,
                )
            ],
        )
        result = self.security_service.process_diff(collection)
        if result.summary.high or result.summary.critical:
            raise SensitiveContentError("周报包含高风险敏感信息，请移除后重试。")
