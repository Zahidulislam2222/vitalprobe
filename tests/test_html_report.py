"""M2 self-contained HTML dossier tests."""

from pathlib import Path

import httpx

from conftest import FAKE_TOKEN
from vitalprobe.config import get_settings
from vitalprobe.packs.loader import load_suite
from vitalprobe.report.html_report import write_html_report
from vitalprobe.runner import run_suite
from vitalprobe.targets.rest import RestAdapter, load_adapter_config

DATA_DIR = Path(__file__).parent / "data"
SUITE_DIR = DATA_DIR / "suite"


async def test_html_report_is_complete_and_secret_free(
    target_env: None, mock_client: httpx.AsyncClient, tmp_path: Path
) -> None:
    suite = load_suite(SUITE_DIR)
    config = load_adapter_config(SUITE_DIR / "adapter.default.yaml")
    adapter = RestAdapter(config, client=mock_client)
    try:
        run = await run_suite(
            suite,
            adapter,
            max_concurrency=get_settings().runner_concurrency,
        )
    finally:
        await adapter.aclose()

    path = write_html_report(run, tmp_path, secrets=[FAKE_TOKEN])
    html = path.read_text(encoding="utf-8")

    assert "Clinician-Reviewed Dossier — UPCOMING" in html
    assert "This report was produced by the <strong>Automated tier</strong>." in html
    assert all(result.id in html for result in run.results)
    assert FAKE_TOKEN not in html
    assert "{{" not in html
    assert "${" not in html
    assert "<script" not in html.lower()
    assert 'src="http' not in html
    assert 'href="http' not in html
    assert "@media print" in html
    assert "/* BRAND" in html

    section_names = [
        "Executive summary",
        "Findings",
        "Methodology &amp; limitations",
        "Tiers",
    ]
    positions = [html.index(name) for name in section_names]
    assert positions == sorted(positions)
