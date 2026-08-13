"""Normalize weekly generation input."""

from __future__ import annotations

import re

from gitplus.models.source import WeeklySourceReference
from gitplus.models.weekly import WeeklyGenerationInput, WeeklyRawItem


class WeeklyNormalizer:
    """Convert commits, commit records, and worklogs into raw report items."""

    def normalize(self, generation_input: WeeklyGenerationInput) -> list[WeeklyRawItem]:
        items: list[WeeklyRawItem] = []
        for commit in generation_input.commits:
            items.append(
                WeeklyRawItem(
                    id=f"commit_{commit.short_hash}",
                    source_type="commit",
                    category_hint=self._category_from_subject(commit.subject),
                    repository_id=commit.repository_id,
                    repository_name=commit.repository_name,
                    scope=self._scope_from_subject(commit.subject),
                    commit_type=self._type_from_subject(commit.subject),
                    title=self._clean_subject(commit.subject),
                    description=commit.body,
                    files=[path.replace("\\", "/") for path in commit.files],
                    occurred_at=commit.committed_at,
                    sources=[
                        WeeklySourceReference(
                            source_type="commit",
                            source_id=commit.commit_hash,
                            repository_id=commit.repository_id,
                            commit_hash=commit.commit_hash,
                            title=commit.subject,
                            repository_name=commit.repository_name,
                            confidence="high",
                            files=commit.files[:100],
                        )
                    ],
                )
            )
        for record in generation_input.commit_records:
            items.append(
                WeeklyRawItem(
                    id=f"record_{record.id}",
                    source_type="record",
                    category_hint=self._category_from_type(record.commit_type),
                    repository_id=record.repository_id,
                    scope=record.scope,
                    commit_type=record.commit_type,
                    title=self._clean_subject(record.subject),
                    description=record.summary,
                    files=[path.replace("\\", "/") for path in record.files],
                    occurred_at=record.created_at,
                    sources=[
                        WeeklySourceReference(
                            source_type="record",
                            source_id=record.id,
                            repository_id=record.repository_id,
                            commit_hash=record.commit_hash,
                            title=record.subject,
                            confidence=record.confidence or "high",
                            files=record.files[:100],
                        )
                    ],
                )
            )
        for worklog in generation_input.worklogs:
            items.append(
                WeeklyRawItem(
                    id=f"worklog_{worklog.id}",
                    source_type="worklog",
                    category_hint=self._category_from_worklog(worklog.work_type),
                    repository_id=worklog.repository_id,
                    repository_name=worklog.repository_name,
                    title=self._clean_text(worklog.title),
                    description=worklog.description,
                    result=worklog.result,
                    occurred_at=None,
                    sources=[
                        WeeklySourceReference(
                            source_type="worklog",
                            source_id=worklog.id,
                            repository_id=worklog.repository_id,
                            title=worklog.title,
                            repository_name=worklog.repository_name,
                            confidence="high",
                        )
                    ],
                )
            )
        for change in generation_input.uncommitted_changes:
            items.append(
                WeeklyRawItem(
                    id=f"uncommitted_{change.repository_id}_{abs(hash(change.summary)) & 0xffffffff:x}",
                    source_type="uncommitted",
                    category_hint="completed",
                    repository_id=change.repository_id,
                    repository_name=change.repository_name,
                    title=self._clean_text(change.summary),
                    files=[path.replace("\\", "/") for path in change.files],
                    sources=[
                        WeeklySourceReference(
                            source_type="uncommitted",
                            source_id=f"{change.repository_id}:{change.summary}",
                            repository_id=change.repository_id,
                            title=change.summary,
                            repository_name=change.repository_name,
                            confidence=change.confidence,
                            files=change.files[:100],
                        )
                    ],
                )
            )
        for note in generation_input.user_notes:
            items.append(
                WeeklyRawItem(
                    id=f"user_note_{note.id}",
                    source_type="user_note",
                    category_hint="completed",
                    title=self._clean_text(note.content),
                    sources=[
                        WeeklySourceReference(
                            source_type="user_note",
                            source_id=note.id,
                            title=note.content,
                            confidence="high"
                            if note.confirmed_by_user
                            else "medium",
                        )
                    ],
                )
            )
        return items

    def _clean_subject(self, value: str) -> str:
        cleaned = self._clean_text(value)
        return re.sub(r"^[a-z]+(?:\([^)]+\))?:\s*", "", cleaned)

    def _clean_text(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _type_from_subject(self, subject: str) -> str | None:
        match = re.match(r"^([a-z]+)(?:\([^)]+\))?:", subject)
        return match.group(1) if match else None

    def _scope_from_subject(self, subject: str) -> str | None:
        match = re.match(r"^[a-z]+\(([^)]+)\):", subject)
        return match.group(1) if match else None

    def _category_from_subject(self, subject: str) -> str:
        return self._category_from_type(self._type_from_subject(subject))

    def _category_from_type(self, commit_type: str | None) -> str:
        if commit_type == "test":
            return "testing"
        return "completed"

    def _category_from_worklog(self, work_type: str) -> str:
        if work_type in {"debug", "support"}:
            return "debugging"
        if work_type == "test":
            return "testing"
        if work_type in {"setup", "document", "research", "learning", "meeting", "other"}:
            return "completed"
        return "completed"
