"""
Application configuration.

Centralized settings loaded from environment variables / .env file.
In Azure, these are injected via App Service Application Settings and
secrets pulled from Azure Key Vault at startup (see core/azure_secrets.py).
"""
from functools import lru_cache
from typing import List, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    PROJECT_NAME: str = "AI Rental Decision Intelligence Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: Literal["development", "testing", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ------------------------------------------------------------------
    # Security
    # ------------------------------------------------------------------
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 10

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    # Stored as a raw comma-separated string on purpose: pydantic-settings
    # attempts to JSON-decode any List[...]-typed env var before custom
    # validators run, which breaks on plain comma-separated values like
    # "http://localhost:3000,http://localhost:5173". Parsing manually via
    # the property below sidesteps that entirely.
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "rental_admin"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "rental_ai_platform"
    DATABASE_URI: PostgresDsn | None = None

    @field_validator("DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_uri(cls, v, info):
        if isinstance(v, str) and v:
            return v
        data = info.data
        return (
            f"postgresql+psycopg2://{data.get('POSTGRES_USER')}:"
            f"{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_SERVER')}:"
            f"{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"
        )

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    # ------------------------------------------------------------------
    # Redis (caching, rate limiting, celery broker)
    # ------------------------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = None
    CACHE_TTL_SECONDS: int = 300

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------
    RATE_LIMIT_PER_MINUTE: int = 120

    # ------------------------------------------------------------------
    # Azure
    # ------------------------------------------------------------------
    AZURE_KEY_VAULT_URL: str | None = None
    AZURE_STORAGE_ACCOUNT_URL: str | None = None
    AZURE_STORAGE_CONTAINER_MODELS: str = "ml-models"
    AZURE_STORAGE_CONTAINER_DATASETS: str = "datasets"
    AZURE_APPLICATIONINSIGHTS_CONNECTION_STRING: str | None = None
    USE_AZURE_KEY_VAULT: bool = False

    # ------------------------------------------------------------------
    # ML
    # ------------------------------------------------------------------
    ML_ARTIFACTS_LOCAL_PATH: str = "../ml/artifacts"
    MODEL_REGISTRY_BACKEND: Literal["local", "azure_blob"] = "local"

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------
    DEFAULT_PAGE_SIZE: int = 25
    MAX_PAGE_SIZE: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
