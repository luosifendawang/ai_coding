"""Bounded and masked single-file diff previews."""

from __future__ import annotations

from typing import cast

from gitpulse.config import SecurityConfig, WebDiffConfig
from gitpulse.git.command_runner import GitCommandRunner
from gitpulse.git.parser import count_patch_lines
from gitpulse.models.diff import DiffCollection, DiffSource, FileChangeStatus, FileDiff
from gitpulse.services.security_service import SecurityService
from gitpulse.web.services.repository_web_service import (
    RepositoryPathValidator,
    RepositoryWebError,
    RepositoryWebService,
)


class DiffWebService:
    def __init__(
        self,
        repository_service: RepositoryWebService,
        config: WebDiffConfig,
        security_config: SecurityConfig,
    ) -> None:
        self.repository_service = repository_service
        self.root = repository_service.root
        self.config = config
        self.runner = GitCommandRunner(self.root, timeout_seconds=20)
        self.validator = RepositoryPathValidator()
        self.security_service = SecurityService(security_config)

    def read(
        self, path: str, source: str, context: int | None = None
    ) -> dict[str, object]:
        if source not in {"staged", "unstaged"}:
            raise RepositoryWebError("invalid_diff_source", "Diff 来源无效。")
        context_lines = (
            self.config.default_context_lines if context is None else context
        )
        if not 0 <= context_lines <= 20:
            raise RepositoryWebError("invalid_diff_context", "Diff 上下文范围无效。")
        status = self.repository_service.status()
        files = cast(list[dict[str, object]], status["files"])
        items = {str(item["path"]): item for item in files}
        self.validator.validate_relative_path(self.root, path, status_paths=set(items))
        item = items[path]
        if source == "unstaged" and item["untracked"]:
            patch, binary, truncated, original_chars = self._untracked_preview(path)
        else:
            arguments = ["diff"]
            if source == "staged":
                arguments.append("--cached")
            arguments.extend(
                ["--no-ext-diff", f"--unified={context_lines}", "--", path]
            )
            patch = self.runner.run(arguments).stdout
            binary = "Binary files " in patch or "GIT binary patch" in patch
            original_chars = len(patch)
            truncated = original_chars > self.config.max_diff_chars
            if binary:
                patch = ""
            elif truncated:
                patch = patch[: self.config.max_diff_chars]
        additions, deletions = count_patch_lines(patch)
        if patch and not binary:
            collection = DiffCollection(
                source=DiffSource(source),
                files=[
                    FileDiff.with_extension(
                        new_path=path,
                        status=FileChangeStatus.MODIFIED,
                        patch=patch,
                        additions=additions,
                        deletions=deletions,
                        is_truncated=truncated,
                    )
                ],
            )
            patch = self.security_service.process_diff(collection).sanitized_diff
        return {
            "path": path,
            "source": source,
            "binary": binary,
            "truncated": truncated,
            "truncation_reason": "diff_too_large" if truncated else None,
            "original_chars": original_chars,
            "returned_chars": len(patch),
            "additions": additions,
            "deletions": deletions,
            "diff": patch,
            "revision": status["revision"],
        }

    def _untracked_preview(self, path: str) -> tuple[str, bool, bool, int]:
        target = self.root / path
        size = target.stat().st_size
        read_size = min(size, self.config.max_file_bytes)
        data = target.read_bytes()[:read_size]
        binary = b"\0" in data
        if binary:
            return "", True, size > read_size, size
        text = data.decode("utf-8", errors="replace")
        lines = text.splitlines()
        patch = "\n".join(
            [
                f"diff --git a/{path} b/{path}",
                "new file mode 100644",
                "--- /dev/null",
                f"+++ b/{path}",
                f"@@ -0,0 +1,{len(lines)} @@",
                *(f"+{line}" for line in lines),
            ]
        )
        original_chars = len(patch)
        truncated = size > read_size or original_chars > self.config.max_diff_chars
        return patch[: self.config.max_diff_chars], False, truncated, original_chars
