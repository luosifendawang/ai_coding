"""Read, validate, preview, and atomically save Web configuration."""

from __future__ import annotations

import os
import stat
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from gitplus.config import (
    GitPlusConfig,
    default_config,
    user_config_path,
    user_secrets_path,
)
from gitplus.web.schemas.config import ConfigUpdateRequest, SecretUpdateAction
from gitplus.web.services.config_backup_service import ConfigBackupService
from gitplus.web.services.config_diff_service import ConfigDiffService


@dataclass(frozen=True)
class ConfigPaths:
    project_root: Path
    legacy_user_config: Path
    user_config: Path
    secrets: Path

    @classmethod
    def create(
        cls,
        project_root: Path,
        *,
        user_path: Path | None = None,
        secrets_path: Path | None = None,
        legacy_user_path: Path | None = None,
    ) -> ConfigPaths:
        root = project_root.resolve()
        return cls(
            project_root=root,
            legacy_user_config=(
                legacy_user_path
                or (
                    # Read the previous top-level file only for migration.
                    Path("~/.gitplus/config.yml").expanduser()
                    if user_path is None
                    else user_path.parent / "legacy-config.yml"
                )
            ).expanduser(),
            user_config=(user_path or user_config_path()).expanduser(),
            secrets=(secrets_path or user_secrets_path()).expanduser(),
        )


class ConfigConflictError(Exception):
    """Raised when configuration changed after the page was loaded."""


