"""Commit generation models."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from gitplus.constants import ALLOWED_COMMIT_TYPES
from gitplus.models.diff import DiffCollection
from gitplus.models.repository import RepositoryInfo
from gitplus.models.risk import SecurityScanResult

CommitType = Literal[
    "feat",
    "fix",
    "refactor",
    "perf",
    "test",
    "docs",
    "style",
    "build",
    "ci",
    "chore",
    "revert",
]
ConfidenceLevel = Literal["high", "medium", "low"]


class CommitRules(BaseModel):
    language: str = "zh-CN"
    format: str = "conventional"
    include_body: bool = True
    subject_max_length: int = 50
    allowed_types: list[str] = Field(default_factory=lambda: list(ALLOWED_COMMIT_TYPES))


class CommitAIFile(BaseModel):
    path: str
    old_path: str | None = None
    status: str
    additions: int = 0
    deletions: int = 0
    is_binary: bool = False
    is_truncated: bool = False


class CommitAIRequest(BaseModel):
    repository: str
    branch: str | None = None
    head_commit: str | None = None
    files: list[CommitAIFile]
    sanitized_diff: str
    stats: dict[str, int]
    commit_rules: CommitRules
    user_context: str | None = None
    security_warnings: list[str] = Field(default_factory=list)


class CommitCandidate(BaseModel):
    subject: str
    body: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("subject must not be empty")
        if "\n" in value:
            raise ValueError("subject must not contain newline")
        if value.endswith((".", "。")):
            raise ValueError("subject must not end with period")
        return value

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("body item must not be empty")
        return value


class CommitEvidence(BaseModel):
    file: str
    reason: str


class SplitTopic(BaseModel):
    title: str
    type: CommitType
    scope: str | None = None
    files: list[str] = Field(default_factory=list)
    suggested_subject: str
    reason: str | None = None


class CommitGenerationResult(BaseModel):
    primary_purpose: str
    type: CommitType
    scope: str | None = None
    subject: str
    body: list[str] = Field(default_factory=list, max_length=5)
    confidence: ConfidenceLevel
    candidates: dict[str, CommitCandidate]
    should_split: bool = False
    split_confidence: float = Field(default=0.0, ge=0, le=1)
    split_suggestions: list[SplitTopic] = Field(default_factory=list)
    evidence: list[CommitEvidence] = Field(default_factory=list, max_length=20)
    needs_confirmation: list[str] = Field(default_factory=list, max_length=10)
    validation_warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_llm_result(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data

        def normalize_body(value: object) -> object:
            if isinstance(value, str):
                stripped = value.strip()
                return [stripped] if stripped else []
            return value

        normalized = dict(data)
        if "body" in normalized:
            normalized["body"] = normalize_body(normalized["body"])
        confidence = normalized.get("confidence")
        if isinstance(confidence, (int, float)):
            normalized["confidence"] = "high" if confidence >= 0.75 else ("medium" if confidence >= 0.4 else "low")
        candidates = normalized.get("candidates")
        if isinstance(candidates, dict):
            normalized_candidates: dict[str, object] = {}
            for key, value in candidates.items():
                if isinstance(value, str):
                    normalized_candidates[key] = {"subject": value, "body": []}
                elif isinstance(value, dict):
                    candidate = dict(value)
                    if "body" in candidate:
                        candidate["body"] = normalize_body(candidate["body"])
                    normalized_candidates[key] = candidate
                else:
                    normalized_candidates[key] = value
            normalized["candidates"] = normalized_candidates
        evidence = normalized.get("evidence")
        if isinstance(evidence, list):
            normalized["evidence"] = [
                {"file": item, "reason": "AI 返回的证据文件"} if isinstance(item, str) else item
                for item in evidence
            ]
        split_suggestions = normalized.get("split_suggestions")
        if normalized.get("should_split") is True and (
            not isinstance(split_suggestions, list) or len(split_suggestions) < 2
        ):
            normalized["should_split"] = False
            warning = "AI 建议拆分提交，但未提供至少两个完整的拆分方案，已忽略该建议。"
            validation_warnings = normalized.get("validation_warnings")
            if not isinstance(validation_warnings, list):
                validation_warnings = []
            if warning not in validation_warnings:
                validation_warnings.append(warning)
            normalized["validation_warnings"] = validation_warnings

            confirmation = "暂存区可能包含多个独立修改主题，请确认是否需要拆分提交。"
            needs_confirmation = normalized.get("needs_confirmation")
            if not isinstance(needs_confirmation, list):
                needs_confirmation = []
            if confirmation not in needs_confirmation and len(needs_confirmation) < 10:
                needs_confirmation.append(confirmation)
            normalized["needs_confirmation"] = needs_confirmation
        return normalized

    @model_validator(mode="after")
    def validate_result(self) -> CommitGenerationResult:
        if not self.primary_purpose.strip():
            raise ValueError("primary_purpose must not be empty")
        CommitCandidate(subject=self.subject, body=self.body)
        required = {"concise", "standard", "detailed"}
        if set(self.candidates) & required != required:
            raise ValueError("candidates must contain concise, standard, and detailed")
        if self.scope and not re.fullmatch(r"[A-Za-z0-9_-]{1,30}", self.scope):
            raise ValueError("scope contains invalid characters")
        if self.should_split and len(self.split_suggestions) < 2:
            raise ValueError("should_split requires at least two split suggestions")
        return self


class TopicEvidence(BaseModel):
    file: str
    reason: str


class DetectedTopic(BaseModel):
    id: str
    title: str
    type: CommitType
    scope: str | None = None
    files: list[str]
    suggested_subject: str
    evidence: list[TopicEvidence] = Field(default_factory=list)


class TopicDetectionResult(BaseModel):
    should_split: bool
    confidence: float = Field(ge=0, le=1)
    reason: str
    topics: list[DetectedTopic] = Field(default_factory=list, max_length=5)
    ambiguous_files: list[str] = Field(default_factory=list)
    needs_confirmation: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_topics(self) -> TopicDetectionResult:
        if self.should_split and len(self.topics) < 2:
            raise ValueError("should_split requires at least two topics")
        return self


class CommitServiceResult(BaseModel):
    repository: RepositoryInfo
    diff: DiffCollection
    security: SecurityScanResult
    generation: CommitGenerationResult | None = None
    topic_detection: TopicDetectionResult | None = None
    ai_called: bool = False
    provider_name: str | None = None
    warnings: list[str] = Field(default_factory=list)
