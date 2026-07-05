"""Write run.json (§2.4) with mandatory credential redaction."""

from pathlib import Path

from vitalprobe.schema import RunResult

REDACTED = "[REDACTED]"


def redact_secrets(text: str, secrets: list[str]) -> str:
    """Remove every known secret value from an output string. Secrets are ALWAYS redacted (§2.4)."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    return text


def render_run_json(run: RunResult, secrets: list[str]) -> str:
    payload = run.model_dump_json(by_alias=True, indent=2)
    return redact_secrets(payload, secrets)


def write_run_json(run: RunResult, output_dir: Path, secrets: list[str]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "run.json"
    path.write_text(render_run_json(run, secrets), encoding="utf-8")
    return path
