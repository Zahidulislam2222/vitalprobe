"""FastAPI app for the local evidence dashboard.

BUILD-PLAN §9 constraints are binding here: localhost-only by default, no
accounts, no login, no telemetry, and every asset served from this package so
the dashboard works fully offline. Read-only in P9a — it renders the local
experience store and never mutates it.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from vitalprobe.baseline import RunComparison, compare_runs
from vitalprobe.experience.store import ExperienceStore

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(store: ExperienceStore | None = None) -> FastAPI:
    """Build the dashboard app around an experience store (injectable for tests)."""
    dashboard_store = store if store is not None else ExperienceStore()
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    app = FastAPI(
        title="VitalProbe dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

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

    return app
