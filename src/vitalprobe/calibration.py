"""Calibration harness (M6 step 4): every judge scores the SAME case/response items,
the founder labels them, and per-judge agreement statistics quantify local-judge trust."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel

from vitalprobe.baseline import BaselineError, load_run
from vitalprobe.judges.base import JudgeBackend, JudgeError, Rubric, load_rubric
from vitalprobe.packs.loader import LoadedSuite
from vitalprobe.report.json_report import redact_secrets
from vitalprobe.schema import JudgeResult, TestCase, Verdict

LABEL_VERDICTS = (Verdict.PASS, Verdict.WARN, Verdict.FAIL)
TEMPLATE_FIELDS = [
    "item_id",
    "case_id",
    "severity",
    "category",
    "last_user_message",
    "response_text",
    "human_verdict",
]


class CalibrationError(Exception):
    """A calibration input is missing or invalid."""


@dataclass(frozen=True)
class CalibrationItem:
    item_id: str
    case: TestCase
    response_text: str


class ItemScore(BaseModel):
    item_id: str
    verdict: Verdict | None = None
    score: float | None = None
    rationale: str = ""
    error: str | None = None


class JudgeAgreement(BaseModel):
    judge: str
    labeled_items: int
    percent_agreement: float
    cohen_kappa: float | None
    confusion: dict[str, dict[str, int]]
    per_severity_agreement: dict[str, float]


def load_items(suite: LoadedSuite, response_paths: list[Path]) -> list[CalibrationItem]:
    """Pair every scoreable run result with its suite case. Items keep run identity so the
    same case from different demo-bot runs stays a distinct calibration item."""
    cases = {case.id: case for case in suite.cases}
    items: list[CalibrationItem] = []
    for path in response_paths:
        try:
            run = load_run(path if path.is_file() else path / "run.json")
        except BaselineError as exc:
            raise CalibrationError(str(exc)) from exc
        for result in run.results:
            case = cases.get(result.id)
            if case is None or not result.response_text:
                continue
            items.append(
                CalibrationItem(
                    item_id=f"{run.run_id[:8]}:{result.id}",
                    case=case,
                    response_text=result.response_text,
                )
            )
    if not items:
        raise CalibrationError("no scoreable case/response items found in the given runs")
    return items


def resolve_rubric(case: TestCase, default_rubric: str) -> Rubric:
    rubric_id = case.expect.judge.rubric if case.expect.judge is not None else default_rubric
    if not rubric_id:
        raise CalibrationError(
            f"case '{case.id}' has no judge rubric and no --rubric default was given"
        )
    return load_rubric(rubric_id)


async def score_items(
    judges: dict[str, JudgeBackend],
    items: list[CalibrationItem],
    default_rubric: str,
) -> dict[str, list[ItemScore]]:
    """Sequential on purpose: local CPU judging must not overload the founder machine."""
    scores: dict[str, list[ItemScore]] = {}
    for name, judge in judges.items():
        judge_scores: list[ItemScore] = []
        for item in items:
            rubric = resolve_rubric(item.case, default_rubric)
            try:
                result: JudgeResult = await judge.score(rubric, item.case, item.response_text)
                judge_scores.append(
                    ItemScore(
                        item_id=item.item_id,
                        verdict=result.verdict,
                        score=result.score,
                        rationale=result.rationale,
                    )
                )
            except (JudgeError, ValueError) as exc:
                judge_scores.append(ItemScore(item_id=item.item_id, error=str(exc)))
        scores[name] = judge_scores
    return scores


def write_labels_template(
    items: list[CalibrationItem], path: Path, *, secrets: list[str] | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = path.open("x", encoding="utf-8", newline="")
    except FileExistsError:
        return
    with handle:
        writer = csv.DictWriter(handle, fieldnames=TEMPLATE_FIELDS)
        writer.writeheader()
        for item in items:
            user_turns = [t.content for t in item.case.input.turns if t.role == "user"]
            row = {
                "item_id": item.item_id,
                "case_id": item.case.id,
                "severity": item.case.severity,
                "category": item.case.category,
                "last_user_message": user_turns[-1] if user_turns else "",
                "response_text": item.response_text,
                "human_verdict": "",
            }
            writer.writerow(
                {key: redact_secrets(value, secrets or []) for key, value in row.items()}
            )


def read_labels(path: Path) -> dict[str, Verdict]:
    """Read founder labels; rows with an empty human_verdict are skipped, invalid values fail."""
    labels: dict[str, Verdict] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"item_id", "human_verdict"} <= set(reader.fieldnames):
            raise CalibrationError(
                f"labels file {path} must have 'item_id' and 'human_verdict' columns"
            )
        for row in reader:
            raw = (row.get("human_verdict") or "").strip().upper()
            if not raw:
                continue
            if raw not in {v.value for v in LABEL_VERDICTS}:
                raise CalibrationError(
                    f"invalid human_verdict '{raw}' for item {row.get('item_id')}"
                    " (allowed: PASS, WARN, FAIL)"
                )
            labels[str(row["item_id"])] = Verdict(raw)
    return labels


def cohen_kappa(pairs: list[tuple[Verdict, Verdict]]) -> float | None:
    """Cohen's kappa over PASS/WARN/FAIL. None when chance agreement is 1 (kappa undefined)."""
    n = len(pairs)
    if n == 0:
        return None
    observed = sum(a is b for a, b in pairs) / n
    expected = sum(
        (sum(a is v for a, _ in pairs) / n) * (sum(b is v for _, b in pairs) / n)
        for v in LABEL_VERDICTS
    )
    if expected == 1:
        return None
    return (observed - expected) / (1 - expected)


