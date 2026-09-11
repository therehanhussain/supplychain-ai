"""Centralized Application Configuration.

Loads configuration from environment variables and optional .env file
using Pydantic BaseSettings.
"""

from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Production Settings schema for SupplyChainAgent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General App Settings
    APP_NAME: str = "SupplyChainAgent"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", description="development, staging, production")
    DEBUG: bool = Field(default=False)
    PORT: int = Field(default=8000)
    LOG_LEVEL: str = Field(default="INFO")

    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed origins for CORS (comma-separated or list)",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(i).strip() for i in v if str(i).strip()]
        return ["http://localhost:5173", "http://localhost:3000"]

    # PostgreSQL Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/supplychain",
        description="SQLAlchemy async connection string",
    )

    # Redis Cache & Queue
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for cache and Celery broker",
    )

    # Neo4j Graph Database
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USERNAME: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="")
    NEO4J_DATABASE: str = Field(default="neo4j")

    # Centralized LLM Gateway
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4o-mini")

    # Security & JWT Tokens
    JWT_SECRET: str = Field(default="development_fallback_secret_must_override_in_production_32chars")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    # Asynchronous Workers
    CELERY_WORKER_CONCURRENCY: int = Field(default=2)

    # MLflow Tracking Server (Optional)
    MLFLOW_TRACKING_URI: str = Field(default="http://localhost:59000")


# Global cached settings instance
settings = Settings()
