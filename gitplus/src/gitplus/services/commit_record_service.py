"""Persist confirmed commit generation results."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from gitplus.models.commit import CommitServiceResult
from gitplus.models.storage import CommitRecord, RepositoryRecord, RiskRecord
from gitplus.storage.database import Database
from gitplus.storage.serializers import IdGenerator
from gitplus.storage.unit_of_work import UnitOfWork


class CommitConfirmationRequest:
    """Final user-confirmed commit message to persist."""

    def __init__(
        self,
        *,
        result: CommitServiceResult,
        selected_candidate: str,
        final_subject: str,
        final_body: list[str],
        commit_hash: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.result = result
        self.selected_candidate = selected_candidate
        self.final_subject = final_subject
        self.final_body = final_body
        self.commit_hash = commit_hash
        self.model_name = model_name


class CommitRecordService:
    """Save confirmed commit records and associated risks in one transaction."""

    def __init__(
        self, database: Database, id_generator: IdGenerator | None = None
    ) -> None:
        self.database = database
        self.id_generator = id_generator or IdGenerator()

    def save_confirmed_record(self, request: CommitConfirmationRequest) -> CommitRecord:
        current = datetime.now(timezone.utc)
        result = request.result
        generation = result.generation
        if generation is None:
            raise ValueError("generation is required")
        with UnitOfWork(self.database) as uow:
            repository = uow.repositories.upsert(
                RepositoryRecord(
                    id=self.id_generator.new_repository_id(),
                    name=result.repository.name,
                    root_path=str(result.repository.root_path),
                    remote_url=result.repository.remote_url,
                    created_at=current,
                    updated_at=current,
                    last_seen_at=current,
                )
            )
            files = [file.new_path for file in result.diff.files]
            verification = [warning for warning in generation.validation_warnings]
            if generation.subject != request.final_subject:
                verification.append(f"AI 原始建议：{generation.subject}")
            record = CommitRecord(
                id=self.id_generator.new_commit_record_id(),
                repository_id=repository.id,
                commit_hash=request.commit_hash,
                branch=result.repository.current_branch,
                commit_type=generation.type,
                scope=generation.scope,
                subject=request.final_subject,
                body=request.final_body,
                summary=generation.primary_purpose,
                files=files,
                insertions=result.diff.stats.insertions,
                deletions=result.diff.stats.deletions,
                confidence=generation.confidence,
                confirmed_by_user=True,
                selected_candidate=request.selected_candidate,
                should_split=generation.should_split,
                split_confidence=generation.split_confidence,
                verification=verification,
                provider_name=result.provider_name,
                model_name=request.model_name,
                security_summary=result.security.summary.model_dump(),
                content_hash=self._content_hash(
                    repository.id, request.final_subject, request.final_body, files
                ),
                created_at=current,
                updated_at=current,
            )
            saved = uow.commit_records.create(record)
            risks = [
                RiskRecord(
                    id=self.id_generator.new_risk_id(),
                    record_id=saved.id,
                    record_type="commit",
                    rule_id=finding.rule_id,
                    risk_level=finding.level.value,
                    risk_type=finding.category.value,
                    file_path=finding.file_path,
                    line_number=finding.line_number,
                    description=finding.description,
                    masked_value=finding.masked_value,
                    suggestion=finding.suggestion,
                    blocks_remote_model=finding.blocks_remote_model,
                    created_at=current,
                )
                for finding in result.security.findings
            ]
            uow.risks.create_many(risks)
            return saved

    def _content_hash(
        self, repository_id: str, subject: str, body: list[str], files: list[str]
    ) -> str:
        payload = "\n".join([repository_id, subject, *body, *sorted(files)])
        return sha256(payload.encode("utf-8")).hexdigest()
