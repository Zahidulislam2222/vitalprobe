"""End-to-end run over the seeded mock target: all four verdicts + golden run.json + redaction."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from conftest import FAKE_TOKEN
from vitalprobe.config import get_settings
from vitalprobe.packs.loader import load_suite
from vitalprobe.report.json_report import REDACTED, write_run_json
from vitalprobe.runner import run_suite
from vitalprobe.schema import JudgeResult, RunResult, RunVerdict, Turn, Verdict
from vitalprobe.targets.rest import AdapterConfig, AdapterError, RestAdapter, load_adapter_config

DATA_DIR = Path(__file__).parent / "data"
SUITE_DIR = DATA_DIR / "suite"
GOLDEN_PATH = DATA_DIR / "golden_run.json"

VOLATILE_FIELDS = {"run_id", "started_at", "finished_at", "latency_ms"}


def _normalize(value: Any) -> Any:
    """Strip volatile fields (timestamps, uuid, latency) for field-by-field comparison."""
    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items() if k not in VOLATILE_FIELDS}
    if isinstance(value, list):
        return [_normalize(v) for v in value]
    return value


async def _execute(mock_client: httpx.AsyncClient, judge: Any = None) -> RunResult:
    suite = load_suite(SUITE_DIR)
    config = load_adapter_config(SUITE_DIR / "adapter.default.yaml")
    adapter = RestAdapter(config, client=mock_client)
    try:
        return await run_suite(
            suite,
            adapter,
            judge,
            max_concurrency=get_settings().runner_concurrency,
        )
    finally:
        await adapter.aclose()


async def test_run_produces_all_four_verdicts(
    target_env: None, mock_client: httpx.AsyncClient
) -> None:
    run = await _execute(mock_client)
    verdicts = {r.id: r.verdict for r in run.results}
    assert verdicts["seed-pass-001"] == Verdict.PASS
    assert verdicts["seed-warn-001"] == Verdict.WARN
    assert verdicts["seed-fail-001"] == Verdict.FAIL
    assert verdicts["seed-error-001"] == Verdict.ERROR
    assert run.verdict == RunVerdict.FAILED
    assert run.counts.pass_ == 1
    assert run.counts.warn == 1
    assert run.counts.fail == 1
    assert run.counts.error == 1
    error_result = next(r for r in run.results if r.id == "seed-error-001")
    assert error_result.error is not None  # reported, never silently skipped


async def test_run_json_redacts_secrets_and_query_params(
    target_env: None, mock_client: httpx.AsyncClient, tmp_path: Path
) -> None:
    run = await _execute(mock_client)
    path = write_run_json(run, tmp_path, secrets=[FAKE_TOKEN])
    content = path.read_text(encoding="utf-8")
    assert FAKE_TOKEN not in content
    assert REDACTED in content
    payload = json.loads(content)
    assert "?" not in payload["target"]["endpoint_redacted"]  # query string stripped
    assert "pass" in payload["counts"]  # serialized with the §2.4 alias, not pass_


async def test_golden_run_json_field_by_field(
    target_env: None, mock_client: httpx.AsyncClient, tmp_path: Path
) -> None:
    run = await _execute(mock_client)
    path = write_run_json(run, tmp_path, secrets=[FAKE_TOKEN])
    actual = _normalize(json.loads(path.read_text(encoding="utf-8")))
    if not GOLDEN_PATH.exists():
        pytest.fail(f"golden file missing: {GOLDEN_PATH}")
    golden = _normalize(json.loads(GOLDEN_PATH.read_text(encoding="utf-8")))
    # suite path differs by machine; compare everything else
    actual["suite"].pop("path", None)
    golden["suite"].pop("path", None)
    assert actual == golden


async def test_semantic_judge_can_lower_deterministic_pass(
    target_env: None, mock_client: httpx.AsyncClient
) -> None:
    class FailingJudge:
        async def score(self, rubric: Any, case: Any, response_text: str) -> JudgeResult:
            return JudgeResult(
                rubric=rubric.id,
                score=1,
                threshold=4,
                verdict=Verdict.FAIL,
                rationale="The response is subtly unsafe.",
                model="mock-judge",
            )

    run = await _execute(mock_client, FailingJudge())
    result = next(item for item in run.results if item.id == "seed-pass-001")
    assert result.judge is not None
    assert result.judge.verdict is Verdict.FAIL
    assert result.verdict is Verdict.FAIL


async def test_rest_retry_attempts_are_adapter_configurable() -> None:
    attempts = 0

    async def always_timeout(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectTimeout("seeded timeout", request=request)

    config = AdapterConfig(
        url="https://example.test/chat",
        retry_attempts=1,
        retry_wait_multiplier_s=0,
        retry_wait_max_s=0,
    )
    client = httpx.AsyncClient(transport=httpx.MockTransport(always_timeout))
    adapter = RestAdapter(config, client=client)
    try:
        with pytest.raises(AdapterError, match="cannot reach target"):
            await adapter.send([Turn(role="user", content="synthetic")])
    finally:
        await adapter.aclose()
    assert attempts == 1
