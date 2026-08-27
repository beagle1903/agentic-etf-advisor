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

    chroma_host: str = "localhost"
    chroma_port: int = Field(default=8000, ge=1, le=65535)
    chroma_collection: str = "etf_source_documents"
    neo4j_uri: str = "neo4j://localhost:17687"
    neo4j_auth: SecretStr = SecretStr("neo4j/local-dev-password")

    def neo4j_credentials(self) -> tuple[str, str]:
        """Return Neo4j credentials without exposing them in logs or CLI output."""

        username, separator, password = self.neo4j_auth.get_secret_value().partition("/")
        if not separator or not username or not password:
            raise ValueError("NEO4J_AUTH must use the format username/password.")
        return username, password


settings = Settings()
