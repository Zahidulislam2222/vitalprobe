"""Loader validation tests (BUILD-PLAN M1 step 8)."""

from pathlib import Path

import pytest

from vitalprobe.packs.loader import SuiteLoadError, load_suite

DATA_DIR = Path(__file__).parent / "data"
SUITE_DIR = DATA_DIR / "suite"
BROKEN_SUITE_DIR = DATA_DIR / "broken-suite"


def test_good_suite_loads_sorted_with_pack_meta() -> None:
    suite = load_suite(SUITE_DIR)
    assert suite.name == "seed-suite"
    assert suite.pack_version == "1.0"
    ids = [c.id for c in suite.cases]
    assert ids == sorted(ids)
    assert len(suite.cases) == 4


def test_broken_suite_reports_file_case_and_problem() -> None:
    with pytest.raises(SuiteLoadError) as excinfo:
        load_suite(BROKEN_SUITE_DIR)
    text = str(excinfo.value)
    assert "bad.yaml" in text            # file named
    assert "broken-001" in text          # case id named
    assert "severity" in text            # bad severity reported
    assert "expect" in text              # missing expect reported
    assert "duplicate" in text.lower()   # duplicate id reported


def test_missing_directory_is_a_load_error(tmp_path: Path) -> None:
    with pytest.raises(SuiteLoadError):
        load_suite(tmp_path / "does-not-exist")


def test_empty_directory_is_a_load_error(tmp_path: Path) -> None:
    with pytest.raises(SuiteLoadError):
        load_suite(tmp_path)


def test_invalid_yaml_is_reported(tmp_path: Path) -> None:
    (tmp_path / "case.yaml").write_text("id: [unclosed", encoding="utf-8")
    with pytest.raises(SuiteLoadError) as excinfo:
        load_suite(tmp_path)
    assert "invalid YAML" in str(excinfo.value)


def test_emergency_core_is_a_25_case_draft_with_required_distribution() -> None:
    suite = load_suite(Path(__file__).parents[1] / "packs" / "emergency-core")
    assert len(suite.cases) == 25
    assert all(case.status == "draft" for case in suite.cases)
    counts = {
        "emergency": sum(case.id.startswith("emerg-") for case in suite.cases),
        "medication": sum(case.id.startswith("med-") for case in suite.cases),
        "scope": sum(case.id.startswith("scope-") for case in suite.cases),
        "privacy": sum(case.id.startswith("privacy-") for case in suite.cases),
        "robustness": sum(case.id.startswith("robust-") for case in suite.cases),
    }
    assert counts == {
        "emergency": 8,
        "medication": 5,
        "scope": 4,
        "privacy": 4,
        "robustness": 4,
    }
