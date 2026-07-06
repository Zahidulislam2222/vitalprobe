"""Persona YAML schema (BUILD-PLAN M8 step 1) and loading."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from vitalprobe.schema import CheckSpec, Severity


class PersonaError(Exception):
    """A persona file is missing or invalid."""


class ScriptedReveal(BaseModel):
    """A disclosure the patient makes verbatim at a fixed patient turn.

    Turn 1 is the opening message; a reveal at turn N replaces the generated
    patient message for that turn (deterministic escalation, testable)."""

    model_config = ConfigDict(extra="forbid")

    turn: int = Field(ge=2)
    message: str


class PersonaChecks(BaseModel):
    model_config = ConfigDict(extra="forbid")

    must: list[CheckSpec] = Field(default_factory=list)
    warn: list[CheckSpec] = Field(default_factory=list)


class Persona(BaseModel):
    """Synthetic patient persona. The patient-LLM plays this person; scripted
    reveals keep the safety-critical disclosures deterministic."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    title: str
    category: str
    severity: Severity
    age: int
    background: str
    condition: str
    goal: str
    disclosure_style: str
    opening_message: str
    escalation_script: list[ScriptedReveal] = Field(default_factory=list)
    max_turns: int = Field(6, ge=1, le=20)
    # The simulation stops early when the target escalates (regex, case-insensitive).
    stop_on_escalation: list[str] = Field(default_factory=list)
    checks: PersonaChecks
    notes: str = ""


def load_persona(path: Path) -> Persona:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PersonaError(f"cannot read persona {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise PersonaError(f"{path.name}: expected a mapping")
    try:
        return Persona.model_validate(raw)
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise PersonaError(f"{path.name}: {problems}") from exc


def load_personas(path: Path) -> list[Persona]:
    """Load one persona file or every `*.yaml` in a directory."""
    if path.is_file():
        return [load_persona(path)]
    if path.is_dir():
        files = sorted(path.glob("*.yaml"))
        if not files:
            raise PersonaError(f"no persona YAML files found in {path}")
        return [load_persona(file) for file in files]
    raise PersonaError(f"persona path not found: {path}")
