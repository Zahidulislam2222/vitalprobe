"""VitalProbe command-line interface."""

import asyncio
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from vitalprobe import __version__
from vitalprobe.config import get_settings
from vitalprobe.experience.store import ExperienceStore, Regression
from vitalprobe.packs.loader import SuiteLoadError, load_suite
from vitalprobe.report.html_report import write_html_report
from vitalprobe.report.json_report import write_run_json
from vitalprobe.runner import run_suite as run_suite_async
from vitalprobe.schema import (
    EXIT_CONFIG_ERROR,
    EXIT_FAILED,
    EXIT_OK,
    RunResult,
    RunVerdict,
    Verdict,
)
from vitalprobe.targets.rest import AdapterConfig, AdapterError, RestAdapter, load_adapter_config

app = typer.Typer(
    name="vitalprobe",
    help="Safety and compliance evidence testing for healthcare & wellness AI assistants.",
    no_args_is_help=True,
)
console = Console()

VERDICT_STYLES = {
    Verdict.PASS: "green",
    Verdict.WARN: "yellow3",
    Verdict.FAIL: "red",
    Verdict.ERROR: "red bold",
}


class ReportFormat(StrEnum):
    HTML = "html"
    JSON = "json"


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


def _print_summary(run: RunResult) -> None:
    table = Table(title=f"VitalProbe run — {run.suite.name}")
    table.add_column("case id")
    table.add_column("verdict")
    table.add_column("latency", justify="right")
    for result in run.results:
        style = VERDICT_STYLES[result.verdict]
        latency = f"{result.latency_ms} ms" if result.latency_ms is not None else "-"
        table.add_row(result.id, f"[{style}]{result.verdict}[/{style}]", latency)
    console.print(table)
    console.print(
        f"verdict: [bold]{run.verdict}[/bold] · "
        f"pass {run.counts.pass_} · warn {run.counts.warn} · "
        f"fail {run.counts.fail} · error {run.counts.error}"
    )


def _print_regressions(regressions: list[Regression]) -> None:
    if not regressions:
        console.print("[green]No regressions against the previous tracked run.[/green]")
        return
    console.print(f"[red bold]{len(regressions)} regression(s) detected:[/red bold]")
    for regression in regressions:
        console.print(
            f"  {regression.case_id}: {regression.previous} → {regression.current}"
        )


@app.command()
def run(
    suite: Annotated[Path, typer.Option(help="Suite directory of test-case YAML files.")],
    output: Annotated[Path, typer.Option(help="Output directory for run.json / report.html.")],
    adapter_config: Annotated[
        Path | None,
        typer.Option(help="Adapter config YAML (default: adapter.default.yaml in the suite dir)."),
    ] = None,
    strict_warn: Annotated[
        bool, typer.Option("--strict-warn", help="Exit 1 when any WARN is present.")
    ] = False,
    format_: Annotated[
        ReportFormat,
        typer.Option(
            "--format",
            help="Output format: html writes run.json and report.html; json writes run.json only.",
        ),
    ] = ReportFormat.HTML,
    track: Annotated[
        bool,
        typer.Option("--track", help="Remember this run and compare it with the prior target run."),
    ] = False,
) -> None:
    """Run a test suite and write its JSON result and, by default, HTML dossier."""
    try:
        loaded = load_suite(suite)
    except SuiteLoadError as exc:
        for line in exc.errors:
            console.print(f"[red]{line}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    config_path = adapter_config or (suite / "adapter.default.yaml")
    try:
        config = load_adapter_config(config_path) if config_path.is_file() else AdapterConfig()
        adapter = RestAdapter(config)
    except AdapterError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    async def _run() -> RunResult:
        try:
            return await run_suite_async(loaded, adapter)
        finally:
            await adapter.aclose()

    result = asyncio.run(_run())

    settings = get_settings()
    secrets = [settings.target_token]
    path = write_run_json(result, output, secrets)
    html_path = None
    if format_ is ReportFormat.HTML:
        html_path = write_html_report(result, output, secrets)
    _print_summary(result)
    console.print(f"run.json written to {path}")
    if html_path is not None:
        console.print(f"report.html written to {html_path}")
    if track:
        regressions = ExperienceStore(settings.db_path).record_run(result, secrets)
        console.print(f"run tracked for {result.target.endpoint_redacted}")
        _print_regressions(regressions)

    if result.verdict is RunVerdict.FAILED:
        raise typer.Exit(code=EXIT_FAILED)
    if result.verdict is RunVerdict.PASSED_WITH_WARNINGS and strict_warn:
        raise typer.Exit(code=EXIT_FAILED)
    raise typer.Exit(code=EXIT_OK)


@app.command()
def history(
    target: Annotated[
        str,
        typer.Option(help="Target name (the redacted endpoint shown by a tracked run)."),
    ],
) -> None:
    """Show tracked run history and regression counts for a target."""
    entries = ExperienceStore(get_settings().db_path).history(target)
    if not entries:
        console.print(f"[yellow]No tracked runs found for {target}[/yellow]")
        raise typer.Exit(code=EXIT_OK)

    table = Table(title=f"VitalProbe history — {target}")
    table.add_column("date")
    table.add_column("verdict")
    table.add_column("pass", justify="right")
    table.add_column("warn", justify="right")
    table.add_column("fail", justify="right")
    table.add_column("error", justify="right")
    table.add_column("regressions", justify="right")
    for entry in entries:
        table.add_row(
            entry.started_at[:10],
            entry.verdict,
            str(entry.pass_count),
            str(entry.warn_count),
            str(entry.fail_count),
            str(entry.error_count),
            str(entry.regression_count),
        )
    console.print(table)
    raise typer.Exit(code=EXIT_OK)


@app.command()
def validate(
    suite: Annotated[Path, typer.Option(help="Suite directory of test-case YAML files.")],
) -> None:
    """Validate a test suite's YAML files without running anything."""
    try:
        loaded = load_suite(suite)
    except SuiteLoadError as exc:
        for line in exc.errors:
            console.print(f"[red]{line}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None
    console.print(
        f"[green]OK[/green] — {len(loaded.cases)} valid cases in suite '{loaded.name}'"
        + (f" v{loaded.pack_version}" if loaded.pack_version else "")
    )
    raise typer.Exit(code=EXIT_OK)
