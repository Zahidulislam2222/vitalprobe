"""View helpers behind the P9b dashboard pages: draft listing, law loading, run trigger.

The trigger path deliberately shells out to the EXISTING CLI (`python -m vitalprobe run`)
instead of re-implementing the run pipeline — the dashboard stays a thin local console.
"""

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from vitalprobe.law import LawFile, LawLoadError, load_law_dir
from vitalprobe.schema import TestCase


@dataclass(frozen=True, slots=True)
class DraftCaseView:
    case_id: str
    title: str
    status: str
    notes: str


@dataclass(frozen=True, slots=True)
class DraftFileView:
    name: str
    cases: list[DraftCaseView] = field(default_factory=list)
    error: str | None = None


def list_draft_files(drafts_dir: Path) -> list[DraftFileView]:
    """Parse every draft YAML in the drafts dir; a broken file becomes an error row,
    never a 500 — hand-edited drafts are expected during human review."""
    if not drafts_dir.is_dir():
        return []
    views: list[DraftFileView] = []
    for path in sorted(drafts_dir.glob("*.yaml")):
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise ValueError("expected a YAML list of draft cases")
            cases = [TestCase.model_validate(item) for item in raw]
        except (OSError, UnicodeError, ValueError, yaml.YAMLError, ValidationError) as exc:
            views.append(DraftFileView(name=path.name, error=str(exc)))
            continue
        views.append(
            DraftFileView(
                name=path.name,
                cases=[
                    DraftCaseView(case.id, case.title, case.status, case.notes)
                    for case in cases
                ],
            )
        )
    return views


@dataclass(frozen=True, slots=True)
class LawView:
    configured: bool
    laws: list[LawFile] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def load_law_view(law_dir: Path | None) -> LawView:
    """Load the configured law dir for display; loader errors render, never raise."""
    if law_dir is None:
        return LawView(configured=False)
    try:
        index = load_law_dir(law_dir)
    except LawLoadError as exc:
        return LawView(configured=True, errors=list(exc.errors))
    return LawView(configured=True, laws=[index[law_id] for law_id in sorted(index)])


@dataclass(frozen=True, slots=True)
class TriggerOutcome:
    exit_code: int | None
    output: str
    timed_out: bool = False


RunExecutor = Callable[[list[str], dict[str, str], float], TriggerOutcome]


def build_run_argv(suite: Path, output_dir: Path) -> list[str]:
    """Always `--track` so the triggered run lands in the store this dashboard reads."""
    return [
        sys.executable,
        "-m",
        "vitalprobe",
        "run",
        "--suite",
        str(suite),
        "--output",
        str(output_dir),
        "--track",
    ]


def run_cli_subprocess(argv: list[str], env: dict[str, str], timeout_s: float) -> TriggerOutcome:
    """Run the CLI as a child process — fixed interpreter, list argv, no shell."""
    try:
        completed = subprocess.run(
            argv,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout if isinstance(exc.stdout, str) else ""
        return TriggerOutcome(exit_code=None, output=partial, timed_out=True)
    output = completed.stdout
    if completed.stderr:
        output = f"{output}\n{completed.stderr}" if output else completed.stderr
    return TriggerOutcome(exit_code=completed.returncode, output=output.strip())