def agreement_for_judge(
    judge: str,
    scores: list[ItemScore],
    labels: dict[str, Verdict],
    items: list[CalibrationItem],
) -> JudgeAgreement:
    severity_by_item = {item.item_id: item.case.severity for item in items}
    pairs: list[tuple[Verdict, Verdict]] = []
    confusion = {h.value: {j.value: 0 for j in LABEL_VERDICTS} for h in LABEL_VERDICTS}
    per_severity: dict[str, list[bool]] = {}
    for score in scores:
        human = labels.get(score.item_id)
        if human is None or score.verdict is None:
            continue
        pairs.append((human, score.verdict))
        confusion[human.value][score.verdict.value] += 1
        severity = severity_by_item.get(score.item_id, "unknown")
        per_severity.setdefault(severity, []).append(human is score.verdict)
    return JudgeAgreement(
        judge=judge,
        labeled_items=len(pairs),
        percent_agreement=(
            round(100 * sum(a is b for a, b in pairs) / len(pairs), 1) if pairs else 0.0
        ),
        cohen_kappa=(round(kappa, 3) if (kappa := cohen_kappa(pairs)) is not None else None),
        confusion=confusion,
        per_severity_agreement={
            severity: round(100 * sum(hits) / len(hits), 1)
            for severity, hits in sorted(per_severity.items())
        },
    )


def write_reports(
    output_dir: Path,
    items: list[CalibrationItem],
    scores: dict[str, list[ItemScore]],
    agreements: list[JudgeAgreement],
    labeled_count: int,
    *,
    secrets: list[str] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "item_count": len(items),
        "labeled_count": labeled_count,
        "judges": {
            name: [score.model_dump(mode="json") for score in judge_scores]
            for name, judge_scores in scores.items()
        },
        "agreement": [agreement.model_dump(mode="json") for agreement in agreements],
    }
    (output_dir / "calibration.json").write_text(
        redact_secrets(json.dumps(payload, indent=2), secrets or []), encoding="utf-8"
    )

    lines = [
        "# VitalProbe local-judge calibration report",
        "",
        f"- Items scored: {len(items)}",
        f"- Items with human labels: {labeled_count}",
        f"- Judges: {', '.join(scores)}",
        "",
    ]
    if not agreements:
        lines += [
            "No human labels yet. Fill `labels_template.csv` (human_verdict = PASS/WARN/FAIL)",
            "and re-run `vitalprobe calibrate` with `--labels` to compute agreement statistics.",
        ]
    for agreement in agreements:
        kappa = "n/a" if agreement.cohen_kappa is None else f"{agreement.cohen_kappa}"
        lines += [
            f"## Judge: {agreement.judge}",
            "",
            f"- Labeled items compared: {agreement.labeled_items}",
            f"- Percent agreement with human labels: {agreement.percent_agreement}%",
            f"- Cohen's kappa: {kappa}",
            "",
            "| human \\ judge | " + " | ".join(v.value for v in LABEL_VERDICTS) + " |",
            "|---|" + "---|" * len(LABEL_VERDICTS),
        ]
        for human in LABEL_VERDICTS:
            row = agreement.confusion[human.value]
            lines.append(
                f"| {human.value} | " + " | ".join(str(row[v.value]) for v in LABEL_VERDICTS) + " |"
            )
        lines.append("")
        if agreement.per_severity_agreement:
            lines.append("Per-severity agreement:")
            lines += [
                f"- {severity}: {value}%"
                for severity, value in agreement.per_severity_agreement.items()
            ]
            lines.append("")
    (output_dir / "calibration_report.md").write_text(
        redact_secrets("\n".join(lines) + "\n", secrets or []), encoding="utf-8"
    )
