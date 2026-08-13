"""Prompt file loading and safe template rendering."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

from gitplus.exceptions import PromptTemplateError


class PromptLoader:
    """Load prompt templates and replace explicit placeholders only."""

    def __init__(self, prompt_dir: Path | None = None) -> None:
        self.prompt_dir = prompt_dir

    def load(self, name: str) -> str:
        if self.prompt_dir is not None:
            path = self.prompt_dir / name
            if not path.exists():
                raise PromptTemplateError(f"Prompt 文件不存在：{name}")
            return path.read_text(encoding="utf-8")
        try:
            return files("gitplus.prompts").joinpath(name).read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise PromptTemplateError(f"Prompt 文件不存在：{name}") from exc

    def render(self, name: str, variables: dict[str, str]) -> str:
        template = self.load(name)
        missing = [
            part.split("}}", 1)[0].strip()
            for part in template.split("{{")[1:]
            if "}}" in part and part.split("}}", 1)[0].strip() not in variables
        ]
        if missing:
            raise PromptTemplateError(f"Prompt 模板缺少变量：{', '.join(sorted(set(missing)))}")
        rendered = template
        for key, value in variables.items():
            rendered = rendered.replace("{{ " + key + " }}", value)
            rendered = rendered.replace("{{" + key + "}}", value)
        return rendered
