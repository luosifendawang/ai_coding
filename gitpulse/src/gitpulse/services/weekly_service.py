"""Weekly report business service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

from gitpulse.ai.weekly_fallback import RuleBasedWeeklyGenerator
from gitpulse.config import WeeklyConfig
from gitpulse.exceptions import EmptyWeeklyDataError, SensitiveContentError, WeeklyExportError, WeeklyValidationError
from gitpulse.exporters import JsonWeeklyExporter, MarkdownWeeklyExporter, TextWeeklyExporter
from gitpulse.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitpulse.models.weekly import (
    WeeklyDateRange,
    WeeklyGenerationInput,
    WeeklyReport,
    WeeklyReportDraft,
    WeeklyUserNote,
)
from gitpulse.services.git_service import GitService
from gitpulse.services.security_service import SecurityService
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork
from gitpulse.weekly.collector import WeeklyDataCollector
from gitpulse.weekly.date_range import WeeklyDateRangeResolver
from gitpulse.weekly.fact_validator import WeeklyFactValidator


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
    ) -> None:
        self.database = database
        self.git_service = git_service or GitService()
        self.config = config or WeeklyConfig()
        self.generator = generator
        self.fallback_generator = fallback_generator or RuleBasedWeeklyGenerator(config=self.config)
        self.validator = validator or WeeklyFactValidator()
        self.security_service = security_service or SecurityService()

    def generate(self, request: WeeklyGenerateRequest, *, use_ai: bool = False) -> WeeklyReport:
        date_range = self._date_range(request)
        generation_input = self._collect(date_range, request)
        if not self._has_work(generation_input):
            raise EmptyWeeklyDataError(
                "本周期内没有可用于周报的 Commit、CommitRecord、Worklog 或用户补充。"
            )
        draft = self._generate_draft(generation_input, use_ai=use_ai)
        validation = self.validator.validate(draft, generation_input)
        if validation.status == "fail":
            reasons = "；".join(issue.reason for issue in validation.issues if issue.level == "error")
            raise WeeklyValidationError("周报事实校验失败：" + reasons)
        draft.source_coverage = validation.source_coverage
        report = self._to_report(draft, status="confirmed" if request.confirm else "draft")
        report.content_markdown = MarkdownWeeklyExporter().render(report)
        self._check_sensitive_report(report)
        return report

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
            except Exception:
                return self.fallback_generator.generate(generation_input)
        return self.fallback_generator.generate(generation_input)

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
