"""Risk and security scan models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(str, Enum):
    SECRET = "secret"
    CREDENTIAL = "credential"
    PRIVATE_KEY = "private_key"
    DATABASE_URL = "database_url"
    CLOUD_CONNECTION = "cloud_connection"
    INTERNAL_NETWORK = "internal_network"
    PERSONAL_INFORMATION = "personal_information"
    LOCAL_PATH = "local_path"
    USER_NAME = "user_name"
    DEBUG_CONTENT = "debug_content"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class SecurityLocation(BaseModel):
    patch_line: int | None = None
    old_file_line: int | None = None
    new_file_line: int | None = None


class SecurityFinding(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    category: RiskCategory
    level: RiskLevel
    file_path: str | None = None
    line_number: int | None = None
    column_start: int | None = None
    column_end: int | None = None
    location: SecurityLocation = Field(default_factory=SecurityLocation)
    description: str
    masked_value: str | None = None
    suggestion: str | None = None
    confidence: float = 1.0
    blocks_remote_model: bool = False


class SecurityScanSummary(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0
    files_scanned: int = 0
    files_with_findings: int = 0
    total_findings: int = 0


class MaskMapping(BaseModel):
    placeholder: str
    category: str
    masked_value: str
    occurrence_count: int = 1


class MaskingResult(BaseModel):
    original_length: int
    masked_length: int
    masked_text: str
    mappings: list[MaskMapping] = Field(default_factory=list)


class SecurityScanResult(BaseModel):
    passed: bool
    scan_completed: bool
    block_remote_model: bool
    summary: SecurityScanSummary
    findings: list[SecurityFinding] = Field(default_factory=list)
    sanitized_diff: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

