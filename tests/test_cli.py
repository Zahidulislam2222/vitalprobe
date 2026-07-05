"""CLI smoke tests."""

from typer.testing import CliRunner

from vitalprobe import __version__
from vitalprobe.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_run_is_stub() -> None:
    result = runner.invoke(app, ["run"])
    assert result.exit_code == 2


def test_validate_is_stub() -> None:
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 2
