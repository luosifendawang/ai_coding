"""LLM provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gitpulse.models.ai import AIRequest, AIResponse


class LLMProvider(ABC):
    """Common interface for all language model providers."""

    name: str = "unknown"

    @property
    @abstractmethod
    def is_local(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        raise NotImplementedError

