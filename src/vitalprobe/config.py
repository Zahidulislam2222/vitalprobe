"""Runtime settings. All config comes from the environment / .env — never hardcoded (Rule 12)."""

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


def get_settings() -> Settings:
    return Settings()
