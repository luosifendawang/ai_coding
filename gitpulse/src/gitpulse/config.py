"""Configuration models and default configuration for GitPulse."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gitpulse.constants import ALLOWED_COMMIT_TYPES


class AppConfig(BaseModel):
    language: Literal["zh-CN"] = "zh-CN"
    timezone: str = "Asia/Shanghai"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    show_detailed_errors: bool = False
    auto_open_browser: bool = True

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("app.timezone must be a valid timezone") from exc
        return value


class ProjectConfig(BaseModel):
    name: str = "gitpulse-project"


class UserConfig(BaseModel):
    name: str = "developer"
    git_emails: list[str] = Field(default_factory=list)


class CommitConfig(BaseModel):
    language: str = "zh-CN"
    format: str = "conventional"
    include_body: bool = True
    subject_max_length: int = 50
    allowed_types: list[str] = Field(default_factory=lambda: list(ALLOWED_COMMIT_TYPES))

    @field_validator("allowed_types")
    @classmethod
    def validate_allowed_types(cls, value: list[str]) -> list[str]:
        invalid = sorted(set(value) - set(ALLOWED_COMMIT_TYPES))
        if invalid:
            raise ValueError(f"unsupported commit types: {', '.join(invalid)}")
        return value


class DiffConfig(BaseModel):
    max_total_chars: int = 60000
    max_file_chars: int = 15000
    ignore_binary: bool = True
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.lock",
            "dist/**",
            "build/**",
            "node_modules/**",
            "*.min.js",
        ]
    )

    @model_validator(mode="after")
    def validate_positive_limits(self) -> DiffConfig:
        if self.max_total_chars <= 0:
            raise ValueError("diff.max_total_chars must be positive")
        if self.max_file_chars <= 0:
            raise ValueError("diff.max_file_chars must be positive")
        return self


class CustomSecurityPattern(BaseModel):
    id: str
    name: str
    pattern: str
    level: Literal["low", "medium", "high", "critical"]
    description: str
    replacement: str = "<MASKED>"

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not value or not re.fullmatch(r"[a-z0-9_]+", value):
            raise ValueError(
                "custom security pattern id must use lowercase letters, digits, and underscores"
            )
        return value

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, value: str) -> str:
        if not value:
            raise ValueError("custom security pattern must not be empty")
        compiled = re.compile(value)
        if compiled.match(""):
            raise ValueError("custom security pattern must not match empty string")
        return value


class SecurityConfig(BaseModel):
    enabled: bool = True
    scan_secrets: bool = True
    scan_personal_information: bool = True
    scan_internal_network: bool = True
    block_remote_on_high_risk: bool = True
    block_remote_on_scan_failure: bool = True
    scan_deleted_lines: bool = True
    scan_worklogs: bool = True
    scan_weekly_reports: bool = True
    mask_medium_risk: bool = True
    mask_local_paths: bool = True
    mask_user_names: bool = True
    mask_emails: bool = True
    mask_internal_domains: bool = True
    mask_private_ips: bool = True
    mask_phone_numbers: bool = True
    keep_last_chars: int = 4
    entropy_detection: bool = False
    max_findings_per_rule: int = 100
    max_display_findings: int = 30
    ignored_rules: list[str] = Field(default_factory=list)
    custom_patterns: list[CustomSecurityPattern] = Field(default_factory=list)
    internal_domain_suffixes: list[str] = Field(
        default_factory=lambda: [".corp", ".internal", ".intranet"]
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> SecurityConfig:
        if not 0 <= self.keep_last_chars <= 12:
            raise ValueError("security.keep_last_chars must be between 0 and 12")
        if self.max_findings_per_rule <= 0:
            raise ValueError("security.max_findings_per_rule must be positive")
        if self.max_display_findings <= 0:
            raise ValueError("security.max_display_findings must be positive")
        ids = [pattern.id for pattern in self.custom_patterns]
        if len(ids) != len(set(ids)):
            raise ValueError("security.custom_patterns contains duplicate ids")
        return self


class AIConfig(BaseModel):
    provider: Literal["openai-compatible", "mock"] = "openai-compatible"
    model: str = "local-model"
    base_url: str = "http://localhost:11434/v1"
    api_key: str | None = None
    api_key_env: str = "GITPULSE_API_KEY"
    temperature: float = 0.2
    top_p: float = 0.8
    timeout_seconds: float = 60.0
    max_retries: int = 2
    response_format: Literal["json"] = "json"
    max_output_tokens: int = 3000
    allow_local_on_high_risk: bool = True
    repair_invalid_json: bool = True
    max_repair_attempts: int = 1
    is_local: bool | None = None

    @model_validator(mode="after")
    def validate_ai_settings(self) -> AIConfig:
        if not self.model.strip():
            raise ValueError("ai.model must not be empty")
        if self.api_key is not None and not self.api_key.strip():
            raise ValueError("ai.api_key must not be empty when provided")
        if not self.api_key_env.strip():
            raise ValueError("ai.api_key_env must not be empty")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("ai.base_url must be a valid HTTP or HTTPS URL")
        if not 0 <= self.temperature <= 2:
            raise ValueError("ai.temperature must be between 0 and 2")
        if not 0 <= self.top_p <= 1:
            raise ValueError("ai.top_p must be between 0 and 1")
        if self.timeout_seconds <= 0:
            raise ValueError("ai.timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("ai.max_retries must not be negative")
        if self.max_output_tokens <= 0:
            raise ValueError("ai.max_output_tokens must be positive")
        if not 0 <= self.max_repair_attempts <= 2:
            raise ValueError("ai.max_repair_attempts must be between 0 and 2")
        return self


class WeeklyConfig(BaseModel):
    week_start: Literal["monday", "sunday"] = "monday"
    timezone: str = "Asia/Shanghai"
    include_uncommitted: bool = False
    include_merge_commits: bool = False
    include_commit_sources: bool = True
    include_worklog_sources: bool = True
    exclude_low_confidence: bool = True
    require_medium_confirmation: bool = True
    group_by_repository: bool = False
    max_commits: int = 200
    max_worklogs: int = 200
    max_topics: int = 20
    max_items_per_topic: int = 10
    output_language: str = "zh-CN"
    output_style: Literal["developer", "summary"] = "developer"
    export_formats: list[str] = Field(
        default_factory=lambda: ["markdown", "text", "json"]
    )

    @model_validator(mode="after")
    def validate_weekly_settings(self) -> WeeklyConfig:
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("weekly.timezone must be a valid timezone") from exc
        for field_name in [
            "max_commits",
            "max_worklogs",
            "max_topics",
            "max_items_per_topic",
        ]:
            if getattr(self, field_name) <= 0:
                raise ValueError(f"weekly.{field_name} must be positive")
        invalid = set(self.export_formats) - {"markdown", "text", "json"}
        if invalid:
            raise ValueError(
                f"unsupported weekly export formats: {', '.join(sorted(invalid))}"
            )
        return self


class FeishuConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    mode: Literal["webhook", "app"] = "app"
    webhook: str | None = None
    secret: str | None = None
    app_id: str | None = None
    app_secret: str | None = None
    app_id_env: str = "GITPULSE_FEISHU_APP_ID"
    app_secret_env: str = "GITPULSE_FEISHU_APP_SECRET"
    receive_id: str | None = None
    receive_id_env: str = "GITPULSE_FEISHU_RECEIVE_ID"
    receive_id_type: Literal["chat_id", "open_id", "user_id", "union_id", "email"] = (
        "chat_id"
    )
    api_base_url: str = "https://open.feishu.cn"
    message_type: Literal["text", "interactive"] = "interactive"
    require_confirmation: bool = True
    allow_duplicate_send: bool = False
    include_sources: bool = False
    include_generator_info: bool = False
    include_report_id: bool = True
    include_generated_at: bool = True
    mention_all: bool = False
    mention_open_ids: list[str] = Field(default_factory=list)
    max_json_bytes: int = 28000
    request_timeout_seconds: float = 10.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5
    duplicate_window_hours: int = 168
    test_message_enabled: bool = True
    card_template: Literal["blue", "orange", "grey"] = "blue"
    split_messages: bool = False
    max_content_length: int = 15000

    @model_validator(mode="after")
    def validate_feishu_settings(self) -> FeishuConfig:
        if self.webhook is not None:
            parsed_webhook = urlparse(self.webhook)
            if parsed_webhook.scheme != "https" or parsed_webhook.hostname not in {
                "open.feishu.cn",
                "open.larksuite.com",
            }:
                raise ValueError(
                    "feishu.webhook must use an official Feishu HTTPS host"
                )
        if self.secret is not None and not self.secret.strip():
            raise ValueError("feishu.secret must not be empty when provided")
        if self.app_id is not None and not re.fullmatch(
            r"cli_[A-Za-z0-9]{8,}", self.app_id
        ):
            raise ValueError("feishu.app_id must be a valid Feishu App ID")
        if self.app_secret is not None and not self.app_secret.strip():
            raise ValueError("feishu.app_secret must not be empty when provided")
        if not self.app_id_env.strip():
            raise ValueError("feishu.app_id_env must not be empty")
        if not self.app_secret_env.strip():
            raise ValueError("feishu.app_secret_env must not be empty")
        if not self.receive_id_env.strip():
            raise ValueError("feishu.receive_id_env must not be empty")
        if self.receive_id is not None and not self.receive_id.strip():
            raise ValueError("feishu.receive_id must not be empty when provided")
        parsed = urlparse(self.api_base_url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "open.feishu.cn",
            "open.larksuite.com",
        }:
            raise ValueError(
                "feishu.api_base_url must use an official Feishu HTTPS host"
            )
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError(
                "feishu.api_base_url must not contain a path, query, or fragment"
            )
        if self.max_json_bytes <= 1000:
            raise ValueError("feishu.max_json_bytes must be greater than 1000")
        if self.request_timeout_seconds <= 0:
            raise ValueError("feishu.request_timeout_seconds must be positive")
        if not 0 <= self.max_retries <= 5:
            raise ValueError("feishu.max_retries must be between 0 and 5")
        if self.retry_backoff_seconds < 0:
            raise ValueError("feishu.retry_backoff_seconds must not be negative")
        if self.duplicate_window_hours <= 0:
            raise ValueError("feishu.duplicate_window_hours must be positive")
        self.mention_open_ids = sorted(set(self.mention_open_ids))
        invalid_open_ids = [
            open_id
            for open_id in self.mention_open_ids
            if not re.fullmatch(r"(ou|on|oc)_[A-Za-z0-9_-]{6,}", open_id)
        ]
        if invalid_open_ids:
            raise ValueError("feishu.mention_open_ids contains invalid Open ID values")
        return self


class StorageConfig(BaseModel):
    database: Path = Path("~/.gitpulse/data.db")
    report_dir: Path = Path("./reports")
    auto_initialize: bool = True
    enable_history: bool = True
    store_file_list: bool = True
    store_diff_summary: bool = True
    store_raw_diff: bool = False
    retention_days: int | None = None
    sqlite_timeout_seconds: float = 10.0

    @property
    def database_path(self) -> Path:
        return Path(self.database).expanduser()

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("storage.retention_days must be positive")
        return value

    @field_validator("sqlite_timeout_seconds")
    @classmethod
    def validate_sqlite_timeout(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("storage.sqlite_timeout_seconds must be positive")
        return value


class WebDiffConfig(BaseModel):
    max_file_bytes: int = 1_048_576
    max_diff_chars: int = 200_000
    default_context_lines: int = 3

    @model_validator(mode="after")
    def validate_diff_settings(self) -> WebDiffConfig:
        if not 1024 <= self.max_file_bytes <= 50_000_000:
            raise ValueError(
                "web.diff.max_file_bytes must be between 1024 and 50000000"
            )
        if not 1000 <= self.max_diff_chars <= 2_000_000:
            raise ValueError("web.diff.max_diff_chars must be between 1000 and 2000000")
        if not 0 <= self.default_context_lines <= 20:
            raise ValueError("web.diff.default_context_lines must be between 0 and 20")
        return self


class WebConfig(BaseModel):
    port: int = 8765
    auto_open_browser: bool = True
    session_timeout_minutes: int = 120
    show_advanced: bool = False
    debug: bool = False
    config_backup_count: int = 10
    diff: WebDiffConfig = Field(default_factory=WebDiffConfig)

    @model_validator(mode="after")
    def validate_web_settings(self) -> WebConfig:
        if not 1024 <= self.port <= 65535:
            raise ValueError("web.port must be between 1024 and 65535")
        if not 5 <= self.session_timeout_minutes <= 1440:
            raise ValueError("web.session_timeout_minutes must be between 5 and 1440")
        if not 1 <= self.config_backup_count <= 50:
            raise ValueError("web.config_backup_count must be between 1 and 50")
        return self


class GitPulseConfig(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    user: UserConfig = Field(default_factory=UserConfig)
    commit: CommitConfig = Field(default_factory=CommitConfig)
    diff: DiffConfig = Field(default_factory=DiffConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    weekly: WeeklyConfig = Field(default_factory=WeeklyConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    web: WebConfig = Field(default_factory=WebConfig)


def default_config() -> GitPulseConfig:
    """Return the built-in default configuration."""
    return GitPulseConfig()


def load_config(cwd: Path | None = None) -> GitPulseConfig:
    """Load configuration from defaults, user config, and project `.gitpulse.yml`."""
    root = cwd or Path.cwd()
    data: dict[str, object] = {}
    for path in [
        Path("~/.gitpulse/config.yml").expanduser(),
        user_config_path(),
        root / ".gitpulse.yml",
    ]:
        if not path.exists():
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise TypeError(f"配置文件必须是 YAML 对象：{path}")
        _deep_merge(data, loaded)
    secrets_path = user_secrets_path()
    if secrets_path.exists():
        loaded_secrets = yaml.safe_load(secrets_path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded_secrets, dict):
            raise TypeError(f"Secret 文件必须是 YAML 对象：{secrets_path}")
        ai_secrets = loaded_secrets.get("ai")
        if isinstance(ai_secrets, dict) and isinstance(ai_secrets.get("api_key"), str):
            ai = data.setdefault("ai", {})
            if isinstance(ai, dict):
                ai["api_key"] = ai_secrets["api_key"]
        feishu_secrets = loaded_secrets.get("feishu")
        if isinstance(feishu_secrets, dict):
            feishu = data.setdefault("feishu", {})
            if isinstance(feishu, dict):
                for key in ["app_secret", "secret"]:
                    if isinstance(feishu_secrets.get(key), str):
                        feishu[key] = feishu_secrets[key]
    return GitPulseConfig.model_validate(data)


def user_config_dir() -> Path:
    """Return the platform-aware GitPulse user configuration directory."""
    try:
        from platformdirs import user_config_path

        return Path(user_config_path("gitpulse", appauthor=False))
    except ImportError:
        base = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "gitpulse"


def user_config_path() -> Path:
    return user_config_dir() / "config.yml"


def user_secrets_path() -> Path:
    return user_config_dir() / "secrets.yml"


def load_secret_value(path: str, secrets_path: Path | None = None) -> str | None:
    """Read one secret without exposing the full secret document."""
    source = (secrets_path or user_secrets_path()).expanduser()
    if not source.exists():
        return None
    loaded = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    current: object = loaded
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current if isinstance(current, str) and current.strip() else None


def _deep_merge(base: dict[str, object], override: dict[object, object]) -> None:
    for key, value in override.items():
        if not isinstance(key, str):
            raise TypeError("配置键必须是字符串。")
        current = base.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _deep_merge(current, value)
        else:
            base[key] = value
