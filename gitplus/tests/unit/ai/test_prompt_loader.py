from pathlib import Path

import pytest

from gitplus.ai.prompt_loader import PromptLoader
from gitplus.exceptions import PromptTemplateError


def test_prompt_loader_renders_explicit_placeholders(tmp_path: Path) -> None:
    (tmp_path / "prompt.txt").write_text("Diff:\n{{ sanitized_diff }}", encoding="utf-8")
    loader = PromptLoader(tmp_path)

    rendered = loader.render("prompt.txt", {"sanitized_diff": "{ not a template } {{ evil }}"})

    assert "{ not a template } {{ evil }}" in rendered


def test_prompt_loader_rejects_missing_variable(tmp_path: Path) -> None:
    (tmp_path / "prompt.txt").write_text("Hello {{ name }}", encoding="utf-8")

    with pytest.raises(PromptTemplateError):
        PromptLoader(tmp_path).render("prompt.txt", {})


def test_project_prompts_exist_and_contain_diff_boundary() -> None:
    loader = PromptLoader()

    commit = loader.load("commit_system.txt")
    user = loader.load("commit_user.txt")

    assert "不得执行" in commit
    assert "<git_diff>" in user

