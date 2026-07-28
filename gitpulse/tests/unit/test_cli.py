from typer.testing import CliRunner

from gitpulse.cli import app


runner = CliRunner()


def test_help_lists_stage_one_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ["init", "commit", "check", "weekly", "worklog", "history", "config", "notify"]:
        assert command in result.output


def test_version_option() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert "GitPulse 0.1.0" in result.output


def test_commit_command_reports_non_git_or_empty_state() -> None:
    result = runner.invoke(app, ["commit", "--lang", "zh-CN", "--format", "conventional", "--no-body"])

    assert result.exit_code == 1


def test_worklog_subcommands_help() -> None:
    result = runner.invoke(app, ["worklog", "--help"])

    assert result.exit_code == 0
    for command in ["add", "list", "show", "edit", "delete"]:
        assert command in result.output
