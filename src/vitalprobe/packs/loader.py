"""Load a suite directory of test-case YAML files into validated TestCase models.

Errors always name the file, the case id when known, and the problem (BUILD-PLAN M1 step 2).
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from vitalprobe.schema import TestCase

RESERVED_FILENAMES_PREFIXES = ("adapter", "pack")


@dataclass
class LoadedSuite:
    name: str
    path: Path
    cases: list[TestCase]
    pack_version: str | None = None


@dataclass
class SuiteLoadError(Exception):
    """Raised when a suite fails validation. `errors` is human-readable, one problem per entry."""

    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return "\n".join(self.errors)


def _format_validation_error(file: Path, exc: ValidationError, case_id: str | None) -> list[str]:
    ident = f" (case {case_id})" if case_id else ""
    out = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"])
        out.append(f"{file.name}{ident}: {loc}: {err['msg']}")
    return out


def load_suite(suite_dir: Path) -> LoadedSuite:
    """Load every case YAML in `suite_dir`. Raises SuiteLoadError listing ALL problems found."""
    errors: list[str] = []
    if not suite_dir.is_dir():
        raise SuiteLoadError([f"suite directory not found: {suite_dir}"])

    pack_name = suite_dir.name
    pack_version: str | None = None
    pack_meta = suite_dir / "pack.yaml"
    if pack_meta.is_file():
        try:
            meta = yaml.safe_load(pack_meta.read_text(encoding="utf-8")) or {}
            if not isinstance(meta, dict):
                errors.append("pack.yaml: expected a mapping with name/version")
            else:
                pack_name = str(meta.get("name", pack_name))
                if "version" in meta:
                    pack_version = str(meta["version"])
        except yaml.YAMLError as exc:
            errors.append(f"pack.yaml: invalid YAML: {exc}")

    case_files = sorted(
        p
        for p in suite_dir.glob("*.yaml")
        if not p.name.startswith(RESERVED_FILENAMES_PREFIXES)
    )
    if not case_files:
        errors.append(f"no test-case YAML files found in {suite_dir}")

    cases: list[TestCase] = []
    seen_ids: dict[str, str] = {}
    for file in case_files:
        try:
            raw = yaml.safe_load(file.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{file.name}: invalid YAML: {exc}")
            continue
        if raw is None:
            errors.append(f"{file.name}: file is empty")
            continue
        # A file may hold one case (mapping) or several (list of mappings).
        raw_cases = raw if isinstance(raw, list) else [raw]
        for idx, raw_case in enumerate(raw_cases):
            if not isinstance(raw_case, dict):
                errors.append(f"{file.name}: entry {idx} is not a mapping")
                continue
            case_id = raw_case.get("id") if isinstance(raw_case.get("id"), str) else None
            # Duplicate detection runs on the raw id so it works even when a case is invalid.
            if case_id is not None:
                if case_id in seen_ids:
                    errors.append(
                        f"{file.name}: duplicate case id '{case_id}' "
                        f"(first seen in {seen_ids[case_id]})"
                    )
                    continue
                seen_ids[case_id] = file.name
            try:
                case = TestCase.model_validate(raw_case)
            except ValidationError as exc:
                errors.extend(_format_validation_error(file, exc, case_id))
                continue
            cases.append(case)

    if errors:
        raise SuiteLoadError(errors)

    cases.sort(key=lambda c: c.id)
    return LoadedSuite(name=pack_name, path=suite_dir, cases=cases, pack_version=pack_version)
