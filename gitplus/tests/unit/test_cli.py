import pytest
from typer.testing import CliRunner

from gitplus.cli import app, main

runner = CliRunner()


def test_help_lists_stage_one_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ["init", "commit", "check", "weekly", "worklog", "history", "config", "notify"]:
        assert command in result.output


def test_version_option() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "gitplus 0.1.0" in result.output


def test_console_script_main_entrypoint(monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["gitplus", "--version"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_commit_command_reports_non_git_or_empty_state() -> None:
    result = runner.invoke(app, ["commit", "--lang", "zh-CN", "--format", "conventional", "--no-body"])

    assert result.exit_code == 1


def test_worklog_subcommands_help() -> None:
    result = runner.invoke(app, ["worklog", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list", "show", "edit", "delete"]:
        assert command in result.output
