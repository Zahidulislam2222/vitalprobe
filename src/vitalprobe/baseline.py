"""Compare canonical VitalProbe run.json artifacts."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from vitalprobe.experience.store import compare_regressions
from vitalprobe.schema import RunResult, Verdict


class BaselineError(Exception):
    """A baseline/current artifact could not be read as a canonical RunResult."""


@dataclass(frozen=True, slots=True)
class CaseChange:
    case_id: str
    previous: Verdict
    current: Verdict


@dataclass(frozen=True, slots=True)
class CaseState:
    case_id: str
    verdict: Verdict


@dataclass(frozen=True, slots=True)
class RunComparison:
    regressions: list[CaseChange]
    improvements: list[CaseChange]
    new_cases: list[CaseState]
    removed_cases: list[CaseState]


def load_run(path: Path) -> RunResult:
    """Load one canonical run artifact with a path-specific error."""
    try:
        return RunResult.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise BaselineError(f"cannot load run artifact {path}: {exc}") from exc


def compare_runs(baseline: RunResult, current: RunResult) -> RunComparison:
    """Compare shared case IDs plus new/removed cases.

    Regressions follow the stable M4 contract: PASS→WARN/FAIL.
    Improvements are the inverse product signal: WARN/FAIL→PASS.
    """
    before = {result.id: result.verdict for result in baseline.results}
    after = {result.id: result.verdict for result in current.results}
    regressions = [
        CaseChange(item.case_id, item.previous, item.current)
        for item in compare_regressions(baseline, current)
    ]
    improvements = sorted(
        [
            CaseChange(case_id, previous, after[case_id])
            for case_id, previous in before.items()
            if previous in (Verdict.WARN, Verdict.FAIL)
            and after.get(case_id) is Verdict.PASS
        ],
        key=lambda item: item.case_id,
    )
    new_cases = [
        CaseState(case_id, after[case_id]) for case_id in sorted(after.keys() - before.keys())
    ]
    removed_cases = [
        CaseState(case_id, before[case_id]) for case_id in sorted(before.keys() - after.keys())
    ]
    return RunComparison(
        regressions=regressions,
        improvements=improvements,
        new_cases=new_cases,
        removed_cases=removed_cases,
    )
