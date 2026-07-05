"""Self-contained HTML dossier rendering (BUILD-PLAN M2)."""

from collections import Counter
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from vitalprobe.report.json_report import REDACTED
from vitalprobe.schema import SEVERITY_ORDER, RunResult, Verdict

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_VERDICT_ORDER = {
    Verdict.ERROR: 0,
    Verdict.FAIL: 1,
    Verdict.WARN: 2,
    Verdict.PASS: 3,
}


def _template_context(run: RunResult) -> dict[str, Any]:
    results = sorted(
        run.results,
        key=lambda result: (
            SEVERITY_ORDER.get(result.severity, 99),
            _VERDICT_ORDER[result.verdict],
            result.id,
        ),
    )
    grouped = [
        {
            "severity": severity,
            "results": [result for result in results if result.severity == severity],
        }
        for severity in SEVERITY_ORDER
        if any(result.severity == severity for result in results)
    ]
    severity_counts = Counter(result.severity for result in results)
    worst = sorted(
        results,
        key=lambda result: (
            _VERDICT_ORDER[result.verdict],
            SEVERITY_ORDER.get(result.severity, 99),
            result.id,
        ),
    )[:3]
    return {
        "run": run,
        "grouped_results": grouped,
        "severity_counts": severity_counts,
        "worst_findings": worst,
        "generated_at": run.finished_at,
    }


def render_html(run: RunResult, secrets: list[str] | None = None) -> str:
    """Render a complete dossier and redact known secrets from the final document."""
    environment = Environment(
        loader=FileSystemLoader(_TEMPLATE_DIR),
        autoescape=select_autoescape(("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html = environment.get_template("dossier.html.j2").render(**_template_context(run))
    for secret in secrets or []:
        if secret:
            html = html.replace(secret, REDACTED)
    return html


def write_html_report(
    run: RunResult, output_dir: Path, secrets: list[str] | None = None
) -> Path:
    """Write `<output_dir>/report.html` and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "report.html"
    path.write_text(render_html(run, secrets), encoding="utf-8")
    return path
