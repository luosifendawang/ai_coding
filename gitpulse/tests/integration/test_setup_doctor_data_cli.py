import json

from typer.testing import CliRunner

from gitpulse.cli import app

runner = CliRunner()


def test_setup_preview_and_doctor_json(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

    setup = runner.invoke(app, ["setup", "--user", "--preview"])
    doctor = runner.invoke(app, ["doctor", "--json"])

    assert setup.exit_code == 0
    assert "GITPULSE_API_KEY" in setup.output
    assert "app_secret:" not in setup.output
    assert doctor.exit_code == 0
    assert json.loads(doctor.output)["items"]


def test_data_cli_info_backup_clear(tmp_path, monkeypatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    info = runner.invoke(app, ["data", "info", "--json"])
    backup = runner.invoke(app, ["data", "backup", "--output-dir", str(tmp_path)])
    clear = runner.invoke(app, ["data", "clear", "--yes"])

    assert info.exit_code == 0
    assert "schema_version" in info.output
    assert backup.exit_code == 0
    assert clear.exit_code == 0


def test_release_check_json_reports_limitations() -> None:
    result = runner.invoke(app, ["release-check", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["version"] == "0.1.0"
    assert "checks" in payload
