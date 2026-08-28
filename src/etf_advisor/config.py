"""Environment-backed application settings."""

from enum import StrEnum

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmProvider(StrEnum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


class Settings(BaseSettings):
    """Runtime settings with safe local defaults and no embedded credentials."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    llm_provider: LlmProvider = LlmProvider.OLLAMA
    ollama_base_url: str = "http://localhost:11434"
    ollama_api_key: SecretStr = SecretStr("")
    ollama_chat_model: str = ""
    openrouter_api_key: SecretStr = SecretStr("")
    openrouter_chat_model: str = ""

    chroma_host: str = "localhost"
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    chroma_collection: str = "etf_source_documents"
    neo4j_uri: str = "neo4j://localhost:17687"
    neo4j_auth: SecretStr = SecretStr("neo4j/local-dev-password")
    postgres_uri: SecretStr = SecretStr(
        "postgresql://etf_advisor:local-dev-password@127.0.0.1:5432/etf_advisor?connect_timeout=5"
    )
    market_data_max_age_hours: int = Field(default=120, ge=1, le=336)
    market_data_future_tolerance_minutes: int = Field(default=5, ge=0, le=60)
    yahoo_max_attempts: int = Field(default=3, ge=1, le=5)
    yahoo_retry_backoff_seconds: float = Field(default=0.25, ge=0, le=10)

    def neo4j_credentials(self) -> tuple[str, str]:
        """Return Neo4j credentials without exposing them in logs or CLI output."""

        username, separator, password = self.neo4j_auth.get_secret_value().partition("/")
        if not separator or not username or not password:
            raise ValueError("NEO4J_AUTH must use the format username/password.")
        return username, password


settings = Settings()
