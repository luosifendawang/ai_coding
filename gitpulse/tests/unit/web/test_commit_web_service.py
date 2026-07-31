from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from gitpulse.ai.mock_provider import MockLLMProvider
from gitpulse.config import AIConfig, GitPulseConfig, StorageConfig
from gitpulse.storage.database import Database
from gitpulse.storage.unit_of_work import UnitOfWork
from gitpulse.web.services.commit_web_service import CommitWebService
from gitpulse.web.services.repository_web_service import (
    RepositoryWebError,
    RepositoryWebService,
)


def git(repo: Path, *args: str, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
    ).stdout.strip()


def repository(path: Path) -> Path:
    path.mkdir()
    git(path, "init")
    git(path, "config", "user.name", "Test User")
    git(path, "config", "user.email", "test@example.com")
    (path / "README.md").write_text("start\n", encoding="utf-8")
    git(path, "add", "--", "README.md")
    git(path, "commit", "-m", "chore: initialize")
    return path


def service(root: Path, tmp_path: Path) -> CommitWebService:
    config = GitPulseConfig(
        ai=AIConfig(provider="mock"),
        storage=StorageConfig(database=tmp_path / "gitpulse.db"),
    )
    return CommitWebService(
        RepositoryWebService(root),
        config,
        Database(config.storage.database_path),
        provider=MockLLMProvider(),
    )


def test_scan_generate_commit_and_persist_record(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    (root / "feature.py").write_text("enabled = True\n", encoding="utf-8")
    git(root, "add", "--", "feature.py")
    current = service(root, tmp_path)
    revision = str(current.repository_service.status()["revision"])

    scan = current.security_scan(revision)
    generated = current.generate(
        revision=revision,
        scan_id=str(scan["scan_id"]),
        context="新增功能开关",
    )
    result = current.commit(
        generation_id=str(generated["generation_id"]),
        revision=revision,
        selected_candidate="standard",
        subject="feat(core): 增加功能开关",
        body=["增加本地功能开关配置"],
        footer=[],
        confirmed=True,
    )

    assert result["success"] is True
    assert git(root, "log", "-1", "--pretty=%s") == "feat(core): 增加功能开关"
    with UnitOfWork(current.database) as uow:
        record = uow.commit_records.get_by_id(str(result["record_id"]))
    assert record is not None
    assert record.commit_hash == result["commit"]["hash"]


def test_high_risk_scan_blocks_ai_generation(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    secret = "sk-" + "a" * 32
    (root / "secret.txt").write_text(secret, encoding="utf-8")
    git(root, "add", "--", "secret.txt")
    current = service(root, tmp_path)
    revision = str(current.repository_service.status()["revision"])

    scan = current.security_scan(revision)

    assert scan["remote_ai_allowed"] is False
    assert secret not in str(scan)
    with pytest.raises(RepositoryWebError) as raised:
        current.generate(
            revision=revision,
            scan_id=str(scan["scan_id"]),
            context=None,
        )
    assert raised.value.code == "security_blocked"


def test_commit_requires_effective_git_identity(tmp_path: Path, monkeypatch) -> None:
    root = repository(tmp_path / "repo")
    git(root, "config", "--unset", "user.name")
    git(root, "config", "--unset", "user.email")
    home = tmp_path / "empty-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    (root / "feature.py").write_text("enabled = True\n", encoding="utf-8")
    git(root, "add", "--", "feature.py")
    current = service(root, tmp_path)
    revision = str(current.repository_service.status()["revision"])
    scan = current.security_scan(revision)
    generated = current.generate(
        revision=revision,
        scan_id=str(scan["scan_id"]),
        context=None,
    )

    with pytest.raises(RepositoryWebError) as raised:
        current.commit(
            generation_id=str(generated["generation_id"]),
            revision=revision,
            selected_candidate="standard",
            subject="feat(core): 增加功能开关",
            body=[],
            footer=[],
            confirmed=True,
        )

    assert raised.value.code == "git_identity_missing"
