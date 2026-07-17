"""Runtime settings. All config comes from the environment / .env, never source constants."""

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VITALPROBE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    target_url: str = ""
    target_token: str = ""
    db_path: Path = Path("artifacts/vitalprobe.db")
    license_file: Path | None = None
    judge: str = "none"
    judge_model: str = ""
    openai_api_key: str = Field(
        "", validation_alias=AliasChoices("OPENAI_API_KEY", "VITALPROBE_OPENAI_API_KEY")
    )
    anthropic_api_key: str = Field(
        "", validation_alias=AliasChoices("ANTHROPIC_API_KEY", "VITALPROBE_ANTHROPIC_API_KEY")
    )
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    ollama_host: str = Field(
        "http://localhost:11434",
        validation_alias=AliasChoices("OLLAMA_HOST", "VITALPROBE_OLLAMA_HOST"),
    )
    openai_responses_path: str = "/responses"
    anthropic_messages_path: str = "/messages"
    anthropic_api_version: str = "2023-06-01"
    ollama_chat_path: str = "/api/chat"
    judge_timeout_s: float = 60
    judge_estimated_tokens_per_case: int = 1500
    anthropic_max_tokens: int = 500
    local_model: str = ""
    judge_ollama_think: bool = False
    generator_temperature: float = 1.0
    generator_max_tokens: int = 400
    local_judge_max_attempts: int = Field(3, ge=1)
    simulator_temperature: float = 0.8
    simulator_max_tokens: int = 200
    judge_input_price_per_million: float = 0
    judge_output_price_per_million: float = 0
    demo_responses_file: Path | None = None
    demo_provider: Literal["scripted", "ollama"] = Field(
        "scripted",
        validation_alias=AliasChoices("DEMOBOT_PROVIDER", "VITALPROBE_DEMO_PROVIDER"),
    )
    demo_model: str = Field(
        "",
        validation_alias=AliasChoices("DEMOBOT_MODEL", "VITALPROBE_DEMO_MODEL"),
    )
    demo_system_prompt_file: Path | None = None
    demo_temperature: float = 0.2
    demo_max_tokens: int = 180
    demo_timeout_s: float = 120
    demo_ollama_think: bool = False
    runner_concurrency: int = Field(4, ge=1)
    # Localhost by design (BUILD-PLAN §9): the dashboard is local-only, no accounts.
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = Field(8800, ge=1, le=65535)
    dashboard_runs_dir: Path = Path("artifacts/dashboard-runs")
    dashboard_run_timeout_s: float = Field(600, gt=0)
    dashboard_output_tail_chars: int = Field(8000, ge=1)
    drafts_dir: Path = Path("artifacts/drafts")
    # Law content lives in the PRIVATE packs bundle; there is no valid default path here.
    law_dir: Path | None = None


def get_settings() -> Settings:
    return Settings()
