"""Safe YAML config writer."""

from __future__ import annotations

import stat
from datetime import datetime, timezone
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from gitplus.config import GitPlusConfig
from gitplus.exceptions import ConfigurationError


class ConfigWriter:
    """Write gitplus configuration with backup and atomic replace."""

    def build_config(self, config: GitPlusConfig) -> dict[str, object]:
        return {
            "ai": {
                "provider": config.ai.provider,
                "model": config.ai.model,
                "base_url": config.ai.base_url,
                "api_key_env": config.ai.api_key_env,
                "is_local": config.ai.is_local,
            },
            "commit": {
                "language": config.commit.language,
                "format": config.commit.format,
            },
            "weekly": {
                "week_start": config.weekly.week_start,
                "timezone": config.weekly.timezone,
            },
            "storage": {
                "database": str(config.storage.database),
            },
        }

    def preview(self, config: GitPlusConfig) -> str:
        return yaml.safe_dump(
            self.build_config(config), allow_unicode=True, sort_keys=True
        )

    def write(self, path: Path, config: GitPlusConfig, *, backup: bool = True) -> Path:
        path = path.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if backup and existing:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            path.with_name(path.name + f".bak.{stamp}").write_text(
                existing, encoding="utf-8"
            )
        generated = self.build_config(config)
        if existing:
            current = yaml.safe_load(existing) or {}
            if isinstance(current, dict):
                generated = self._deep_merge(current, generated)
        text = yaml.safe_dump(generated, allow_unicode=True, sort_keys=True)
        parsed = yaml.safe_load(text)
        if not isinstance(parsed, dict):
            raise ConfigurationError("生成的配置无法解析。")
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.chmod(stat.S_IRUSR | stat.S_IWUSR)
        tmp.replace(path)
        return path

    def _deep_merge(
        self, base: dict[str, object], update: dict[str, object]
    ) -> dict[str, object]:
        result = dict(base)
        for key, value in update.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._deep_merge(result[key], value)  # type: ignore[arg-type]
            else:
                result[key] = value
        return result
