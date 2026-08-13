"""Aggregate real Git history, persisted commit records, and worklogs."""

from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from typing import cast

from gitplus.git.log_reader import GitLogReader
from gitplus.models.diff import (
    DiffCollection,
    DiffSource,
    FileChangeStatus,
    FileDiff,
)
from gitplus.models.history import CommitHistoryFilters
from gitplus.models.worklog import WorklogFilters
from gitplus.services.history_service import HistoryService
from gitplus.services.security_service import SecurityService
from gitplus.services.worklog_service import WorklogService
from gitplus.web.services.repository_context_service import RepositoryContextService
from gitplus.web.services.repository_web_service import RepositoryWebService


class HistoryWebService:
    def __init__(
        self,
        repository_service: RepositoryWebService,
        repository_context: RepositoryContextService,
        history_service: HistoryService,
        worklog_service: WorklogService,
    ) -> None:
        self.repository_service = repository_service
        self.repository_context = repository_context
        self.history_service = history_service
        self.worklog_service = worklog_service
        self.security_service = SecurityService()

    def query(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
        record_types: list[str] | None,
        repository: str | None,
        tag: str | None,
        commit_type: str | None,
        keyword: str | None,
        author: str | None,
        page: int,
        page_size: int,
    ) -> dict[str, object]:
        repository_record = self.repository_context.ensure_record()
        if repository and repository not in {
            repository_record.id,
            repository_record.name,
            repository_record.root_path,
        }:
            items: list[dict[str, object]] = []
        else:
            start, end = self._range(date_from, date_to)
            items = self._items(
                repository_record.id,
                start,
                end,
                record_types=record_types,
                tag=tag,
                commit_type=commit_type,
                keyword=keyword,
                author=author,
            )
        total = len(items)
        offset = (page - 1) * page_size
        return {
            "items": items[offset : offset + page_size],
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, (total + page_size - 1) // page_size),
            "stats": self._stats(items),
        }

    def export(self, *, export_format: str, **filters) -> tuple[bytes, str, str]:
        result = self.query(page=1, page_size=100, **filters)
        # Export is intentionally bounded; query sources are independently capped.
        total = cast(int, result["total"])
        export_result = self.query(
            page=1,
            page_size=max(100, total),
            **filters,
        )
        all_items = cast(list[dict[str, object]], export_result["items"])
        if export_format == "json":
            content = json.dumps(
                {"items": all_items, "stats": self._stats(all_items)},
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            filename = self._filename(filters, "json")
            return content, "application/json; charset=utf-8", filename
        if export_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(
                ["record_type", "occurred_at", "title", "repository", "type", "duration_minutes", "tags"]
            )
            for item in all_items:
                writer.writerow(
                    [
                        item["record_type"],
                        item["occurred_at"],
                        item["title"],
                        item["repository"],
                        item.get("type") or "",
                        item.get("duration_minutes") or "",
                        ",".join(cast(list[str], item.get("tags", []))),
                    ]
                )
            return (
                ("\ufeff" + output.getvalue()).encode("utf-8"),
                "text/csv; charset=utf-8",
                self._filename(filters, "csv"),
            )
        lines = ["# gitplus 工作历史", ""]
        for item in all_items:
            lines.extend(
                [
                    f"## {item['title']}",
                    "",
                    f"- 时间：{item['occurred_at']}",
                    f"- 类型：{item['record_type']}",
                    f"- 仓库：{item['repository']}",
                ]
            )
            if item.get("summary"):
                lines.append(f"- 摘要：{item['summary']}")
            lines.append("")
        return (
            "\n".join(lines).encode("utf-8"),
            "text/markdown; charset=utf-8",
            self._filename(filters, "md"),
        )

    def _items(
        self,
        repository_id: str,
        start: datetime,
        end: datetime,
        *,
        record_types: list[str] | None,
        tag: str | None,
        commit_type: str | None,
        keyword: str | None,
        author: str | None,
    ) -> list[dict[str, object]]:
        selected = set(record_types or ["git_commit", "commit_record", "worklog"])
        repository_name = self.repository_service.root.name
        items: list[dict[str, object]] = []
        if "git_commit" in selected and not tag:
            email = author or self.repository_service.repository.get_user_email()
            commits = GitLogReader(self.repository_service.repository).read(
                start,
                end,
                authors=[email] if email else None,
                max_count=2000,
            )
            for commit in commits:
                detected_type = self._commit_type(commit.subject)
                if commit_type and detected_type != commit_type:
                    continue
                if keyword and keyword.lower() not in commit.subject.lower():
                    continue
                items.append(
                    {
                        "id": commit.commit_hash,
                        "record_type": "git_commit",
                        "occurred_at": commit.committed_at.isoformat(),
                        "title": self._safe_text(commit.subject),
                        "body": self._safe_text(commit.body),
                        "summary": self._safe_text(commit.body),
                        "repository": repository_name,
                        "type": detected_type,
                        "commit_hash": commit.commit_hash,
                        "short_hash": commit.short_hash,
                        "author_name": commit.author_name,
                        "author_email": commit.author_email,
                        "changed_files": len(commit.changed_files),
                        "insertions": commit.insertions,
                        "deletions": commit.deletions,
                        "duration_minutes": None,
                        "tags": [],
                    }
                )
        if "commit_record" in selected and not tag:
            records = self.history_service.list_commit_records(
                CommitHistoryFilters(
                    repository_id=repository_id,
                    date_from=start,
                    date_to=end,
                    commit_type=commit_type,
                    search=keyword,
                    limit=2000,
                )
            )
            for record in records:
                items.append(
                    {
                        "id": record.id,
                        "record_type": "commit_record",
                        "occurred_at": record.created_at.isoformat(),
                        "title": self._safe_text(record.subject),
                        "body": [self._safe_text(line) for line in record.body],
                        "summary": self._safe_text(record.summary or ""),
                        "repository": repository_name,
                        "type": record.commit_type,
                        "commit_hash": record.commit_hash,
                        "short_hash": (
                            record.commit_hash[:8] if record.commit_hash else None
                        ),
                        "scope": record.scope,
                        "branch": record.branch,
                        "changed_files": len(record.files),
                        "insertions": record.insertions,
                        "deletions": record.deletions,
                        "ai_provider": record.provider_name,
                        "ai_model": record.model_name,
                        "ai_called": bool(record.provider_name),
                        "message_edited_by_user": any(
                            line.startswith("AI 原始建议：")
                            for line in record.verification
                        ),
                        "security_summary": record.security_summary,
                        "confirmed_by_user": record.confirmed_by_user,
                        "duration_minutes": None,
                        "tags": [],
                    }
                )
        if "worklog" in selected:
            worklogs = self._all_worklogs(
                WorklogFilters(
                    repository_id=repository_id,
                    date_from=start.date(),
                    date_to=end.date(),
                    tags=[tag] if tag else None,
                    keyword=keyword,
                    limit=100,
                )
            )
            for worklog in worklogs:
                occurred_at = worklog.occurred_at or datetime.combine(
                    worklog.work_date, time.min, tzinfo=timezone.utc
                )
                items.append(
                    {
                        "id": worklog.id,
                        "record_type": "worklog",
                        "occurred_at": occurred_at.isoformat(),
                        "title": self._safe_text(worklog.title),
                        "body": self._safe_text(worklog.description or ""),
                        "summary": self._safe_text(
                            worklog.result or worklog.description or ""
                        ),
                        "repository": repository_name,
                        "type": worklog.work_type,
                        "commit_hash": worklog.related_commit_hash,
                        "short_hash": (
                            worklog.related_commit_hash[:8]
                            if worklog.related_commit_hash
                            else None
                        ),
                        "duration_minutes": worklog.duration_minutes,
                        "tags": worklog.tags,
                    }
                )
        items.sort(key=lambda item: str(item["occurred_at"]), reverse=True)
        return items

    def _all_worklogs(self, filters: WorklogFilters) -> list:
        items = []
        offset = 0
        while True:
            page_filters = filters.model_copy(update={"offset": offset})
            page = self.worklog_service.list(page_filters)
            items.extend(page)
            if len(page) < filters.limit or len(items) >= 5000:
                return items
            offset += filters.limit

    def _range(
        self, date_from: date | None, date_to: date | None
    ) -> tuple[datetime, datetime]:
        today = datetime.now(timezone.utc).date()
        first = date_from or today - timedelta(days=29)
        last = date_to or today
        return (
            datetime.combine(first, time.min, tzinfo=timezone.utc),
            datetime.combine(last, time.max, tzinfo=timezone.utc),
        )

    def _stats(self, items: list[dict[str, object]]) -> dict[str, object]:
        tags: Counter[str] = Counter()
        for item in items:
            tags.update(
                str(tag)
                for tag in cast(list[object], item.get("tags", []))
            )
        return {
            "git_commits": sum(
                item["record_type"] == "git_commit" for item in items
            ),
            "commit_records": sum(
                item["record_type"] == "commit_record" for item in items
            ),
            "worklogs": sum(item["record_type"] == "worklog" for item in items),
            "development_minutes": sum(
                duration
                for item in items
                if isinstance(
                    duration := item.get("duration_minutes"), int
                )
            ),
            "repositories": sorted(
                {str(item["repository"]) for item in items}
            ),
            "tags": [
                {"name": name, "count": count}
                for name, count in tags.most_common(20)
            ],
        }

    def _safe_text(self, value: str) -> str:
        if not value:
            return ""
        result = self.security_service.process_diff(
            DiffCollection(
                source=DiffSource.STAGED,
                files=[
                    FileDiff.with_extension(
                        new_path="history.txt",
                        status=FileChangeStatus.MODIFIED,
                        patch=value,
                    )
                ],
            )
        )
        return result.sanitized_diff

    def _filename(self, filters: dict[str, object], extension: str) -> str:
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        if isinstance(date_from, date) and isinstance(date_to, date):
            suffix = f"-{date_from.isoformat()}-{date_to.isoformat()}"
        else:
            suffix = ""
        return f"gitplus-history{suffix}.{extension}"

    def _commit_type(self, subject: str) -> str | None:
        match = re.match(r"^([a-z]+)(?:\([^)]*\))?!?:", subject)
        return match.group(1) if match else None
