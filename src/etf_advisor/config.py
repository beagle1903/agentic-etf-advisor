"""Environment-backed application settings."""

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmProvider(StrEnum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


class Settings(BaseSettings):
    """Runtime settings with safe local defaults and no embedded credentials."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    llm_provider: LlmProvider = LlmProvider.OLLAMA

    chroma_host: str = "localhost"
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    neo4j_uri: str = "neo4j://localhost:17687"


settings = Settings()
