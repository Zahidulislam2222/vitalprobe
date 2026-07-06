"""VitalProbe command-line interface."""

import asyncio
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from vitalprobe import __version__
from vitalprobe.baseline import BaselineError, RunComparison, compare_runs, load_run
from vitalprobe.calibration import (
    CalibrationError,
    ItemScore,
    agreement_for_judge,
    load_items,
    read_labels,
    score_items,
    write_labels_template,
    write_reports,
)
from vitalprobe.config import Settings, get_settings
from vitalprobe.entitlements.features import (
    FeatureFlag,
    FeatureUnavailableError,
    require,
)
from vitalprobe.entitlements.license import EntitlementStatus, verify_license
from vitalprobe.experience.generator import (
    GenerationError,
    VariantGenerator,
    generate_drafts,
)
from vitalprobe.experience.store import (
    CalibrationLabelRecord,
    ExperienceStore,
    Regression,
)
from vitalprobe.judges.anthropic import AnthropicJudge
from vitalprobe.judges.base import JudgeBackend
from vitalprobe.judges.ollama import OllamaJudge
from vitalprobe.judges.openai import OpenAIJudge
from vitalprobe.law import LawLoadError, load_law_dir, validate_suite_refs
from vitalprobe.mcp.server import build_server as build_mcp_server
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
from vitalprobe.simulator.loop import simulate as simulate_personas
from vitalprobe.simulator.patient import PatientError, PatientLLM
from vitalprobe.simulator.persona import PersonaError, load_personas
from vitalprobe.targets.base import TargetAdapter
from vitalprobe.targets.mcp import McpAdapter, load_mcp_adapter_config
from vitalprobe.targets.rest import AdapterConfig, AdapterError, RestAdapter, load_adapter_config

app = typer.Typer(
    name="vitalprobe",
    help="Safety and compliance evidence testing for healthcare & wellness AI assistants.",
    no_args_is_help=True,
)
license_app = typer.Typer(help="Inspect and verify offline VitalProbe licenses.")
app.add_typer(license_app, name="license")
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


def _print_comparison(comparison: RunComparison) -> None:
    table = Table(title="VitalProbe baseline comparison")
    table.add_column("change")
    table.add_column("case id")
    table.add_column("previous")
    table.add_column("current")
    for regression in comparison.regressions:
        table.add_row(
            "REGRESSION",
            regression.case_id,
            regression.previous,
            regression.current,
            style="red",
        )
    for improvement in comparison.improvements:
        table.add_row(
            "IMPROVEMENT",
            improvement.case_id,
            improvement.previous,
            improvement.current,
            style="green",
        )
    for new_case in comparison.new_cases:
        table.add_row("NEW", new_case.case_id, "-", new_case.verdict)
    for removed_case in comparison.removed_cases:
        table.add_row("REMOVED", removed_case.case_id, removed_case.verdict, "-")
    console.print(table)
    console.print(
        f"regressions {len(comparison.regressions)} · "
        f"improvements {len(comparison.improvements)} · "
        f"new {len(comparison.new_cases)} · removed {len(comparison.removed_cases)}"
    )


def _print_license(status: EntitlementStatus) -> None:
    console.print(f"tier: [bold]{status.tier}[/bold]")
    console.print(f"status: {status.message}")
    if status.licensee:
        console.print(f"licensee: {status.licensee}")
    if status.expires_at:
        console.print(f"expires: {status.expires_at.isoformat()}")
    features = ", ".join(sorted(feature.value for feature in status.features))
    console.print(f"paid features: {features or 'none'}")
    if not status.valid:
        console.print("Free engine and reporting features remain available.")


def _build_judge() -> JudgeBackend | None:
    config = get_settings()
    if config.judge == "none":
        return None
    model = config.local_model if config.judge == "ollama" else config.judge_model
    if not model:
        raise AdapterError("judge model is required in configuration")
    if config.judge == "openai":
        return OpenAIJudge(
            model,
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            responses_path=config.openai_responses_path,
            timeout_s=config.judge_timeout_s,
            input_price=config.judge_input_price_per_million,
            output_price=config.judge_output_price_per_million,
        )
    if config.judge == "anthropic":
        return AnthropicJudge(
            model,
            api_key=config.anthropic_api_key,
            base_url=config.anthropic_base_url,
            messages_path=config.anthropic_messages_path,
            api_version=config.anthropic_api_version,
            timeout_s=config.judge_timeout_s,
            max_tokens=config.anthropic_max_tokens,
            input_price=config.judge_input_price_per_million,
            output_price=config.judge_output_price_per_million,
        )
    if config.judge == "ollama":
        return _ollama_judge(model, config)
    raise AdapterError(f"unknown judge provider: {config.judge}")