class ConfigWebService:
    """Manage the global gitplus configuration and user secrets."""

    def __init__(
        self,
        project_root: Path,
        *,
        user_path: Path | None = None,
        secrets_path: Path | None = None,
        backup_service: ConfigBackupService | None = None,
        legacy_user_path: Path | None = None,
    ) -> None:
        self.paths = ConfigPaths.create(
            project_root,
            user_path=user_path,
            secrets_path=secrets_path,
            legacy_user_path=legacy_user_path,
        )
        self.backups = backup_service or ConfigBackupService()
        self.diff = ConfigDiffService()

    def get_effective_config(self) -> dict[str, object]:
        layers = self._layers()
        merged: dict[str, object] = {}
        for _, layer in layers:
            self._deep_merge(merged, layer)
        secrets = self._read_yaml(self.paths.secrets)
        ai_secret = self._nested_get(secrets, "ai.api_key")
        if isinstance(ai_secret, str):
            self._nested_set(merged, "ai.api_key", ai_secret)
        config = GitPlusConfig.model_validate(merged)
        serialized = config.model_dump(mode="json")
        ai = serialized.get("ai")
        if isinstance(ai, dict):
            ai.pop("api_key", None)

        source_map: dict[str, str] = {
            path: "default"
            for path in self.diff.flatten(default_config().model_dump(mode="json"))
        }
        for source, layer in layers:
            for path in self.diff.flatten(layer):
                source_map[path] = source

        secret_source: str | None = None
        env_ai_secret = bool(os.getenv(config.ai.api_key_env))
        if isinstance(ai_secret, str):
            secret_source = "user_secret"
        elif env_ai_secret:
            secret_source = "environment"
        return {
            "config": serialized,
            "sources": source_map,
            "secrets": {
                "ai.api_key": {
                    "configured": bool(ai_secret or env_ai_secret),
                    "source": secret_source,
                },
            },
            "revision": self.revision(),
            # This is display-only repository context. It is not a
            # configuration layer and cannot change the effective settings.
            "project": {
                "name": self.paths.project_root.name,
                "root": str(self.paths.project_root),
            },
            "configuration": {
                "path": str(self.paths.user_config),
                "loaded_at": self._latest_mtime(),
            },
        }

    def sources(self) -> dict[str, object]:
        mode = (
            stat.S_IMODE(self.paths.secrets.stat().st_mode)
            if self.paths.secrets.exists()
            else None
        )
        return {
            "default": {"exists": True},
            "user": self._path_status(self.paths.user_config),
            "secrets": {
                **self._path_status(self.paths.secrets),
                "permission_secure": mode in {None, 0o600},
            },
            "priority": ["default", "legacy_user", "user", "environment", "cli"],
        }

    def validate_update(self, request: ConfigUpdateRequest) -> dict[str, object]:
        try:
            effective = self._effective_for_request(request)
            config = GitPlusConfig.model_validate(effective)
            warnings = self._warnings(request, config)
            return {
                "valid": True,
                "warnings": warnings,
                "errors": [],
                "normalized_config": self._sanitize(config.model_dump(mode="json")),
            }
        except ValidationError as exc:
            errors = [
                {
                    "path": self._validation_error_path(item),
                    "message": item["msg"],
                }
                for item in exc.errors(include_url=False, include_input=False)
            ]
            return {
                "valid": False,
                "warnings": [],
                "errors": errors,
                "normalized_config": {},
            }
        except (ValueError, OSError) as exc:
            return {
                "valid": False,
                "warnings": [],
                "errors": [{"path": "config", "message": str(exc)}],
                "normalized_config": {},
            }

    def _validation_error_path(self, error: Mapping[str, Any]) -> str:
        loc = error.get("loc", ())
        path = ".".join(str(part) for part in loc) if isinstance(loc, tuple) else ""
        message = str(error.get("msg", ""))
        if "." not in path:
            candidate = message.removeprefix("Value error, ").split(" ", 1)[0]
            if candidate.startswith(path + "."):
                return candidate
        return path

    def config_for_request(self, request: ConfigUpdateRequest) -> GitPlusConfig:
        """Return validated effective config for an unsaved form request."""
        config = GitPlusConfig.model_validate(self._effective_for_request(request))
        self._validate_paths(config)
        return config

    def preview_update(self, request: ConfigUpdateRequest) -> dict[str, object]:
        validation = self.validate_update(request)
        if not validation["valid"]:
            return {**validation, "changes": [], "restart_required": []}
        current = self._read_yaml(self.paths.user_config)
        updated = self._updated_global_config(request)
        changes = self.diff.compare(current, updated, source="user")
        for path, update in request.secret_updates.items():
            if update.action == SecretUpdateAction.KEEP:
                continue
            current_status = bool(
                self._nested_get(self._read_yaml(self.paths.secrets), path)
            )
            label = (
                "已替换"
                if current_status and update.action == SecretUpdateAction.REPLACE
                else (
                    "已配置"
                    if update.action == SecretUpdateAction.REPLACE
                    else "已删除"
                )
            )
            changes.append(
                {
                    "path": path,
                    "old": "已配置" if current_status else "未配置",
                    "new": label,
                    "source": "user_secret",
                }
            )
        restart = [
            item["path"]
            for item in changes
            if item["path"] in {"web.port", "web.debug"}
        ]
        return {
            "valid": True,
            "warnings": validation["warnings"],
            "errors": [],
            "changes": changes,
            "restart_required": restart,
        }

    def save_update(self, request: ConfigUpdateRequest) -> dict[str, object]:
        if request.revision != self.revision():
            raise ConfigConflictError
        validation = self.validate_update(request)
        if not validation["valid"]:
            raise ValueError("配置校验失败")
        if validation["warnings"] and not request.confirmed:
            raise ValueError("存在需要确认的安全警告")

        target = self.paths.user_config
        updated = self._updated_global_config(request)
        secrets = self._updated_secrets(request)
        target_bytes = self._dump_yaml(updated)
        secret_bytes = self._dump_yaml(secrets)
        GitPlusConfig.model_validate(self._effective_for_request(request))

        originals = {
            target: target.read_bytes() if target.exists() else None,
            self.paths.secrets: self.paths.secrets.read_bytes()
            if self.paths.secrets.exists()
            else None,
        }
        self.backups.create_backup(target)
        self.backups.create_backup(self.paths.secrets, secret=True)
        try:
            self.backups.atomic_write(self.paths.secrets, secret_bytes, secret=True)
            self.backups.atomic_write(target, target_bytes)
            self.get_effective_config()
        except Exception:
            self._rollback(originals)
            raise
        keep = GitPlusConfig.model_validate(
            self._effective_for_request(request)
        ).web.config_backup_count
        self.backups.cleanup_old_backups(target, keep)
        self.backups.cleanup_old_backups(self.paths.secrets, keep)
        return self.get_effective_config()

    def restore_latest(self) -> dict[str, object]:
        target = self.paths.user_config
        backup = self.backups.latest_backup(target)
        if backup is None:
            raise FileNotFoundError("没有可恢复的配置备份")
        self.backups.restore_backup(backup, target)
        return self.get_effective_config()

    def revision(self) -> str:
        digest = sha256()
        for path in (
            self.paths.user_config,
            self.paths.secrets,
        ):
            digest.update(str(path).encode())
            if path.exists():
                digest.update(path.read_bytes())
                digest.update(str(path.stat().st_mtime_ns).encode())
            else:
                digest.update(b"missing")
        return f"sha256:{digest.hexdigest()}"

    def secret_value(self, path: str) -> str | None:
        value = self._nested_get(self._read_yaml(self.paths.secrets), path)
        if isinstance(value, str):
            return value
        for _source, layer in reversed(self._layers()):
            value = self._nested_get(layer, path)
            if isinstance(value, str):
                return value
        return None

    def _layers(self) -> list[tuple[str, dict[str, object]]]:
        return [
            ("legacy_user", self._read_yaml(self.paths.legacy_user_config)),
            ("user", self._read_yaml(self.paths.user_config)),
        ]

    def _effective_for_request(self, request: ConfigUpdateRequest) -> dict[str, object]:
        merged: dict[str, object] = {}
        for source, layer in self._layers():
            if source == "user":
                layer = self._updated_global_config(request)
            self._deep_merge(merged, layer)
        secrets = self._updated_secrets(request)
        ai_secret = self._nested_get(secrets, "ai.api_key")
        if isinstance(ai_secret, str):
            self._nested_set(merged, "ai.api_key", ai_secret)
        return merged

    def _updated_global_config(self, request: ConfigUpdateRequest) -> dict[str, object]:
        updated = deepcopy(self._read_yaml(self.paths.user_config))
        forbidden = {"ai.api_key"}
        if forbidden & set(self.diff.flatten(request.config)):
            raise ValueError("Secret 必须通过 secret_updates 修改")
        self._deep_merge(updated, request.config)
        for path in request.inherit:
            self._nested_delete(updated, path)
        return updated

    def _updated_secrets(self, request: ConfigUpdateRequest) -> dict[str, object]:
        secrets = deepcopy(self._read_yaml(self.paths.secrets))
        allowed = {"ai.api_key"}
        for path, update in request.secret_updates.items():
            if path not in allowed:
                raise ValueError(f"不支持的 Secret 字段：{path}")
            if update.action == SecretUpdateAction.REPLACE and update.value is not None:
                self._nested_set(secrets, path, update.value.get_secret_value())
            elif update.action == SecretUpdateAction.DELETE:
                self._nested_delete(secrets, path)
        return secrets

    def _warnings(
        self, request: ConfigUpdateRequest, config: GitPlusConfig
    ) -> list[str]:
        warnings: list[str] = []
        if not config.security.enabled:
            warnings.append("关闭安全扫描可能将 Token、密码或私钥发送到远程模型。")
        if config.storage.store_raw_diff:
            warnings.append("保存原始 Diff 可能增加敏感代码落盘风险。")
        if config.web.debug:
            warnings.append("Debug 模式会记录更多诊断信息。")
        if any(
            update.action != SecretUpdateAction.KEEP
            for update in request.secret_updates.values()
        ):
            warnings.append("Secret 将保存到用户级凭证文件，而不是项目仓库。")
        self._validate_paths(config)
        return warnings

    def _validate_paths(self, config: GitPlusConfig) -> None:
        database = Path(config.storage.database).expanduser()
        if database.exists() and database.is_dir():
            raise ValueError("storage.database 不能指向目录")
        report_dir = Path(config.storage.report_dir).expanduser()
        resolved_report = (
            report_dir.resolve()
            if report_dir.is_absolute()
            else (self.paths.project_root / report_dir).resolve()
        )
        git_dir = (self.paths.project_root / ".git").resolve()
        if resolved_report == git_dir or git_dir in resolved_report.parents:
            raise ValueError("storage.report_dir 不能位于 .git 目录中")

    def _rollback(self, originals: dict[Path, bytes | None]) -> None:
        for path, content in originals.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                self.backups.atomic_write(
                    path, content, secret=path == self.paths.secrets
                )

    def _path_status(self, path: Path) -> dict[str, object]:
        parent = path.parent if not path.exists() else path
        return {
            "path": str(path),
            "exists": path.exists(),
            "writable": os.access(parent, os.W_OK),
        }

    def _latest_mtime(self) -> str | None:
        values = [
            path.stat().st_mtime
            for path in (
                self.paths.user_config,
                self.paths.secrets,
            )
            if path.exists()
        ]
        if not values:
            return None
        from datetime import datetime, timezone

        return datetime.fromtimestamp(max(values), tz=timezone.utc).isoformat()

    def _read_yaml(self, path: Path) -> dict[str, object]:
        if not path.exists():
            return {}
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise TypeError(f"配置文件必须是 YAML 对象：{path}")
        return loaded

    def _dump_yaml(self, value: dict[str, object]) -> bytes:
        text = yaml.safe_dump(value, allow_unicode=True, sort_keys=False)
        parsed = yaml.safe_load(text) or {}
        if not isinstance(parsed, dict):
            raise TypeError("生成的配置无法重新解析")
        return text.encode("utf-8")

    def _sanitize(self, value: dict[str, Any]) -> dict[str, Any]:
        sanitized = deepcopy(value)
        ai = sanitized.get("ai")
        if isinstance(ai, dict):
            ai.pop("api_key", None)
        return sanitized

    def _deep_merge(self, base: dict[str, object], update: dict[str, object]) -> None:
        for key, value in update.items():
            current = base.get(key)
            if isinstance(current, dict) and isinstance(value, dict):
                self._deep_merge(current, value)
            else:
                base[key] = deepcopy(value)

    def _nested_get(self, data: dict[str, object], path: str) -> object | None:
        current: object = data
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def _nested_set(self, data: dict[str, object], path: str, value: object) -> None:
        current = data
        parts = path.split(".")
        for part in parts[:-1]:
            child = current.setdefault(part, {})
            if not isinstance(child, dict):
                child = {}
                current[part] = child
            current = child
        current[parts[-1]] = value

    def _nested_delete(self, data: dict[str, object], path: str) -> None:
        parts = path.split(".")
        current = data
        parents: list[tuple[dict[str, object], str]] = []
        for part in parts[:-1]:
            child = current.get(part)
            if not isinstance(child, dict):
                return
            parents.append((current, part))
            current = child
        current.pop(parts[-1], None)
        for parent, key in reversed(parents):
            child = parent.get(key)
            if isinstance(child, dict) and not child:
                parent.pop(key, None)
