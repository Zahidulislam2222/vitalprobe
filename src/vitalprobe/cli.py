"""VitalProbe command-line interface."""

from typing import Annotated

import typer

from vitalprobe import __version__

app = typer.Typer(
    name="vitalprobe",
    help="Safety and compliance evidence testing for healthcare & wellness AI assistants.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"vitalprobe {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """VitalProbe CLI."""


@app.command()
def run() -> None:
    """Run a test suite against a target endpoint. (Arrives in M1.)"""
    typer.echo("Not implemented yet. The runner arrives in milestone M1.")
    raise typer.Exit(code=2)


@app.command()
def validate() -> None:
    """Validate a test suite's YAML files. (Arrives in M1.)"""
    typer.echo("Not implemented yet. The validator arrives in milestone M1.")
    raise typer.Exit(code=2)
