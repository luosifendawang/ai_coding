"""Web orchestration for weekly preview, editing, and export."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from gitpulse.exceptions import (
    EmptyWeeklyDataError,
    RepositoryOperationError,
    SensitiveContentError,
    WeeklyError,
)
from gitpulse.exporters.markdown import MarkdownWeeklyExporter
from gitpulse.models.source import WeeklySourceReference
from gitpulse.models.weekly import (
    WeeklyGenerationInput,
    WeeklyReport,
    WeeklyReportItem,
    WeeklyReportTopic,
    WeeklyUserNote,
)
from gitpulse.services.weekly_service import (
    WeeklyGenerateRequest,
    WeeklyService,
)
from gitpulse.storage.unit_of_work import UnitOfWork
from gitpulse.web.schemas.weekly import (
    WeeklyGenerateWebRequest,
    WeeklyItemEdit,
    WeeklyRangeRequest,
    WeeklyReportEdit,
)
from gitpulse.web.services.repository_context_service import RepositoryContextService
from gitpulse.web.services.repository_web_service import RepositoryWebError
from gitpulse.weekly.cleaner import WeeklyCleanupResult, WeeklyDataCleaner


class WeeklyWebService:
    def __init__(
        self,
        weekly_service: WeeklyService,
        repository_context: RepositoryContextService,
        cleaner: WeeklyDataCleaner | None = None,
    ) -> None:
        self.weekly_service = weekly_service
        self.repository_context = repository_context
        self.cleaner = cleaner or WeeklyDataCleaner()

    def preview(self, payload: WeeklyRangeRequest) -> dict[str, object]:
        generation_input = self._collect(payload)
        cleanup = self.cleaner.clean(generation_input)
        return self._preview_payload(generation_input, cleanup)

    def generate(
        self, payload: WeeklyGenerateWebRequest
    ) -> dict[str, object]:
        repository = self.repository_context.ensure_record()
        generation_input = self._collect(payload)
        generation_input = self._exclude(
            generation_input, payload.excluded_source_ids
        )
        if payload.user_context.strip():
            generation_input = generation_input.model_copy(
                update={
                    "user_notes": [
                        *generation_input.user_notes,
                        WeeklyUserNote(
                            id=f"manual_{uuid4().hex[:12]}",
                            note_type="context",
                            content=payload.user_context.strip(),
                            confirmed_by_user=True,
                        ),
                    ]
                }
            )
        try:
            outcome = self.weekly_service.generate_from_input(
                generation_input, use_ai=payload.use_ai
            )
            report = self.weekly_service.save(
                outcome.report, repository_id=repository.id
            )
        except EmptyWeeklyDataError as exc:
            raise RepositoryWebError("weekly_no_data", str(exc), 422) from exc
        except (WeeklyError, SensitiveContentError) as exc:
            raise RepositoryWebError(
                "weekly_generation_failed", str(exc), 422
            ) from exc
        return {
            "report": self._report_payload(report),
            "warnings": outcome.warnings,
        }

    def list_reports(
        self, *, status: str | None, page: int, page_size: int
    ) -> dict[str, object]:
        repository = self.repository_context.ensure_record()
        with UnitOfWork(self.weekly_service.database) as uow:
            reports = uow.weekly_reports.list(
                repository_id=repository.id,
                statuses=[status] if status else None,
                limit=page_size + 1,
                offset=(page - 1) * page_size,
            )
        has_next = len(reports) > page_size
        reports = reports[:page_size]
        return {
            "items": [self._report_summary(report) for report in reports],
            "page": page,
            "page_size": page_size,
            "has_next": has_next,
        }

    def get(self, report_id: str) -> dict[str, object]:
        return self._report_payload(self._owned(report_id))

    def update(
        self,
        report_id: str,
        *,
        expected_version: int,
        edited: WeeklyReportEdit,
    ) -> dict[str, object]:
        current = self._owned(report_id)
        self._assert_version(current, expected_version)
        updated = self._build_edited_report(current, edited)
        self._validate_safe(updated)
        try:
            with UnitOfWork(self.weekly_service.database) as uow:
                saved = uow.weekly_reports.update(
                    updated, expected_version=expected_version
                )
        except RepositoryOperationError as exc:
            raise RepositoryWebError(
                "weekly_version_conflict",
                "周报已被其他操作修改，请重新加载。",
                409,
            ) from exc
        return self._report_payload(saved)

    def delete(
        self, report_id: str, *, expected_version: int, confirmed: bool
    ) -> None:
        current = self._owned(report_id)
        self._assert_version(current, expected_version)
        if not confirmed:
            raise RepositoryWebError(
                "delete_confirmation_required", "删除周报前需要明确确认。"
            )
        with UnitOfWork(self.weekly_service.database) as uow:
            uow.weekly_reports.delete(
                report_id, expected_version=expected_version
            )

    def confirm(
        self, report_id: str, *, expected_version: int
    ) -> dict[str, object]:
        current = self._owned(report_id)
        self._assert_version(current, expected_version)
        if current.status != "draft":
            raise RepositoryWebError(
                "weekly_state_invalid", "只有草稿可以确认。", 409
            )
        items = self._items(current)
        if any(not item.sources for item in items):
            raise RepositoryWebError(
                "weekly_sources_incomplete",
                "正式周报中的每个工作项都必须具有有效来源。",
                422,
            )
        if any(item.confidence == "low" for item in items):
            raise RepositoryWebError(
                "weekly_low_confidence",
                "低可信内容不能进入正式周报。",
                422,
            )
        if any(
            item.confidence == "medium" and not item.confirmed_by_user
            for item in items
        ):
            raise RepositoryWebError(
                "weekly_confirmation_required",
                "仍有中可信工作项需要用户确认。",
                422,
            )
        current.status = "confirmed"
        current.confirmed_at = datetime.now(timezone.utc)
        current.updated_at = current.confirmed_at
        current.version += 1
        current.source_coverage = 1.0
        current.content_markdown = MarkdownWeeklyExporter().render(current)
        self._validate_safe(current)
        with UnitOfWork(self.weekly_service.database) as uow:
            saved = uow.weekly_reports.update(
                current, expected_version=expected_version
            )
        return self._report_payload(saved)

    def reopen(
        self, report_id: str, *, expected_version: int
    ) -> dict[str, object]:
        current = self._owned(report_id)
        self._assert_version(current, expected_version)
        if current.status not in {"confirmed", "exported"}:
            raise RepositoryWebError(
                "weekly_state_invalid",
                "只有已确认或已导出的周报可以重新打开。",
                409,
            )
        current.status = "draft"
        current.confirmed_at = None
        current.updated_at = datetime.now(timezone.utc)
        current.version += 1
        current.content_markdown = MarkdownWeeklyExporter().render(current)
        with UnitOfWork(self.weekly_service.database) as uow:
            saved = uow.weekly_reports.update(
                current, expected_version=expected_version
            )
        return self._report_payload(saved)

    def export(
        self, report_id: str, output_format: str
    ) -> tuple[bytes, str, str]:
        report = self._owned(report_id)
        if report.status == "confirmed":
            expected_version = report.version
            report.status = "exported"
            report.version += 1
            report.updated_at = datetime.now(timezone.utc)
            report.content_markdown = MarkdownWeeklyExporter().render(report)
            with UnitOfWork(self.weekly_service.database) as uow:
                report = uow.weekly_reports.update(
                    report, expected_version=expected_version
                )
        self._validate_safe(report)
        try:
            content = self.weekly_service.render(report, output_format)
        except WeeklyError as exc:
            raise RepositoryWebError(
                "weekly_export_failed", str(exc), 422
            ) from exc
        extensions = {"markdown": "md", "text": "txt", "json": "json"}
        media_types = {
            "markdown": "text/markdown; charset=utf-8",
            "text": "text/plain; charset=utf-8",
            "json": "application/json; charset=utf-8",
        }
        extension = extensions[output_format]
        filename = (
            f"gitpulse-weekly-{report.date_range.date_from.isoformat()}-"
            f"{report.date_range.date_to.isoformat()}.{extension}"
        )
        return content.encode("utf-8"), media_types[output_format], filename

    def _collect(
        self, payload: WeeklyRangeRequest
    ) -> WeeklyGenerationInput:
        self.repository_context.ensure_record()
        try:
            return self.weekly_service.collect(
                WeeklyGenerateRequest(
                    range_kind=payload.range_kind,
                    date_from=payload.date_from,
                    date_to=payload.date_to,
                    authors=payload.authors,
                    include_uncommitted=payload.include_uncommitted,
                )
            )
        except WeeklyError as exc:
            raise RepositoryWebError(
                "weekly_collection_failed", str(exc), 422
            ) from exc

    def _exclude(
        self,
        generation_input: WeeklyGenerationInput,
        excluded_ids: list[str],
    ) -> WeeklyGenerationInput:
        excluded = set(excluded_ids)
        if not excluded:
            return generation_input
        cleanup = self.cleaner.clean(generation_input)
        excluded_labels: set[str] = set()
        for item in [
            *cleanup.items,
            *cleanup.template_items,
            *cleanup.low_information_items,
        ]:
            if item.id in excluded or any(
                source.label in excluded or source.source_id in excluded
                for source in item.sources
            ):
                excluded_labels.update(source.label for source in item.sources)
        return generation_input.model_copy(
            update={
                "commits": [
                    item
                    for item in generation_input.commits
                    if f"commit:{item.commit_hash[:8]}" not in excluded_labels
                ],
                "commit_records": [
                    item
                    for item in generation_input.commit_records
                    if f"record:{item.id}" not in excluded_labels
                ],
                "worklogs": [
                    item
                    for item in generation_input.worklogs
                    if f"worklog:{item.id}" not in excluded_labels
                ],
                "uncommitted_changes": [
                    item
                    for item in generation_input.uncommitted_changes
                    if (
                        f"uncommitted:{item.repository_id}:{item.summary}"
                        not in excluded_labels
                    )
                ],
            }
        )

    def _preview_payload(
        self,
        generation_input: WeeklyGenerationInput,
        cleanup: WeeklyCleanupResult,
    ) -> dict[str, object]:
        items = [self._raw_item_payload(item) for item in cleanup.items]
        sourced = sum(bool(item["sources"]) for item in items)
        total = len(items)
        return {
            "date_range": generation_input.date_range.model_dump(mode="json"),
            "authors": sorted(
                {item.author_email for item in generation_input.commits}
            ),
            "items": items,
            "counts": {
                "commits": len(generation_input.commits),
                "commit_records": len(generation_input.commit_records),
                "worklogs": len(generation_input.worklogs),
                "uncommitted": len(generation_input.uncommitted_changes),
                "usable": total,
            },
            "source_coverage": 1.0 if total == 0 else sourced / total,
            "duplicates": [
                group.model_dump(mode="json")
                for group in cleanup.merged_groups
            ],
            "low_information": [
                self._raw_item_payload(item)
                for item in cleanup.low_information_items
            ],
            "templates": [
                self._raw_item_payload(item)
                for item in cleanup.template_items
            ],
        }

    def _raw_item_payload(self, item) -> dict[str, object]:  # type: ignore[no-untyped-def]
        return {
            "id": item.id,
            "source_type": item.source_type,
            "title": item.title,
            "description": item.description,
            "result": item.result,
            "repository": item.repository_name,
            "occurred_at": (
                item.occurred_at.isoformat() if item.occurred_at else None
            ),
            "files": item.files[:20],
            "sources": [
                source.model_dump(mode="json") | {"label": source.label}
                for source in item.sources
            ],
        }

    def _owned(self, report_id: str) -> WeeklyReport:
        repository = self.repository_context.ensure_record()
        with UnitOfWork(self.weekly_service.database) as uow:
            report = uow.weekly_reports.get_by_id_for_repository(
                report_id, repository.id
            )
        if report is None:
            raise RepositoryWebError(
                "weekly_not_found", "未找到周报。", 404
            )
        return report

    def _assert_version(
        self, report: WeeklyReport, expected_version: int
    ) -> None:
        if report.version != expected_version:
            raise RepositoryWebError(
                "weekly_version_conflict",
                "周报已被其他操作修改，请重新加载。",
                409,
            )

    def _build_edited_report(
        self, current: WeeklyReport, edited: WeeklyReportEdit
    ) -> WeeklyReport:
        allowed_sources = {
            source.model_dump_json()
            for item in self._items(current)
            for source in item.sources
        }
        existing_ids = {item.id for item in self._items(current)}
        seen_ids: set[str] = set()

        def item(value: WeeklyItemEdit) -> WeeklyReportItem:
            if value.id in seen_ids:
                raise RepositoryWebError(
                    "weekly_item_duplicate", "工作项 ID 重复。", 422
                )
            seen_ids.add(value.id)
            references = [
                WeeklySourceReference.model_validate(
                    source.model_dump()
                )
                for source in value.sources
            ]
            if value.id not in existing_ids:
                if not value.id.startswith("manual_"):
                    raise RepositoryWebError(
                        "weekly_source_invalid",
                        "新增工作项必须标记为用户补充。",
                        422,
                    )
                references = [
                    WeeklySourceReference(
                        source_type="user_note",
                        source_id=value.id,
                        title=value.content,
                        confidence="high",
                    )
                ]
            elif any(
                reference.model_dump_json() not in allowed_sources
                for reference in references
            ):
                raise RepositoryWebError(
                    "weekly_source_invalid",
                    "工作项包含未经验证的来源。",
                    422,
                )
            if not references:
                raise RepositoryWebError(
                    "weekly_sources_incomplete",
                    "工作项必须具有有效来源。",
                    422,
                )
            confidence = (
                "high" if value.id not in existing_ids else value.confidence
            )
            return WeeklyReportItem(
                id=value.id,
                content=value.content.strip(),
                title=value.title.strip() if value.title else None,
                description=(
                    value.description.strip()
                    if value.description
                    else None
                ),
                result=value.result.strip() if value.result else None,
                confidence=confidence,
                sources=references,
                confirmed_by_user=(
                    True
                    if confidence == "high"
                    else value.confirmed_by_user
                ),
                needs_confirmation=(
                    confidence == "medium"
                    and not value.confirmed_by_user
                ),
                notes=value.notes,
            )

        completed: list[WeeklyReportTopic] = []
        for topic in edited.completed:
            topic_items = [item(value) for value in topic.items]
            if not topic_items:
                continue
            sources = {
                source.label: source
                for report_item in topic_items
                for source in report_item.sources
            }
            completed.append(
                WeeklyReportTopic(
                    id=topic.id,
                    title=topic.title.strip(),
                    summary=topic.summary,
                    category=topic.category,
                    items=topic_items,
                    sources=list(sources.values()),
                    confidence=topic.confidence,
                    confirmed_by_user=topic.confirmed_by_user,
                )
            )
        report = current.model_copy(
            deep=True,
            update={
                "title": edited.title.strip(),
                "completed": completed,
                "debugging": [item(value) for value in edited.debugging],
                "testing": [item(value) for value in edited.testing],
                "risks": [item(value) for value in edited.risks],
                "next_week": [item(value) for value in edited.next_week],
                "status": "draft",
                "version": current.version + 1,
                "confirmed_at": None,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        report.source_coverage = self._coverage(report)
        report.content_markdown = MarkdownWeeklyExporter().render(report)
        return report

    def _coverage(self, report: WeeklyReport) -> float:
        items = self._items(report)
        if not items:
            return 1.0
        return sum(bool(item.sources) for item in items) / len(items)

    def _items(self, report: WeeklyReport) -> list[WeeklyReportItem]:
        return [
            *(item for topic in report.completed for item in topic.items),
            *report.debugging,
            *report.testing,
            *report.risks,
            *report.next_week,
        ]

    def _report_summary(self, report: WeeklyReport) -> dict[str, object]:
        return {
            "id": report.id,
            "title": report.title,
            "date_from": report.date_range.date_from.isoformat(),
            "date_to": report.date_range.date_to.isoformat(),
            "status": report.status,
            "source_coverage": report.source_coverage,
            "generator": report.generator,
            "version": report.version,
            "updated_at": report.updated_at.isoformat(),
        }

    def _report_payload(self, report: WeeklyReport) -> dict[str, object]:
        return report.model_dump(mode="json")

    def _validate_safe(self, report: WeeklyReport) -> None:
        try:
            self.weekly_service.validate_safe_report(report)
        except SensitiveContentError as exc:
            raise RepositoryWebError(
                "weekly_sensitive_content", str(exc), 422
            ) from exc
