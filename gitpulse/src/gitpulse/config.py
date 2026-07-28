"""Configuration models and default configuration for GitPulse."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator
import yaml

from gitpulse.constants import ALLOWED_COMMIT_TYPES


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
        default_factory=lambda: ["*.lock", "dist/**", "build/**", "node_modules/**", "*.min.js"]
    )

    @model_validator(mode="after")
    def validate_positive_limits(self) -> "DiffConfig":
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
            raise ValueError("custom security pattern id must use lowercase letters, digits, and underscores")
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
    internal_domain_suffixes: list[str] = Field(default_factory=lambda: [".corp", ".internal", ".intranet"])

    @model_validator(mode="after")
    def validate_security_settings(self) -> "SecurityConfig":
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
    def validate_ai_settings(self) -> "AIConfig":
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
    export_formats: list[str] = Field(default_factory=lambda: ["markdown", "text", "json"])

    @model_validator(mode="after")
    def validate_weekly_settings(self) -> "WeeklyConfig":
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("weekly.timezone must be a valid timezone") from exc
        for field_name in ["max_commits", "max_worklogs", "max_topics", "max_items_per_topic"]:
            if getattr(self, field_name) <= 0:
                raise ValueError(f"weekly.{field_name} must be positive")
        invalid = set(self.export_formats) - {"markdown", "text", "json"}
        if invalid:
            raise ValueError(f"unsupported weekly export formats: {', '.join(sorted(invalid))}")
        return self


class FeishuConfig(BaseModel):
    enabled: bool = False
    webhook_env: str = "GITPULSE_FEISHU_WEBHOOK"
    secret_env: str = "GITPULSE_FEISHU_SECRET"
    message_type: Literal["text", "interactive"] = "interactive"
    signature_required: bool = True
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

    @model_validator(mode="before")
    @classmethod
    def reject_plain_credentials(cls, data: object) -> object:
        if isinstance(data, dict):
            forbidden = {"webhook", "secret"}
            present = sorted(forbidden & set(data))
            if present:
                raise ValueError(
                    "feishu webhook/secret must be provided by environment variables, "
                    f"not config keys: {', '.join(present)}"
                )
        return data

    @model_validator(mode="after")
    def validate_feishu_settings(self) -> "FeishuConfig":
        if not self.webhook_env.strip():
            raise ValueError("feishu.webhook_env must not be empty")
        if not self.secret_env.strip():
            raise ValueError("feishu.secret_env must not be empty")
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


class GitPulseConfig(BaseModel):
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    user: UserConfig = Field(default_factory=UserConfig)
    commit: CommitConfig = Field(default_factory=CommitConfig)
    diff: DiffConfig = Field(default_factory=DiffConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    weekly: WeeklyConfig = Field(default_factory=WeeklyConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


def default_config() -> GitPulseConfig:
    """Return the built-in default configuration."""
    return GitPulseConfig()


def load_config(cwd: Path | None = None) -> GitPulseConfig:
    """Load configuration from defaults, user config, and project `.gitpulse.yml`."""
    root = cwd or Path.cwd()
    data: dict[str, object] = {}
    for path in [Path("~/.gitpulse/config.yml").expanduser(), root / ".gitpulse.yml"]:
        if not path.exists():
            continue
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"配置文件必须是 YAML 对象：{path}")
        _deep_merge(data, loaded)
    return GitPulseConfig.model_validate(data)


def _deep_merge(base: dict[str, object], override: dict[object, object]) -> None:
    for key, value in override.items():
        if not isinstance(key, str):
            raise ValueError("配置键必须是字符串。")
        current = base.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            _deep_merge(current, value)
        else:
            base[key] = value
