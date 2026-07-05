"""Runtime settings. All config comes from the environment / .env, never source constants."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VITALPROBE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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
    ollama_host: str = "http://localhost:11434"
    openai_responses_path: str = "/responses"
    anthropic_messages_path: str = "/messages"
    anthropic_api_version: str = "2023-06-01"
    ollama_chat_path: str = "/api/chat"
    judge_timeout_s: float = 60
    judge_estimated_tokens_per_case: int = 1500
    anthropic_max_tokens: int = 500
    local_model: str = ""
    judge_input_price_per_million: float = 0
    judge_output_price_per_million: float = 0
    demo_responses_file: Path | None = None


def get_settings() -> Settings:
    return Settings()
