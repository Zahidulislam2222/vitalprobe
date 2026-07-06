"""VitalProbe AS an MCP server (BUILD-PLAN M8 step 4, PAID-ONLY).

Exposes the core engine to agents/IDEs: `run_suite`, `history`, `compare`, `learn`.
The entire server is gated by the MCP_SERVER feature flag — `build_server()` raises
without a valid license. This is distinct from `vitalprobe.targets.mcp`, which TESTS
someone else's bot behind an MCP server.

Every tool is a thin shell over the same engine the CLI uses (engine-first rule).
"""

import json
from dataclasses import asdict
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from vitalprobe.baseline import BaselineError, compare_runs, load_run
from vitalprobe.config import get_settings
from vitalprobe.entitlements.features import FeatureFlag, require
from vitalprobe.experience.generator import GenerationError, VariantGenerator, generate_drafts
from vitalprobe.experience.store import ExperienceStore
from vitalprobe.packs.loader import SuiteLoadError, load_suite
from vitalprobe.report.html_report import write_html_report
from vitalprobe.report.json_report import write_run_json
from vitalprobe.runner import run_suite as run_suite_async
from vitalprobe.targets.rest import AdapterConfig, AdapterError, RestAdapter, load_adapter_config


def _run_summary(verdict: str, counts: dict[str, int], extra: dict[str, object]) -> str:
    return json.dumps({"verdict": verdict, "counts": counts, **extra}, ensure_ascii=False)


def build_server() -> FastMCP:
    """Build the licensed MCP server. Raises FeatureUnavailableError without a license."""
    require(FeatureFlag.MCP_SERVER)

    server = FastMCP("vitalprobe")

    @server.tool()
    async def run_suite(suite_dir: str, output_dir: str) -> str:
        """Run a VitalProbe test suite against the configured target and write
        run.json + report.html to output_dir. Returns a JSON verdict summary."""
        settings = get_settings()
        try:
            loaded = load_suite(Path(suite_dir))
        except SuiteLoadError as exc:
            return json.dumps({"error": str(exc)})
        config_path = Path(suite_dir) / "adapter.default.yaml"
        try:
            config = load_adapter_config(config_path) if config_path.is_file() else AdapterConfig()
            adapter = RestAdapter(config)
        except AdapterError as exc:
            return json.dumps({"error": str(exc)})
        try:
            result = await run_suite_async(
                loaded, adapter, None, max_concurrency=settings.runner_concurrency
            )
        finally:
            await adapter.aclose()
        secrets = [settings.target_token, settings.openai_api_key, settings.anthropic_api_key]
        write_run_json(result, Path(output_dir), secrets)
        write_html_report(result, Path(output_dir), secrets)
        return _run_summary(
            result.verdict.value,
            result.counts.model_dump(by_alias=True),
            {"run_id": result.run_id, "output_dir": output_dir},
        )

    @server.tool()
    def history(target: str) -> str:
        """List tracked runs for a target endpoint (newest first) as JSON."""
        entries = ExperienceStore(get_settings().db_path).history(target)
        return json.dumps([asdict(entry) for entry in entries], ensure_ascii=False)

    @server.tool()
    def compare(baseline_path: str, current_path: str) -> str:
        """Compare two canonical run.json artifacts; returns regressions/improvements JSON."""
        try:
            comparison = compare_runs(load_run(Path(baseline_path)), load_run(Path(current_path)))
        except BaselineError as exc:
            return json.dumps({"error": str(exc)})
        return json.dumps(
            {
                "regressions": [asdict(c) for c in comparison.regressions],
                "improvements": [asdict(c) for c in comparison.improvements],
                "new_cases": [asdict(c) for c in comparison.new_cases],
                "removed_cases": [asdict(c) for c in comparison.removed_cases],
            },
            ensure_ascii=False,
        )

    @server.tool()
    async def learn(run_id: str, variants_per_failure: int, output_dir: str) -> str:
        """Draft adversarial variants from a tracked run's failures (paid: learning).
        Drafts stay status: draft — human review is mandatory before pack inclusion."""
        require(FeatureFlag.LEARNING)
        settings = get_settings()
        run = ExperienceStore(settings.db_path).run_by_id(run_id)
        if run is None:
            return json.dumps({"error": f"run '{run_id}' not found in the experience store"})
        try:
            loaded = load_suite(Path(run.suite.path))
            generator = VariantGenerator(settings)
        except (SuiteLoadError, GenerationError) as exc:
            return json.dumps({"error": str(exc)})
        try:
            written, errors = await generate_drafts(
                run, loaded, generator, variants_per_failure, Path(output_dir)
            )
        finally:
            await generator.aclose()
        return json.dumps(
            {
                "drafts_written": [str(path) for path in written],
                "errors": errors,
                "note": "Drafts are status: draft; human review required before any pack.",
            },
            ensure_ascii=False,
        )

    return server


def main() -> None:
    """Entry point: refuses to start without a license (upgrade message on stderr)."""
    import sys

    from vitalprobe.entitlements.features import FeatureUnavailableError

    try:
        server = build_server()
    except FeatureUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from None
    server.run()


if __name__ == "__main__":
    main()
