"""FastAPI app for the local evidence dashboard.

BUILD-PLAN §9 constraints are binding here: localhost-only by default, no
accounts, no login, no telemetry, and every asset served from this package so
the dashboard works fully offline. P9b adds the paid surfaces (learning drafts,
law mapping) behind the SAME entitlement checks as the CLI, plus a trigger-run
form that shells out to the existing CLI run path.
"""

import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from vitalprobe.baseline import RunComparison, compare_runs
from vitalprobe.config import Settings, get_settings
from vitalprobe.dashboard.services import (
    RunExecutor,
    TriggerOutcome,
    build_run_argv,
    list_draft_files,
    load_law_view,
    run_cli_subprocess,
)
from vitalprobe.entitlements.features import (
    FeatureFlag,
    FeatureUnavailableError,
    require,
)
from vitalprobe.entitlements.license import verify_license
from vitalprobe.experience.store import ExperienceStore
from vitalprobe.law import LAW_DISCLAIMER

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_LOCAL_ORIGIN_HOSTS = {"127.0.0.1", "localhost", "::1"}


def create_app(
    store: ExperienceStore | None = None,
    settings: Settings | None = None,
    run_executor: RunExecutor | None = None,
) -> FastAPI:
    """Build the dashboard app around an experience store (injectable for tests)."""
    dashboard_store = store if store is not None else ExperienceStore()
    app_settings = settings if settings is not None else get_settings()
    executor = run_executor if run_executor is not None else run_cli_subprocess
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    app = FastAPI(
        title="VitalProbe dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    def _locked(
        request: Request, nav: str, title: str, reason: str
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "locked.html",
            {"page_nav": nav, "page_title": title, "reason": reason},
        )

    def _origin_is_local(request: Request) -> bool:
        """A web page must never drive this console via a cross-site form. Port must
        match too: another server on loopback is still a foreign origin."""
        origin = request.headers.get("origin")
        if origin is None:
            return True
        parsed = urlsplit(origin)
        if (
            parsed.hostname not in _LOCAL_ORIGIN_HOSTS
            and parsed.hostname != app_settings.dashboard_host
        ):
            return False
        return parsed.port == request.url.port

    @app.get("/", response_class=HTMLResponse)
    def runs_index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "runs.html",
            {
                "summaries": dashboard_store.run_summaries(),
                "targets": dashboard_store.targets(),
            },
        )

    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_detail(request: Request, run_id: str) -> HTMLResponse:
        run = dashboard_store.run_by_id(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="unknown run id")
        return templates.TemplateResponse(request, "run_detail.html", {"run": run})

    @app.get("/history", response_class=HTMLResponse)
    def target_history(request: Request, target: str) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "history.html",
            {"target": target, "entries": dashboard_store.history(target)},
        )

    @app.get("/compare", response_class=HTMLResponse)
    def compare_view(
        request: Request, baseline: str = "", current: str = ""
    ) -> HTMLResponse:
        comparison: RunComparison | None = None
        error = ""
        if baseline and current:
            baseline_run = dashboard_store.run_by_id(baseline)
            current_run = dashboard_store.run_by_id(current)
            if baseline_run is None or current_run is None:
                error = "unknown run id"
            else:
                comparison = compare_runs(baseline_run, current_run)
        return templates.TemplateResponse(
            request,
            "compare.html",
            {
                "summaries": dashboard_store.run_summaries(),
                "baseline": baseline,
                "current": current,
                "comparison": comparison,
                "error": error,
            },
        )

    @app.get("/license", response_class=HTMLResponse)
    def license_status(request: Request) -> HTMLResponse:
        # Same offline verification the CLI uses; every failure degrades to free.
        status = verify_license()
        return templates.TemplateResponse(
            request,
            "license.html",
            {"status": status, "all_flags": list(FeatureFlag)},
        )

    @app.get("/calibration", response_class=HTMLResponse)
    def calibration_status(request: Request) -> HTMLResponse:
        total, cases = dashboard_store.calibration_label_summary()
        return templates.TemplateResponse(
            request,
            "calibration.html",
            {"total_labels": total, "labeled_cases": cases},
        )

    @app.get("/learning", response_class=HTMLResponse)
    def learning_drafts(request: Request) -> HTMLResponse:
        # Same gate as `vitalprobe learn` — free tier gets a locked page, never a crash.
        try:
            require(FeatureFlag.LEARNING)
        except FeatureUnavailableError as exc:
            return _locked(request, "learning", "Learning drafts", str(exc))
        return templates.TemplateResponse(
            request,
            "learning.html",
            {
                "drafts_dir": str(app_settings.drafts_dir),
                "files": list_draft_files(app_settings.drafts_dir),
            },
        )

    @app.get("/law", response_class=HTMLResponse)
    def law_surfaces(request: Request) -> HTMLResponse:
        # Same gate as `vitalprobe run --law-dir` (paid: law_mapping).
        try:
            require(FeatureFlag.LAW_MAPPING)
        except FeatureUnavailableError as exc:
            return _locked(request, "law", "Law mapping", str(exc))
        return templates.TemplateResponse(
            request,
            "law.html",
            {
                "view": load_law_view(app_settings.law_dir),
                "disclaimer": LAW_DISCLAIMER,
            },
        )

    def _trigger_context(
        suite: str = "", target_url: str = ""
    ) -> dict[str, object]:
        return {
            "suite": suite,
            "target_url": target_url,
            "error": "",
            "outcome": None,
            "output_tail": "",
            "output_dir": "",
        }

    @app.get("/trigger-run", response_class=HTMLResponse)
    def trigger_form(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(request, "trigger.html", _trigger_context())

    @app.post("/trigger-run", response_class=HTMLResponse)
    async def trigger_run(request: Request) -> HTMLResponse:
        if not _origin_is_local(request):
            raise HTTPException(
                status_code=403, detail="cross-site form submissions are rejected"
            )
        form = await request.form()
        suite_value = str(form.get("suite", "")).strip()
        target_url = str(form.get("target_url", "")).strip()
        context = _trigger_context(suite_value, target_url)
        suite_path = Path(suite_value)
        if not suite_value or not suite_path.is_dir():
            context["error"] = (
                "suite path must be an existing directory of test-case YAML files"
            )
            return templates.TemplateResponse(request, "trigger.html", context)

        stamp = f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid4().hex[:6]}"
        output_dir = app_settings.dashboard_runs_dir / f"run-{stamp}"
        env = dict(os.environ)
        if target_url:
            env["VITALPROBE_TARGET_URL"] = target_url
        outcome: TriggerOutcome = await run_in_threadpool(
            executor,
            build_run_argv(suite_path, output_dir),
            env,
            app_settings.dashboard_run_timeout_s,
        )
        context["outcome"] = outcome
        context["output_tail"] = outcome.output[-app_settings.dashboard_output_tail_chars :]
        context["output_dir"] = str(output_dir)
        return templates.TemplateResponse(request, "trigger.html", context)

    return app