def _ollama_judge(model: str, config: Settings) -> OllamaJudge:
    return OllamaJudge(
        model,
        host=config.ollama_host,
        chat_path=config.ollama_chat_path,
        timeout_s=config.judge_timeout_s,
        max_attempts=config.local_judge_max_attempts,
        think=config.judge_ollama_think,
    )


def _build_calibration_judges(specs: list[str], config: Settings) -> dict[str, JudgeBackend]:
    """Parse `--judges` specs: `ollama:<model tag>`, `anthropic`, or `openai` (configured model)."""
    judges: dict[str, JudgeBackend] = {}
    for spec in specs:
        if spec.startswith("ollama:"):
            model = spec.removeprefix("ollama:")
            if not model:
                raise AdapterError(f"judge spec '{spec}' is missing a local model tag")
            judges[spec] = _ollama_judge(model, config)
        elif spec in {"anthropic", "openai"}:
            if not config.judge_model:
                raise AdapterError(
                    f"cloud judge '{spec}' needs VITALPROBE_JUDGE_MODEL in configuration"
                )
            if spec == "anthropic":
                judges[f"{spec}:{config.judge_model}"] = AnthropicJudge(
                    config.judge_model,
                    api_key=config.anthropic_api_key,
                    base_url=config.anthropic_base_url,
                    messages_path=config.anthropic_messages_path,
                    api_version=config.anthropic_api_version,
                    timeout_s=config.judge_timeout_s,
                    max_tokens=config.anthropic_max_tokens,
                    input_price=config.judge_input_price_per_million,
                    output_price=config.judge_output_price_per_million,
                )
            else:
                judges[f"{spec}:{config.judge_model}"] = OpenAIJudge(
                    config.judge_model,
                    api_key=config.openai_api_key,
                    base_url=config.openai_base_url,
                    responses_path=config.openai_responses_path,
                    timeout_s=config.judge_timeout_s,
                    input_price=config.judge_input_price_per_million,
                    output_price=config.judge_output_price_per_million,
                )
        else:
            raise AdapterError(
                f"unknown judge spec '{spec}' (use ollama:<model>, anthropic, or openai)"
            )
    return judges


@license_app.command("show")
def license_show() -> None:
    """Show the configured tier, paid features, and expiry."""
    _print_license(verify_license())
    raise typer.Exit(code=EXIT_OK)


@license_app.command("verify")
def license_verify(
    path: Annotated[Path, typer.Argument(help="Path to a signed license JSON file.")],
) -> None:
    """Verify a license file offline against VitalProbe's embedded public key."""
    status = verify_license(path)
    _print_license(status)
    raise typer.Exit(code=EXIT_OK if status.valid else EXIT_CONFIG_ERROR)


