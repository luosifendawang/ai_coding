"""AI request and response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AIMessage(BaseModel):
    role: str
    content: str


class AIRequest(BaseModel):
    messages: list[AIMessage]
    model: str
    temperature: float
    top_p: float
    max_output_tokens: int
    response_schema: dict[str, object] | None = None


class AIResponse(BaseModel):
    content: str
    model: str | None = None
    request_id: str | None = None
    finish_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int | None = None


class ProviderCallRecord(BaseModel):
    request: AIRequest
    response: AIResponse | None = None

