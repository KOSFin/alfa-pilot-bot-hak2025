"""Configuration module for environment-driven settings."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent.parent / ".env", env_file_encoding="utf-8", extra="allow")


    project_name: str = Field(default="Alfa Pilot Smart Calculator")
    environment: Literal["local", "dev", "prod"] = Field(default="local")
    api_prefix: str = Field(default="/api", alias="API_PREFIX")
    api_base_url: str = Field(default="http://localhost:8000/api", alias="AI_LLM_API_BASE_URL")
    webhook_base_url: Optional[str] = Field(default=None, alias="WEBHOOK_BASE_URL")
    webhook_secret_token: Optional[str] = Field(default=None, alias="WEBHOOK_SECRET_TOKEN")


    bot_token: str = Field(alias="BOT_TOKEN")
    twa_url: str = Field(alias="TWA_URL")


    gemini_api_key: str = Field(alias="API_KEY_AI_MODEL")
    llm_api_base_url: str = Field(default="https://ai.megallm.io/v1", alias="AI_LLM_API_BASE_URL")
    llm_model_name: str = Field(default="gemini-2.5-flash", alias="LLM_MODEL_NAME")
    embedding_model: str = Field(default="simple-tfidf", alias="EMBEDDING_MODEL")
    groq_api_key: str = Field(alias="API_KEY_SPEECH2TEXT")
    groq_api_url: str = Field(alias="API_URL_SPEECH2TEXT")


    redis_url: str = Field(alias="REDIS_URL")
    opensearch_url: str = Field(alias="OPENSEARCH_URL")


    data_dir: Path = Field(default=Path(__file__).resolve().parent.parent / "data")
    uploads_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent / "data" / "uploads")


    debug: bool = Field(default=False)
    opensearch_index: str = Field(default="alfa-pilot-knowledge")
    opensearch_chat_index: str = Field(default="alfa-pilot-dialogs")
    calculator_tool_name: str = Field(default="python_code_executor")
    calculator_timeout_sec: int = Field(default=10)


    enable_tool_audit: bool = Field(default=True)
    enable_telegram_bot: bool = Field(default=True, alias="ENABLE_TELEGRAM_BOT")

    def ensure_directories(self) -> None:
        """Ensure that runtime directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
