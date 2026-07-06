"""Config-driven REST adapter (BUILD-PLAN M1 step 3).

The adapter config is a small YAML file describing how to call the target:

    method: POST
    url_env: VITALPROBE_TARGET_URL
    headers:
      Authorization: "Bearer ${VITALPROBE_TARGET_TOKEN}"
    request_template:
      message: "{{last_user_message}}"
    response_path: "reply"
    timeout_s: 30

Placeholders: `{{last_user_message}}` and `{{turns_json}}`. A template value that is EXACTLY
`{{turns_json}}` becomes the structured turn list; inside a longer string it becomes JSON text.
`${VAR}` in header values expands from the environment; headers with unset vars are dropped.
Response extraction uses a simple dot-path (`data.reply`, `choices.0.message.content`).
Retries: 2 (3 attempts total) on network errors and 5xx only.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx
import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from vitalprobe.schema import ResponseMeta, Turn

_ENV_VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class AdapterError(Exception):
    """The target could not be reached or its response was unusable. Becomes an ERROR verdict."""


class _RetryableStatus(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"server error {status_code}")
        self.status_code = status_code


class AdapterConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = "POST"
    url: str | None = None
    url_env: str = "VITALPROBE_TARGET_URL"
    headers: dict[str, str] = {}
    request_template: dict[str, Any] = {"message": "{{last_user_message}}"}
    response_path: str = "reply"
    timeout_s: float = 30.0
    retry_attempts: int = Field(default=3, ge=1)
    retry_wait_multiplier_s: float = Field(default=0.2, ge=0)
    retry_wait_max_s: float = Field(default=2, ge=0)


def load_adapter_config(path: Path) -> AdapterConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise AdapterError(f"cannot read adapter config {path}: {exc}") from exc
    try:
        return AdapterConfig.model_validate(raw)
    except ValidationError as exc:
        raise AdapterError(f"invalid adapter config {path}: {exc}") from exc


def _expand_headers(headers: dict[str, str]) -> dict[str, str]:
    expanded: dict[str, str] = {}
    for name, value in headers.items():
        missing = False

        def _sub(match: re.Match[str]) -> str:
            nonlocal missing
            var = os.environ.get(match.group(1), "")
            if not var:
                missing = True
            return var

        result = _ENV_VAR_RE.sub(_sub, value)
        if not missing:
            expanded[name] = result
    return expanded


def _fill_placeholders(value: Any, turns: list[Turn]) -> Any:
    last_user = next((t.content for t in reversed(turns) if t.role == "user"), "")
    turns_json = json.dumps([t.model_dump() for t in turns], ensure_ascii=False)
    if isinstance(value, str):
        if value == "{{turns_json}}":
            return [t.model_dump() for t in turns]
        return value.replace("{{last_user_message}}", last_user).replace(
            "{{turns_json}}", turns_json
        )
    if isinstance(value, dict):
        return {k: _fill_placeholders(v, turns) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill_placeholders(v, turns) for v in value]
    return value


def _extract_path(payload: Any, dot_path: str) -> Any:
    current = payload
    for part in dot_path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise AdapterError(f"response path '{dot_path}': key '{part}' not found")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise AdapterError(
                    f"response path '{dot_path}': bad list index '{part}'"
                ) from exc
        else:
            raise AdapterError(
                f"response path '{dot_path}': cannot descend into {type(current).__name__}"
            )
    return current


def redact_endpoint(url: str) -> str:
    """Strip credentials-bearing parts of a URL for reports."""
    without_query = url.split("?", 1)[0]
    return re.sub(r"//[^@/]+@", "//", without_query)


class RestAdapter:
    name = "rest"

    def __init__(self, config: AdapterConfig, client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        url = config.url or os.environ.get(config.url_env, "")
        if not url:
            raise AdapterError(
                f"no target URL: set {config.url_env} in the environment "
                "or 'url' in the adapter config"
            )
        self.url = url
        self._client = client or httpx.AsyncClient(timeout=config.timeout_s)

    @property
    def endpoint_redacted(self) -> str:
        return redact_endpoint(self.url)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def send(self, turns: list[Turn]) -> ResponseMeta:
        body = _fill_placeholders(self.config.request_template, turns)
        headers = _expand_headers(self.config.headers)
        started = time.perf_counter()

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.config.retry_attempts),
            wait=wait_exponential(
                multiplier=self.config.retry_wait_multiplier_s,
                max=self.config.retry_wait_max_s,
            ),
            retry=retry_if_exception_type((httpx.TransportError, _RetryableStatus)),
        )
        async def _do_request() -> httpx.Response:
            response = await self._client.request(
                self.config.method, self.url, json=body, headers=headers
            )
            if response.status_code >= 500:
                raise _RetryableStatus(response.status_code)
            return response

        try:
            response = await _do_request()
        except _RetryableStatus as exc:
            raise AdapterError(f"target kept returning {exc.status_code}") from exc
        except httpx.TransportError as exc:
            raise AdapterError(f"cannot reach target: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)

        text: str
        try:
            payload = response.json()
            extracted = _extract_path(payload, self.config.response_path)
            text = extracted if isinstance(extracted, str) else json.dumps(extracted)
        except (json.JSONDecodeError, AdapterError):
            # Non-JSON or unexpected shape: keep the raw body so checks (and humans) can see it.
            text = response.text

        return ResponseMeta(text=text, status_code=response.status_code, latency_ms=latency_ms)
