"""Configuration API request and response models."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class SecretUpdateAction(str, Enum):
    KEEP = "keep"
    REPLACE = "replace"
    DELETE = "delete"


class SecretUpdate(BaseModel):
    action: SecretUpdateAction = SecretUpdateAction.KEEP
    value: SecretStr | None = None

    @model_validator(mode="after")
    def validate_action(self) -> SecretUpdate:
        if self.action == SecretUpdateAction.REPLACE:
            if self.value is None or not self.value.get_secret_value().strip():
                raise ValueError("replace 操作必须提供非空 Secret")
        elif self.value is not None:
            self.value = None
        return self


class ConfigUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config: dict[str, object] = Field(default_factory=dict)
    inherit: list[str] = Field(default_factory=list)
    secret_updates: dict[str, SecretUpdate] = Field(default_factory=dict)
    revision: str | None = None
    confirmed: bool = False


class ConfigValidationIssue(BaseModel):
    path: str
    message: str
