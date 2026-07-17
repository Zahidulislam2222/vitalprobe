"""Guardrails that keep the compliance posture from silently regressing.

VitalProbe's legal position rests on three invariants (BUILD-PLAN section 7):
it never claims compliance/certification/approval, every law and report
surface carries its disclaimer verbatim, and the CLI never phones home.
These tests fail the suite the moment a future change breaks one of them.
"""

import re
import subprocess
from pathlib import Path

from vitalprobe.law import LAW_DISCLAIMER

ROOT = Path(__file__).parents[1]

SCANNED_SUFFIXES = {".py", ".md", ".j2", ".yaml", ".yml", ".txt", ".toml", ".html"}

# Positive compliance claims the product must never make about itself or a target.
BANNED_CLAIM_PATTERNS = [
    re.compile(r"\bHIPAA[-\s]?(?:compliant|certified|approved)\b", re.IGNORECASE),
    re.compile(r"\bGDPR[-\s]?(?:compliant|certified|approved)\b", re.IGNORECASE),
    re.compile(r"\bcompliant\s+with\s+(?:HIPAA|GDPR)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:ensur|deliver|provid|achiev|guarante)\w*\s+"
        r"(?:full\s+)?(?:HIPAA\s+|GDPR\s+)?compliance\b",
        re.IGNORECASE,
    ),
    re.compile(r"\blegally\s+compliant\b", re.IGNORECASE),
    re.compile(r"\bfully\s+compliant\b", re.IGNORECASE),
    re.compile(r"\bregulatory\s+approvals?\b", re.IGNORECASE),
    re.compile(r"\b(?:SOC\s*2|ISO\s*\d+|HITRUST)[-\s]?certified\b", re.IGNORECASE),
]

# Product surfaces (the code repo) additionally ban the bare word; reference
# docs legitimately discuss third-party certification programs, so they get a
# claim-shaped pattern instead ("earned/has/received ... certification").
STRICT_EXTRA_PATTERNS = [
    re.compile(r"\bcertification\b", re.IGNORECASE),
]
DOC_EXTRA_PATTERNS = [
    re.compile(
        r"\b(?:is|are|has|have|earned|obtained|passed|received|granted|holds?)\s+"
        r"(?:\w+\s+){0,2}certifi(?:cation|ed)\b",
        re.IGNORECASE,
    ),
]

# A match is allowed only when the same line negates it ("not a regulatory
# approval", "no certification", "never claim ... certified"). Known accepted
# limitation: a negation word within the window whitelists the rest of the
# line even when it does not grammatically negate the claim — this guard is a
# net for accidental drift, not a court; the compliance-auditor reads context.
NEGATION_BEFORE_MATCH = re.compile(
    r"\b(?:not|never|no|without|nor)\b[^.;\n]{0,70}$", re.IGNORECASE
)

TELEMETRY_IMPORT = re.compile(
    r"^\s*(?:import|from)\s+"
    r"(?:sentry_sdk|posthog|mixpanel|segment|amplitude|statsd|newrelic|datadog)\b",
    re.MULTILINE,
)


def _tracked_text_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        ROOT / path
        for path in result.stdout.decode().split("\0")
        if path
        and (ROOT / path).is_file()
        and (ROOT / path).suffix in SCANNED_SUFFIXES
    ]


def _unnegated_claim_hits(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    hits: list[str] = []
    for line in text.splitlines():
        for pattern in patterns:
            for match in pattern.finditer(line):
                if not NEGATION_BEFORE_MATCH.search(line[: match.start()]):
                    hits.append(line.strip())
    return hits


def test_no_positive_compliance_claims_in_tracked_files() -> None:
    offenders: dict[str, list[str]] = {}
    for path in _tracked_text_files():
        if path.name == "test_compliance_guard.py":
            continue
        hits = _unnegated_claim_hits(
            path.read_text(encoding="utf-8", errors="ignore"),
            BANNED_CLAIM_PATTERNS + STRICT_EXTRA_PATTERNS,
        )
        if hits:
            offenders[str(path.relative_to(ROOT))] = hits
    assert offenders == {}


def test_no_positive_compliance_claims_in_project_docs() -> None:
    """Also scan the docs folder one level above the repo, when it exists.

    BUILD-LOG/DOSSIER/plan files are where a session would most plausibly write
    an overclaim. The docs folder is intentionally not a git repo, so pytest is
    the only automation that reaches it. Skips silently on CI clones where the
    folder is absent. COMPLIANCE-GATE.md and CLAUDE.md quote the banned phrases
    on purpose and are excluded.
    """
    docs_root = ROOT.parent
    quoting_files = {"COMPLIANCE-GATE.md", "CLAUDE.md", "AGENTS.md"}
    offenders: dict[str, list[str]] = {}
    for path in docs_root.glob("*.md"):
        if path.name in quoting_files:
            continue
        hits = _unnegated_claim_hits(
            path.read_text(encoding="utf-8", errors="ignore"),
            BANNED_CLAIM_PATTERNS + DOC_EXTRA_PATTERNS,
        )
        if hits:
            offenders[path.name] = hits
    assert offenders == {}


def test_no_telemetry_or_phone_home_imports_in_source() -> None:
    offenders = [
        str(path.relative_to(ROOT))
        for path in (ROOT / "src").rglob("*.py")
        if TELEMETRY_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_no_telemetry_dependencies_declared() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").casefold()
    names = (
        "sentry", "posthog", "mixpanel", "segment",
        "amplitude", "statsd", "newrelic", "datadog",
    )
    for name in names:
        assert name not in pyproject


def test_law_disclaimer_keeps_required_caveats() -> None:
    lowered = LAW_DISCLAIMER.casefold()
    assert "not legal advice" in lowered
    assert "have not been reviewed by an attorney" in lowered
    assert "drafted with ai assistance" in lowered


def test_dossier_template_keeps_limitations_block() -> None:
    template = (
        ROOT / "src/vitalprobe/report/templates/dossier.html.j2"
    ).read_text(encoding="utf-8")
    assert "Methodology &amp; limitations" in template
    assert "not a regulatory approval, legal advice, a clinical assessment" in template
    assert "HIPAA" in template
