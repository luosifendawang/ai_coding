"""Security-bound AI generation and confirmed local Git commits."""

from __future__ import annotations

import os
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from gitplus.ai.provider import LLMProvider
from gitplus.config import GitPlusConfig
from gitplus.exceptions import GitCommandError
from gitplus.git.command_runner import GitCommandRunner
from gitplus.models.commit import CommitServiceResult
from gitplus.models.risk import SecurityScanResult
from gitplus.services.commit_record_service import (
    CommitConfirmationRequest,
    CommitRecordService,
)
from gitplus.services.commit_service import CommitService
from gitplus.services.git_service import GitService
from gitplus.services.security_service import SecurityService
from gitplus.storage.database import Database
from gitplus.web.services.repository_web_service import (
    RepositoryWebError,
    RepositoryWebService,
)


@dataclass
class StoredScan:
    revision: str
    result: SecurityScanResult
    created_at: float


@dataclass
class StoredGeneration:
    revision: str
    scan_id: str
    result: CommitServiceResult
    created_at: float


class CommitWebService:
    ttl_seconds = 900

    def __init__(
        self,
        repository_service: RepositoryWebService,
        config: GitPlusConfig,
        database: Database,
        *,
        provider: LLMProvider | None = None,
    ) -> None:
        self.repository_service = repository_service
        self.root = repository_service.root
        self.config = config
        self.database = database
        self.provider = provider
        self.scans: dict[str, StoredScan] = {}
        self.generations: dict[str, StoredGeneration] = {}

    def security_scan(self, revision: str) -> dict[str, object]:
        status = self.repository_service.assert_revision(revision)
        self._require_staged_without_conflicts(status)
        diff = GitService(
            path=self.root, diff_config=self.config.diff
        ).get_staged_diff()
        result = SecurityService(self.config.security).process_diff(diff)
        if not result.scan_completed:
            raise RepositoryWebError("security_scan_failed", "安全扫描未能完成。", 500)
        scan_id = f"scan_{uuid4().hex[:12]}"
        self.scans[scan_id] = StoredScan(revision, result, time.monotonic())
        return {
            "scan_id": scan_id,
            "source": "staged",
            "status": "passed" if result.passed else "blocked",
            "summary": result.summary.model_dump(),
            "remote_ai_allowed": not result.block_remote_model,
            "findings": [
                {
                    "id": finding.id,
                    "rule_id": finding.rule_id,
                    "rule_name": finding.rule_name,
                    "severity": finding.level.value,
                    "path": finding.file_path,
                    "line": finding.line_number,
                    "message": finding.description,
                    "masked_preview": "********",
                    "suggestion": finding.suggestion,
                }
                for finding in result.findings
            ],
        }

    def generate(
        self,
        *,
        revision: str,
        scan_id: str,
        context: str | None,
    ) -> dict[str, object]:
        status = self.repository_service.assert_revision(revision)
        self._require_staged_without_conflicts(status)
        scan = self._valid_scan(scan_id, revision)
        if scan.result.block_remote_model:
            raise RepositoryWebError(
                "security_blocked",
                "检测到高风险敏感信息，已阻止远程 AI 调用。",
                409,
            )
        service = CommitService(
            path=self.root,
            ai_config=self.config.ai,
            commit_config=self.config.commit,
            diff_config=self.config.diff,
            security_config=self.config.security,
            provider=self.provider,
        )
        try:
            result = service.generate_commit_message(
                source="staged", user_context=context
            )
        except Exception as exc:
            raise self._ai_error(exc) from exc
        if result.generation is None:
            message = result.warnings[0] if result.warnings else "AI 未返回有效结果。"
            code = (
                "security_blocked"
                if result.security.block_remote_model
                else "ai_response_invalid"
            )
            raise RepositoryWebError(code, message, 409)
        generation_id = f"generation_{uuid4().hex[:12]}"
        self.generations[generation_id] = StoredGeneration(
            revision, scan_id, result, time.monotonic()
        )
        generation = result.generation
        labels = {"concise": "简洁", "standard": "标准", "detailed": "详细"}
        return {
            "generation_id": generation_id,
            "repository_revision": revision,
            "primary_purpose": generation.primary_purpose,
            "type": generation.type,
            "scope": generation.scope,
            "subject": generation.subject,
            "body": generation.body,
            "confidence": generation.confidence,
            "should_split": generation.should_split,
            "split_suggestions": [
                suggestion.model_dump(mode="json")
                for suggestion in generation.split_suggestions
            ],
            "needs_confirmation": generation.needs_confirmation,
            "candidates": [
                {
                    "id": candidate_id,
                    "label": labels.get(candidate_id, candidate_id),
                    **candidate.model_dump(mode="json"),
                }
                for candidate_id, candidate in generation.candidates.items()
            ],
            "validation_warnings": generation.validation_warnings,
            "evidence": [
                {"path": item.file, "reason": item.reason}
                for item in generation.evidence
            ],
        }

    def commit(
        self,
        *,
        generation_id: str,
        revision: str,
        selected_candidate: str,
        subject: str,
        body: list[str],
        footer: list[str],
        confirmed: bool,
    ) -> dict[str, object]:
        if not confirmed:
            raise RepositoryWebError(
                "commit_confirmation_required", "创建 Commit 前需要明确确认。"
            )
        if not self.repository_service.lock.acquire(blocking=False):
            raise RepositoryWebError(
                "repository_busy", "当前仓库正在执行另一项写操作。", 409
            )
        try:
            status = self.repository_service.assert_revision(revision)
            self._require_staged_without_conflicts(status)
            repository = status["repository"]
            if repository["detached_head"]:  # type: ignore[index]
                raise RepositoryWebError(
                    "detached_head", "Detached HEAD 状态下不允许通过 Web 创建 Commit。"
                )
            if not repository["identity_configured"]:  # type: ignore[index]
                raise RepositoryWebError(
                    "git_identity_missing",
                    '未配置 Git 用户身份。请运行 git config --global user.name "你的名字" '
                    '和 git config --global user.email "你的邮箱"。',
                )
            stored = self._valid_generation(generation_id, revision)
            self._valid_scan(stored.scan_id, revision)
            message = self._validate_message(subject, body, footer)
            before_head = (
                GitCommandRunner(self.root)
                .run(["rev-parse", "HEAD"], check=False)
                .stdout.strip()
            )
            message_path: Path | None = None
            try:
                descriptor, raw_path = tempfile.mkstemp(
                    prefix="gitplus-commit-", suffix=".txt"
                )
                message_path = Path(raw_path)
                os.chmod(message_path, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(message)
                GitCommandRunner(self.root, timeout_seconds=60).run(
                    ["commit", "-F", str(message_path)]
                )
            except GitCommandError as exc:
                raise RepositoryWebError("commit_failed", str(exc)) from exc
            finally:
                if message_path is not None:
                    message_path.unlink(missing_ok=True)
            commit_hash = (
                GitCommandRunner(self.root).run(["rev-parse", "HEAD"]).stdout.strip()
            )
            if not commit_hash or commit_hash == before_head:
                raise RepositoryWebError(
                    "commit_failed", "Git 未创建新的 Commit。", 500
                )
            request = CommitConfirmationRequest(
                result=stored.result,
                selected_candidate=selected_candidate,
                final_subject=subject.strip(),
                final_body=body + footer,
                commit_hash=commit_hash,
                model_name=self.config.ai.model,
            )
            try:
                self.database.initialize()
                record = CommitRecordService(self.database).save_confirmed_record(
                    request
                )
            except Exception as exc:
                raise RepositoryWebError(
                    "commit_record_failed",
                    f"Commit {commit_hash[:8]} 已创建，但记录保存失败。",
                    500,
                ) from exc
            refreshed = self.repository_service.status()
            generation = stored.result.generation
            return {
                "success": True,
                "commit": {
                    "hash": commit_hash,
                    "subject": subject.strip(),
                    "branch": repository["branch"],  # type: ignore[index]
                    "files": stored.result.diff.stats.files_changed,
                    "additions": stored.result.diff.stats.insertions,
                    "deletions": stored.result.diff.stats.deletions,
                    "edited_by_user": bool(
                        generation and generation.subject != subject.strip()
                    ),
                },
                "record_id": record.id,
                "repository_status": refreshed,
                "repository_revision": refreshed["revision"],
            }
        finally:
            self.repository_service.lock.release()

    def _require_staged_without_conflicts(self, status: dict[str, object]) -> None:
        if status["repository"]["has_conflicts"]:  # type: ignore[index]
            raise RepositoryWebError(
                "repository_has_conflicts",
                "当前仓库存在未解决的合并冲突。",
                409,
            )
        if status["summary"]["staged"] == 0:  # type: ignore[index]
            raise RepositoryWebError("no_staged_changes", "当前没有已暂存变更。", 409)

    def _valid_scan(self, scan_id: str, revision: str) -> StoredScan:
        scan = self.scans.get(scan_id)
        if (
            scan is None
            or scan.revision != revision
            or time.monotonic() - scan.created_at > self.ttl_seconds
        ):
            raise RepositoryWebError(
                "security_scan_expired", "安全扫描已过期，请重新扫描。", 409
            )
        return scan

    def _valid_generation(self, generation_id: str, revision: str) -> StoredGeneration:
        generation = self.generations.get(generation_id)
        if (
            generation is None
            or generation.revision != revision
            or time.monotonic() - generation.created_at > self.ttl_seconds
        ):
            raise RepositoryWebError(
                "generation_expired", "Commit Message 已过期，请重新生成。", 409
            )
        return generation

    def _validate_message(
        self, subject: str, body: list[str], footer: list[str]
    ) -> str:
        cleaned = subject.strip()
        if not cleaned or "\n" in subject or "\r" in subject:
            raise RepositoryWebError("commit_message_invalid", "Commit Subject 无效。")
        if len(cleaned) > self.config.commit.subject_max_length:
            raise RepositoryWebError(
                "commit_message_invalid",
                f"Commit Subject 不能超过 {self.config.commit.subject_max_length} 个字符。",
            )
        pattern = r"^([a-z]+)(?:\([A-Za-z0-9_-]{1,30}\))?: .+"
        match = re.fullmatch(pattern, cleaned)
        if not match or match.group(1) not in self.config.commit.allowed_types:
            raise RepositoryWebError(
                "commit_message_invalid", "Commit Subject 不符合配置格式。"
            )
        all_lines = [*body, *footer]
        if any(
            "\0" in line or any(ord(char) < 32 and char != "\t" for char in line)
            for line in all_lines
        ):
            raise RepositoryWebError(
                "commit_message_invalid", "Commit Message 包含控制字符。"
            )
        message = cleaned
        if body:
            message += "\n\n" + "\n".join(line.rstrip() for line in body)
        if footer:
            message += "\n\n" + "\n".join(line.rstrip() for line in footer)
        if len(message) > 20_000:
            raise RepositoryWebError(
                "commit_message_invalid", "Commit Message 总长度超过限制。"
            )
        return message + "\n"

    def _ai_error(self, exc: Exception) -> RepositoryWebError:
        name = type(exc).__name__.lower()
        if "authentication" in name:
            return RepositoryWebError("ai_authentication_failed", "AI 鉴权失败。")
        if "ratelimit" in name:
            return RepositoryWebError("ai_rate_limited", "AI 请求频率受限。")
        if "timeout" in name:
            return RepositoryWebError("ai_timeout", "AI 请求超时。")
        message = str(exc).lower()
        if "length" in message or "输出长度" in str(exc):
            return RepositoryWebError(
                "ai_output_length_exceeded",
                "模型在生成最终 JSON 前达到输出长度上限。",
            )
        return RepositoryWebError("ai_response_invalid", "AI 返回结果无效。")
