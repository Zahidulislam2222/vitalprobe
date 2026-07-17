"""Law-mapping (M7 step 4): resolve case `law_refs` against law schema YAML files.

Law content itself lives in the PRIVATE packs repo (`law/*.yaml`); this module only
defines the schema and resolution. Mapping is informational — the report always carries
LAW_DISCLAIMER verbatim and never claims compliance.
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

LAW_DISCLAIMER = (
    "Informational mapping to help you discuss compliance with your counsel. "
    "Law summaries were drafted with AI assistance and have not been reviewed "
    "by an attorney. Not legal advice."
)


class LawRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    req_id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    summary: str
    citation: str


class LawFile(BaseModel):
    """One statute/regulation file (`law/<law_id>.yaml`)."""

    model_config = ConfigDict(extra="forbid")

    law_id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    jurisdiction: str
    name: str
    status: str
    effective_date: str
    source_url: str
    requirements: list[LawRequirement] = Field(min_length=1)


@dataclass
class LawLoadError(Exception):
    """Raised on invalid law files or unresolvable refs. One problem per entry."""

    errors: list[str]

    def __str__(self) -> str:
        return "\n".join(self.errors)


@dataclass(frozen=True)
class ResolvedRequirement:
    """One requirement a finding maps to, ready for report rendering."""

    law_id: str
    law_name: str
    jurisdiction: str
    status: str
    req_id: str
    summary: str
    citation: str


LawIndex = dict[str, LawFile]


def load_law_dir(law_dir: Path) -> LawIndex:
    """Load every `*.yaml` in `law_dir`. Raises LawLoadError listing ALL problems found."""
    errors: list[str] = []
    if not law_dir.is_dir():
        raise LawLoadError([f"law directory not found: {law_dir}"])
    files = sorted(law_dir.glob("*.yaml"))
    if not files:
        errors.append(f"no law YAML files found in {law_dir}")
    index: LawIndex = {}
    for file in files:
        try:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{file.name}: invalid YAML: {exc}")
            continue
        if not isinstance(raw, dict):
            errors.append(f"{file.name}: expected a mapping")
            continue
        try:
            law = LawFile.model_validate(raw)
        except ValidationError as exc:
            errors.extend(
                f"{file.name}: {'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            continue
        if law.law_id != file.stem:
            errors.append(f"{file.name}: law_id '{law.law_id}' does not match filename")
            continue
        if law.law_id in index:
            errors.append(f"{file.name}: duplicate law_id '{law.law_id}'")
            continue
        index[law.law_id] = law
    if errors:
        raise LawLoadError(errors)
    return index


def resolve_refs(refs: list[str], index: LawIndex) -> list[ResolvedRequirement]:
    """Resolve `law_refs` entries — `<law_id>:<req_id>` or bare `<law_id>` (every
    requirement). Raises LawLoadError on any unknown ref: a citation must never
    silently drop out of a compliance dossier."""
    errors: list[str] = []
    resolved: list[ResolvedRequirement] = []
    for ref in refs:
        law_id, _, req_id = ref.partition(":")
        law = index.get(law_id)
        if law is None:
            errors.append(f"unknown law '{law_id}' in law_ref '{ref}'")
            continue
        requirements = law.requirements
        if req_id:
            requirements = [r for r in law.requirements if r.req_id == req_id]
            if not requirements:
                errors.append(f"unknown requirement '{req_id}' in law_ref '{ref}'")
                continue
        resolved.extend(
            ResolvedRequirement(
                law_id=law.law_id,
                law_name=law.name,
                jurisdiction=law.jurisdiction,
                status=law.status,
                req_id=r.req_id,
                summary=r.summary,
                citation=r.citation,
            )
            for r in requirements
        )
    if errors:
        raise LawLoadError(errors)
    return resolved


def validate_suite_refs(all_refs: list[list[str]], index: LawIndex) -> None:
    """Fail fast on any unresolvable ref anywhere in a suite (config error, exit 2)."""
    errors: list[str] = []
    for refs in all_refs:
        try:
            resolve_refs(refs, index)
        except LawLoadError as exc:
            errors.extend(e for e in exc.errors if e not in errors)
    if errors:
        raise LawLoadError(errors)
