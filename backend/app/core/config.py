"""Centralized Application Configuration.

Loads configuration from environment variables and optional .env file
using Pydantic BaseSettings.
"""

from typing import List, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_FALLBACK_JWT_SECRET = "development_fallback_secret_must_override_in_production_32chars"


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
        default=["http://localhost:5173", "http://localhost:3000", "https://frontend-pi-hazel-83.vercel.app"],
        description="Allowed origins for CORS (comma-separated or list)",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(i).strip() for i in v if str(i).strip()]
        return ["http://localhost:5173", "http://localhost:3000", "https://frontend-pi-hazel-83.vercel.app"]

    # PostgreSQL Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/supplychain",
        description="SQLAlchemy async connection string",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if not v:
            return v
        # Normalize Render/cloud providers supplying postgres:// or postgresql:// to asyncpg
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        if v.startswith("postgresql://") and not v.startswith("postgresql+"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

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
    LLM_MODE: str = Field(default="mock", description="'live' or 'mock'")
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    DEEPSEEK_API_KEY: str = Field(default="")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com/v1")
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4o-mini")

    # Security & JWT Tokens
    JWT_SECRET: str = Field(default="development_fallback_secret_must_override_in_production_32chars")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # Asynchronous Workers
    CELERY_WORKER_CONCURRENCY: int = Field(default=2)

    # MLflow Tracking Server (Optional)
    MLFLOW_TRACKING_URI: str = Field(default="http://localhost:59000")

    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_UNAUTHENTICATED: int = Field(default=30, description="Max requests per minute for unauthenticated clients")
    RATE_LIMIT_AUTHENTICATED: int = Field(default=120, description="Max requests per minute for authenticated clients")
    RATE_LIMIT_SIMULATION: int = Field(default=10, description="Max requests per minute for simulation/AI dispatch")

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Strictly prevent insecure fallback keys from running in production environment."""
        if self.ENVIRONMENT.lower() == "production":
            if self.JWT_SECRET == DEV_FALLBACK_JWT_SECRET or not self.JWT_SECRET or len(self.JWT_SECRET) < 32:
                raise ValueError(
                    "Production deployment security violation: In 'production' environment, "
                    "JWT_SECRET must be explicitly provided via environment variables with a "
                    "cryptographically secure key of at least 32 characters."
                )
        return self


# Global cached settings instance
settings = Settings()

