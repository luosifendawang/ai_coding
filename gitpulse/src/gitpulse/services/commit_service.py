"""Commit message generation service."""

from __future__ import annotations

from pathlib import Path

from gitpulse.ai.commit_generator import CommitGenerator
from gitpulse.ai.mock_provider import MockLLMProvider
from gitpulse.ai.openai_provider import OpenAICompatibleProvider
from gitpulse.ai.provider import LLMProvider
from gitpulse.config import AIConfig, CommitConfig, DiffConfig, SecurityConfig
from gitpulse.exceptions import CommitGenerationError, SensitiveContentError
from gitpulse.models.commit import CommitAIFile, CommitAIRequest, CommitRules, CommitServiceResult
from gitpulse.models.diff import DiffCollection
from gitpulse.services.git_service import GitService
from gitpulse.services.security_service import SecurityService


class CommitService:
    """Coordinate Git, security, and AI commit generation."""

    def __init__(
        self,
        *,
        path: Path | None = None,
        ai_config: AIConfig | None = None,
        commit_config: CommitConfig | None = None,
        diff_config: DiffConfig | None = None,
        security_config: SecurityConfig | None = None,
        provider: LLMProvider | None = None,
    ) -> None:
        self.ai_config = ai_config or AIConfig()
        self.commit_config = commit_config or CommitConfig()
        self.git_service = GitService(path=path, diff_config=diff_config or DiffConfig())
        self.security_service = SecurityService(security_config or SecurityConfig())
        self.provider = provider or self._provider_from_config(self.ai_config)
        self.generator = CommitGenerator(
            self.provider,
            model=self.ai_config.model,
            temperature=self.ai_config.temperature,
            top_p=self.ai_config.top_p,
            max_output_tokens=self.ai_config.max_output_tokens,
        )

    def generate_commit_message(
        self,
        *,
        source: str = "staged",
        user_context: str | None = None,
    ) -> CommitServiceResult:
        repository = self.git_service.inspect_repository()
        diff = self.git_service.get_staged_diff() if source == "staged" else self.git_service.get_unstaged_diff()
        security = self.security_service.process_diff(diff)
        result = CommitServiceResult(
            repository=repository,
            diff=diff,
            security=security,
            provider_name=getattr(self.provider, "name", None),
        )
        if diff.stats.files_changed == 0:
            result.warnings.append("当前暂存区没有代码变更。" if source == "staged" else "当前未暂存区没有代码变更。")
            return result
        if not security.scan_completed:
            result.warnings.append("安全扫描失败，已阻止 AI 调用。")
            return result
        if self._should_block_ai(security.block_remote_model, security.summary.critical):
            result.warnings.append("检测到高风险敏感信息，已阻止 AI 调用。")
            return result

        request = self._build_ai_request(
            repository.name,
            repository.current_branch,
            repository.head_commit,
            diff,
            security.sanitized_diff,
            security.warnings,
            user_context,
        )
        generation = self.generator.generate(request)
        result.generation = generation
        result.ai_called = True
        return result

    def _should_block_ai(self, block_remote_model: bool, critical_count: int) -> bool:
        if critical_count > 0:
            return True
        if block_remote_model and not self.provider.is_local:
            return True
        if block_remote_model and self.provider.is_local and not self.ai_config.allow_local_on_high_risk:
            return True
        return False

    def _build_ai_request(
        self,
        repository: str,
        branch: str | None,
        head_commit: str | None,
        diff: DiffCollection,
        sanitized_diff: str,
        security_warnings: list[str],
        user_context: str | None,
    ) -> CommitAIRequest:
        return CommitAIRequest(
            repository=repository,
            branch=branch,
            head_commit=head_commit,
            files=[
                CommitAIFile(
                    path=file.new_path,
                    old_path=file.old_path,
                    status=file.status.value,
                    additions=file.additions,
                    deletions=file.deletions,
                    is_binary=file.is_binary,
                    is_truncated=file.is_truncated,
                )
                for file in diff.files
            ],
            sanitized_diff=sanitized_diff,
            stats={
                "files_changed": diff.stats.files_changed,
                "insertions": diff.stats.insertions,
                "deletions": diff.stats.deletions,
                "total_patch_chars": diff.stats.total_patch_chars,
            },
            commit_rules=CommitRules(
                language=self.commit_config.language,
                format=self.commit_config.format,
                include_body=self.commit_config.include_body,
                subject_max_length=self.commit_config.subject_max_length,
                allowed_types=self.commit_config.allowed_types,
            ),
            user_context=user_context,
            security_warnings=security_warnings,
        )

    def _provider_from_config(self, config: AIConfig) -> LLMProvider:
        if config.provider == "mock":
            return MockLLMProvider()
        return OpenAICompatibleProvider(config)
