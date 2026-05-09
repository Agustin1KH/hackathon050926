"""Application configuration via pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    llm_provider: Literal["anthropic", "openai"] = "anthropic"

    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Reddit discovery uses the anonymous public JSON endpoint - no API key needed.
    # Reddit only requires a descriptive User-Agent string for low-volume access.
    reddit_user_agent: str = "synthaudience:v0.1.0"

    browse_model: str = "claude-haiku-4-5-20251001"
    eval_model: str = "claude-sonnet-4-6"

    discovery_interval_minutes: int = 60

    database_url: str = "sqlite:///data/synthaudience.db"
    chroma_persist_dir: str = "data/chroma"

    @property
    def data_dir(self) -> Path:
        return Path("data")


def get_settings() -> Settings:
    return Settings()
