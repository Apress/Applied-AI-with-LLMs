from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    tmdb_api_key: str
    telegram_bot_token: str
    database_url: str

    llm_provider: Literal["none", "gemini"] = "none"
    llm_api_key: str | None = None
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    llm_model: str = "gemini-2.5-flash-lite"

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