@license_app.command("check")
def license_check(
    feature: Annotated[FeatureFlag, typer.Argument(help="Paid feature to check.")],
) -> None:
    """Check whether the configured license unlocks one paid feature."""
    try:
        require(feature)
    except FeatureUnavailableError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None
    console.print(f"[green]Feature unlocked: {feature.value}[/green]")
    raise typer.Exit(code=EXIT_OK)


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
    yes_spend: Annotated[
        bool,
        typer.Option("--yes-spend", help="Confirm estimated cloud judge spending."),
    ] = False,
    save_baseline: Annotated[
        Path | None,
        typer.Option(
            "--save-baseline",
            help="Also write canonical run.json to this baseline directory.",
        ),
    ] = None,
    law_dir: Annotated[
        Path | None,
        typer.Option(
            "--law-dir",
            help="Law schema directory: map case law_refs to requirement citations "
            "in the report (paid feature: law_mapping).",
        ),
    ] = None,
) -> None:
    """Run a test suite and write its JSON result and, by default, HTML dossier."""
    try:
        loaded = load_suite(suite)
    except SuiteLoadError as exc:
        for line in exc.errors:
            console.print(f"[red]{line}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    law_index = None
    if law_dir is not None:
        try:
            require(FeatureFlag.LAW_MAPPING)
        except FeatureUnavailableError as exc:
            console.print(f"[yellow]{exc}[/yellow]")
            raise typer.Exit(code=EXIT_CONFIG_ERROR) from None
        try:
            law_index = load_law_dir(law_dir)
            validate_suite_refs([case.law_refs for case in loaded.cases], law_index)
        except LawLoadError as exc:
            for line in exc.errors:
                console.print(f"[red]{line}[/red]")
            raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    settings = get_settings()
    judged_cases = sum(case.expect.judge is not None for case in loaded.cases)
    if settings.judge in {"openai", "anthropic"} and judged_cases:
        estimate = judged_cases * settings.judge_estimated_tokens_per_case * (
            settings.judge_input_price_per_million
            + settings.judge_output_price_per_million
        ) / 1_000_000
        console.print(
            f"{judged_cases} judged cases × ~{settings.judge_estimated_tokens_per_case} "
            "tokens × configured prices "
            f"= estimated ${estimate:.4f}"
        )
        if not yes_spend:
            console.print("[yellow]Cloud judging requires --yes-spend.[/yellow]")
            raise typer.Exit(code=EXIT_CONFIG_ERROR)

    config_path = adapter_config or (suite / "adapter.default.yaml")
    try:
        adapter = _build_adapter(config_path)
        judge = _build_judge()
    except AdapterError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    async def _run() -> RunResult:
        try:
            return await run_suite_async(
                loaded,
                adapter,
                judge,
                max_concurrency=settings.runner_concurrency,
            )
        finally:
            await adapter.aclose()
            if judge is not None and hasattr(judge, "aclose"):
                await judge.aclose()

    result = asyncio.run(_run())

    secrets = [
        settings.target_token,
        settings.openai_api_key,
        settings.anthropic_api_key,
    ]
    path = write_run_json(result, output, secrets)
    html_path = None
    if format_ is ReportFormat.HTML:
        html_path = write_html_report(result, output, secrets, law_index)
    _print_summary(result)
    console.print(f"run.json written to {path}")
    if html_path is not None:
        console.print(f"report.html written to {html_path}")
    if save_baseline is not None:
        baseline_path = write_run_json(result, save_baseline, secrets)
        console.print(f"baseline written to {baseline_path}")
    if track:
        regressions = ExperienceStore(settings.db_path).record_run(result, secrets)
        console.print(f"run tracked for {result.target.endpoint_redacted}")
        _print_regressions(regressions)

    if result.verdict is RunVerdict.FAILED:
        raise typer.Exit(code=EXIT_FAILED)
    if result.verdict is RunVerdict.PASSED_WITH_WARNINGS and strict_warn:
        raise typer.Exit(code=EXIT_FAILED)
    raise typer.Exit(code=EXIT_OK)


def _build_adapter(config_path: Path) -> TargetAdapter:
    """REST by default; `kind: mcp` in the adapter YAML selects the MCP target adapter."""
    if config_path.is_file():
        mcp_config = load_mcp_adapter_config(config_path)
        if mcp_config is not None:
            return McpAdapter(mcp_config)
        return RestAdapter(load_adapter_config(config_path))
    return RestAdapter(AdapterConfig())


@app.command()
def simulate(
    persona: Annotated[
        Path, typer.Option(help="Persona YAML file or a directory of persona files.")
    ],
    output: Annotated[Path, typer.Option(help="Output directory for run.json / report.html.")],
    adapter_config: Annotated[
        Path | None,
        typer.Option(help="Adapter config YAML (default: REST adapter from the environment)."),
    ] = None,
    format_: Annotated[
        ReportFormat,
        typer.Option("--format", help="html writes run.json and report.html; json only run.json."),
    ] = ReportFormat.HTML,
) -> None:
    """Multi-turn synthetic-patient simulation: personas converse with the target bot,
    trajectory checks judge the full transcript."""
    try:
        personas = load_personas(persona)
    except PersonaError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    settings = get_settings()
    try:
        adapter = _build_adapter(adapter_config or Path("adapter.default.yaml"))
        patient = PatientLLM(settings)
    except (AdapterError, PatientError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    async def _simulate() -> RunResult:
        try:
            return await simulate_personas(
                personas,
                adapter,
                patient,
                suite_name=f"simulator:{persona.name}",
                suite_path=str(persona),
            )
        finally:
            await adapter.aclose()
            await patient.aclose()

    result = asyncio.run(_simulate())
    secrets = [settings.target_token, settings.openai_api_key, settings.anthropic_api_key]
    path = write_run_json(result, output, secrets)
    html_path = None
    if format_ is ReportFormat.HTML:
        html_path = write_html_report(result, output, secrets)
    _print_summary(result)
    console.print(f"run.json written to {path}")
    if html_path is not None:
        console.print(f"report.html written to {html_path}")
    raise typer.Exit(
        code=EXIT_FAILED if result.verdict is RunVerdict.FAILED else EXIT_OK
    )


@app.command("mcp-serve")
def mcp_serve() -> None:
    """Start VitalProbe as an MCP server (paid: mcp_server) over stdio."""
    try:
        server = build_mcp_server()
    except FeatureUnavailableError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None
    server.run()


@app.command()
def compare(
    baseline: Annotated[Path, typer.Option(help="Baseline run.json path.")],
    current: Annotated[Path, typer.Option(help="Current run.json path.")],
) -> None:
    """Compare two canonical run artifacts and fail on a regression."""
    try:
        comparison = compare_runs(load_run(baseline), load_run(current))
    except BaselineError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None
    _print_comparison(comparison)
    raise typer.Exit(code=EXIT_FAILED if comparison.regressions else EXIT_OK)


@app.command()
def calibrate(
    suite: Annotated[Path, typer.Option(help="Suite directory of test-case YAML files.")],
    responses: Annotated[
        list[Path],
        typer.Option(
            "--responses",
            help="run.json artifact (file or run directory); repeat for multiple runs.",
        ),
    ],
    judges: Annotated[
        list[str],
        typer.Option(
            "--judges",
            help="Judge spec, repeatable: ollama:<model tag>, anthropic, or openai.",
        ),
    ],
    output: Annotated[Path, typer.Option(help="Output directory for calibration artifacts.")],
    labels: Annotated[
        Path | None,
        typer.Option(help="Filled labels CSV (human_verdict per item) to compute agreement."),
    ] = None,
    rubric: Annotated[
        str,
        typer.Option(help="Rubric id used for cases without their own judge rubric."),
    ] = "",
    yes_spend: Annotated[
        bool,
        typer.Option("--yes-spend", help="Confirm estimated cloud judge spending."),
    ] = False,
    track: Annotated[
        bool,
        typer.Option(
            "--track",
            help="Persist human labels and judge verdicts to the experience store (L3).",
        ),
    ] = False,
) -> None:
    """Score the same case/response items with every judge and, once founder labels exist,
    compute per-judge agreement, Cohen's kappa, and confusion matrices."""
    settings = get_settings()
    try:
        loaded = load_suite(suite)
    except SuiteLoadError as exc:
        for line in exc.errors:
            console.print(f"[red]{line}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None
    try:
        items = load_items(loaded, responses)
        judge_backends = _build_calibration_judges(judges, settings)
    except (AdapterError, CalibrationError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    cloud_judges = [name for name in judge_backends if not name.startswith("ollama:")]
    if cloud_judges:
        estimate = len(cloud_judges) * len(items) * settings.judge_estimated_tokens_per_case * (
            settings.judge_input_price_per_million + settings.judge_output_price_per_million
        ) / 1_000_000
        console.print(
            f"{len(cloud_judges)} cloud judge(s) × {len(items)} items × "
            f"~{settings.judge_estimated_tokens_per_case} tokens × configured prices "
            f"= estimated ${estimate:.4f}"
        )
        if not yes_spend:
            console.print("[yellow]Cloud judging requires --yes-spend.[/yellow]")
            raise typer.Exit(code=EXIT_CONFIG_ERROR)

    async def _score() -> dict[str, list[ItemScore]]:
        try:
            return await score_items(judge_backends, items, rubric)
        finally:
            for backend in judge_backends.values():
                if hasattr(backend, "aclose"):
                    await backend.aclose()

    try:
        scores = asyncio.run(_score())
    except CalibrationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    output.mkdir(parents=True, exist_ok=True)
    template_path = output / "labels_template.csv"
    write_labels_template(items, template_path)

    human_labels = {}
    if labels is not None:
        try:
            human_labels = read_labels(labels)
        except (OSError, CalibrationError) as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=EXIT_CONFIG_ERROR) from None
    agreements = (
        [
            agreement_for_judge(name, judge_scores, human_labels, items)
            for name, judge_scores in scores.items()
        ]
        if human_labels
        else []
    )
    write_reports(output, items, scores, agreements, len(human_labels))

    if track and human_labels:
        case_by_item = {item.item_id: item.case.id for item in items}
        recorded_at = datetime.now(UTC).isoformat()
        label_rows = [
            CalibrationLabelRecord(
                item_id=score.item_id,
                case_id=case_by_item.get(score.item_id, ""),
                judge=judge_name,
                human_verdict=human_labels[score.item_id].value,
                judge_verdict=score.verdict.value if score.verdict else None,
                agree=(score.verdict is human_labels[score.item_id])
                if score.verdict
                else None,
                recorded_at=recorded_at,
            )
            for judge_name, judge_scores in scores.items()
            for score in judge_scores
            if score.item_id in human_labels
        ]
        count = ExperienceStore(settings.db_path).record_calibration_labels(label_rows)
        console.print(f"{count} calibration label rows recorded to the experience store")

    console.print(f"{len(items)} items scored by {len(judge_backends)} judge(s)")
    errored = {
        name: sum(score.error is not None for score in judge_scores)
        for name, judge_scores in scores.items()
    }
    for name, error_count in errored.items():
        status = f"[red]{error_count} judge errors[/red]" if error_count else "[green]ok[/green]"
        console.print(f"  {name}: {status}")
    console.print(f"labels template written to {template_path}")
    if agreements:
        table = Table(title="Agreement vs human labels")
        table.add_column("judge")
        table.add_column("items", justify="right")
        table.add_column("agreement", justify="right")
        table.add_column("kappa", justify="right")
        for agreement in agreements:
            table.add_row(
                agreement.judge,
                str(agreement.labeled_items),
                f"{agreement.percent_agreement}%",
                "n/a" if agreement.cohen_kappa is None else str(agreement.cohen_kappa),
            )
        console.print(table)
    else:
        console.print(
            "[yellow]No human labels yet — fill the template and re-run with --labels "
            "to compute agreement.[/yellow]"
        )
    console.print(f"calibration report written to {output / 'calibration_report.md'}")
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
    release: Annotated[
        bool,
        typer.Option(
            "--release",
            help="Release lint: additionally fail when any case is still status: draft.",
        ),
    ] = False,
) -> None:
    """Validate a test suite's YAML files without running anything."""
    try:
        loaded = load_suite(suite)
    except SuiteLoadError as exc:
        for line in exc.errors:
            console.print(f"[red]{line}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None
    if release:
        drafts = [case.id for case in loaded.cases if case.status == "draft"]
        if drafts:
            console.print(
                f"[red]release lint failed: {len(drafts)} draft case(s) present — "
                "human review must flip them to status: reviewed[/red]"
            )
            for case_id in drafts:
                console.print(f"  [red]{case_id}[/red]")
            raise typer.Exit(code=EXIT_CONFIG_ERROR)
    console.print(
        f"[green]OK[/green] — {len(loaded.cases)} valid cases in suite '{loaded.name}'"
        + (f" v{loaded.pack_version}" if loaded.pack_version else "")
    )
    raise typer.Exit(code=EXIT_OK)


@app.command()
def learn(
    from_run: Annotated[
        str, typer.Option("--from-run", help="Tracked run id to learn from.")
    ],
    variants: Annotated[
        int, typer.Option(min=1, help="Adversarial variants to draft per failed case.")
    ],
    output: Annotated[
        Path, typer.Option(help="Drafts directory (NEVER a pack directory).")
    ],
) -> None:
    """Draft adversarial test-case variants from a tracked run's failures (paid: learning).

    Drafts stay `status: draft`; only human review may move them into a pack.
    """
    try:
        require(FeatureFlag.LEARNING)
    except FeatureUnavailableError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    settings = get_settings()
    run = ExperienceStore(settings.db_path).run_by_id(from_run)
    if run is None:
        console.print(
            f"[red]run '{from_run}' not found in the experience store "
            "(record it with `vitalprobe run --track`)[/red]"
        )
        raise typer.Exit(code=EXIT_CONFIG_ERROR)
    try:
        loaded = load_suite(Path(run.suite.path))
    except SuiteLoadError as exc:
        for line in exc.errors:
            console.print(f"[red]{line}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    try:
        generator = VariantGenerator(settings)
    except GenerationError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=EXIT_CONFIG_ERROR) from None

    async def _generate() -> tuple[list[Path], list[str]]:
        try:
            return await generate_drafts(run, loaded, generator, variants, output)
        finally:
            await generator.aclose()

    written, errors = asyncio.run(_generate())
    for line in errors:
        console.print(f"[red]{line}[/red]")
    if not written and not errors:
        console.print("[green]No failed cases in this run — nothing to learn from.[/green]")
        raise typer.Exit(code=EXIT_OK)
    for path in written:
        console.print(f"drafts written to {path}")
    console.print(
        f"{len(written)} draft file(s) from {len(written) + len(errors)} failed case(s). "
        "Human review required before any pack inclusion."
    )
    raise typer.Exit(code=EXIT_OK if written else EXIT_FAILED)
