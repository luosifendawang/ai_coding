"""Security check service."""

from __future__ import annotations

from pathlib import Path

from gitpulse.config import DiffConfig, SecurityConfig
from gitpulse.models.diff import DiffCollection
from gitpulse.models.repository import RepositoryInfo
from gitpulse.models.risk import SecurityScanResult
from gitpulse.services.git_service import GitService
from gitpulse.services.security_service import SecurityService


class CheckResult:
    """Container for repository, diff, and security scan results."""

    def __init__(
        self,
        *,
        repository: RepositoryInfo,
        diff: DiffCollection,
        security: SecurityScanResult,
        source: str,
    ) -> None:
        self.repository = repository
        self.diff = diff
        self.security = security
        self.source = source


class CheckService:
    """Run Git diff reads followed by local security scanning."""

    def __init__(
        self,
        path: Path | None = None,
        diff_config: DiffConfig | None = None,
        security_config: SecurityConfig | None = None,
    ) -> None:
        self.git_service = GitService(path=path, diff_config=diff_config or DiffConfig())
        self.security_service = SecurityService(security_config or SecurityConfig())

    def run(self, *, staged: bool = True) -> CheckResult:
        repository = self.git_service.inspect_repository()
        diff = self.git_service.get_staged_diff() if staged else self.git_service.get_unstaged_diff()
        security = self.security_service.process_diff(diff)
        return CheckResult(
            repository=repository,
            diff=diff,
            security=security,
            source="staged" if staged else "unstaged",
        )

