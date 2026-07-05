"""Core contracts (BUILD-PLAN §2.1–§2.4). Everything depends on this; it depends on nothing."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG_ERROR = 2


class Verdict(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    ERROR = "ERROR"


class RunVerdict(StrEnum):
    PASSED = "PASSED"
    PASSED_WITH_WARNINGS = "PASSED_WITH_WARNINGS"
    FAILED = "FAILED"


Severity = Literal["critical", "high", "medium", "low"]
CaseStatus = Literal["draft", "reviewed"]

SEVERITY_ORDER: dict[str, int] = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class CheckSpec(BaseModel):
    """One check inside `expect.must` / `expect.warn`.

    `type` selects the evaluator; every other YAML key is an evaluator parameter.
    """

    model_config = ConfigDict(extra="allow")

    type: str

    def params(self) -> dict[str, Any]:
        return self.model_dump(exclude={"type"})


class JudgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rubric: str


class Expectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    must: list[CheckSpec] = Field(default_factory=list)
    warn: list[CheckSpec] = Field(default_factory=list)
    judge: JudgeSpec | None = None


class CaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turns: list[Turn] = Field(min_length=1)


class TestCase(BaseModel):
    """Test-case YAML schema v1 (§2.1)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    title: str
    category: str
    severity: Severity
    status: CaseStatus = "draft"
    languages: list[str] = Field(default_factory=lambda: ["en"])
    input: CaseInput
    expect: Expectation
    law_refs: list[str] = Field(default_factory=list)
    notes: str = ""


class ResponseMeta(BaseModel):
    """What the target adapter observed for one case."""

    model_config = ConfigDict(extra="forbid")

    text: str
    status_code: int | None = None
    latency_ms: int


class CheckResult(BaseModel):
    type: str
    passed: bool
    evidence: str


class JudgeResult(BaseModel):
    rubric: str
    score: float
    threshold: float
    verdict: Verdict
    rationale: str
    model: str


class TestResult(BaseModel):
    id: str
    title: str
    category: str
    severity: str
    verdict: Verdict
    latency_ms: int | None = None
    input_turns: list[Turn]
    response_text: str
    checks: list[CheckResult] = Field(default_factory=list)
    judge: JudgeResult | None = None
    error: str | None = None


class RunCounts(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # "pass" is a Python keyword, so the field is pass_ with "pass" used in JSON (§2.4)
    pass_: int = Field(0, validation_alias="pass", serialization_alias="pass")
    warn: int = 0
    fail: int = 0
    error: int = 0


class TargetInfo(BaseModel):
    endpoint_redacted: str
    adapter: str


class SuiteInfo(BaseModel):
    name: str
    path: str
    case_count: int
    pack_version: str | None = None


class RunResult(BaseModel):
    """Run-result contract (§2.4). Canonical format; storage layers index it, never replace it."""

    vitalprobe_version: str
    run_id: str
    started_at: str
    finished_at: str
    target: TargetInfo
    suite: SuiteInfo
    verdict: RunVerdict
    counts: RunCounts
    results: list[TestResult]


def case_verdict(check_results: list[CheckResult], must_count: int) -> Verdict:
    """Aggregate one case's checks per §2.3.

    The first `must_count` entries in `check_results` are the `must` checks; the rest are `warn`.
    """
    must = check_results[:must_count]
    warn = check_results[must_count:]
    if any(not c.passed for c in must):
        return Verdict.FAIL
    if any(not c.passed for c in warn):
        return Verdict.WARN
    return Verdict.PASS


def run_verdict(results: list[TestResult]) -> RunVerdict:
    """Aggregate the run verdict per §2.3. ERROR counts as FAIL for the run verdict —
    an unreachable target must never look like a pass."""
    if any(r.verdict in (Verdict.FAIL, Verdict.ERROR) for r in results):
        return RunVerdict.FAILED
    if any(r.verdict is Verdict.WARN for r in results):
        return RunVerdict.PASSED_WITH_WARNINGS
    return RunVerdict.PASSED


def count_results(results: list[TestResult]) -> RunCounts:
    counts = RunCounts()
    for r in results:
        if r.verdict is Verdict.PASS:
            counts.pass_ += 1
        elif r.verdict is Verdict.WARN:
            counts.warn += 1
        elif r.verdict is Verdict.FAIL:
            counts.fail += 1
        else:
            counts.error += 1
    return counts
