"""AI response JSON extraction and validation."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from gitplus.exceptions import AIResponseValidationError

T = TypeVar("T", bound=BaseModel)


class AIResponseParser:
    """Extract, repair, and validate structured JSON model output."""

    def parse(self, content: str, model_type: type[T]) -> T:
        if not content or not content.strip():
            raise AIResponseValidationError("AI 响应为空。")
        json_text = self.extract_json(content)
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            json_text = self.repair_json(json_text, model_type)
            try:
                data = json.loads(json_text)
            except json.JSONDecodeError as exc:
                raise AIResponseValidationError("AI 响应不是合法 JSON。") from exc
        data = self.unwrap_common_envelope(data)
        try:
            return model_type.model_validate(data)
        except ValidationError as exc:
            raise AIResponseValidationError("AI 响应不符合结构化 Schema。") from exc

    def extract_json(self, content: str) -> str:
        text = content.strip().lstrip("\ufeff")
        fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if fence:
            return fence.group(1).strip()
        if text.startswith("{") and text.endswith("}"):
            return text
        start = text.find("{")
        if start == -1:
            raise AIResponseValidationError("AI 响应中未找到 JSON 对象。")
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        raise AIResponseValidationError("AI 响应 JSON 对象不完整。")

    def repair_json(self, content: str, _model_type: type[T]) -> str:
        repaired = content.strip()
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        return repaired

    def unwrap_common_envelope(self, data: object) -> object:
        if not isinstance(data, dict):
            return data
        for key in ["answer", "result", "data", "output"]:
            value = data.get(key)
            if isinstance(value, dict):
                return value
        return data
