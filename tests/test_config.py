"""Test Configuration and Environment Loading."""

import pytest
from backend.app.core.config import Settings, DEV_FALLBACK_JWT_SECRET


def test_config_defaults_and_env():
    """Verify settings loads defaults and parses environment variables correctly."""
    s = Settings(ENVIRONMENT="testing", PORT=9000, CORS_ORIGINS="http://test.com, http://example.com")
    assert s.ENVIRONMENT == "testing"
    assert s.PORT == 9000
    assert s.CORS_ORIGINS == ["http://test.com", "http://example.com"]


def test_cors_origins_list_parsing():
    """Verify comma-separated string correctly parses to Python list."""
    s = Settings(CORS_ORIGINS="http://localhost:5173, http://localhost:8000")
    assert isinstance(s.CORS_ORIGINS, list)
    assert len(s.CORS_ORIGINS) == 2
    assert "http://localhost:5173" in s.CORS_ORIGINS


def test_cors_origins_default_includes_vercel_production():
    """Verify default CORS origins authorize the deployed Vercel frontend."""
    s = Settings()
    assert "https://frontend-pi-hazel-83.vercel.app" in s.CORS_ORIGINS


def test_production_jwt_secret_validation_enforced():
    """Verify production environment blocks default fallback JWT secret."""
    with pytest.raises(ValueError, match="Production deployment security violation"):
        Settings(ENVIRONMENT="production", JWT_SECRET=DEV_FALLBACK_JWT_SECRET)


def test_production_jwt_secret_short_key_rejected():
    """Verify production environment rejects JWT secret shorter than 32 characters."""
    with pytest.raises(ValueError, match="cryptographically secure key of at least 32 characters"):
        Settings(ENVIRONMENT="production", JWT_SECRET="short_secret_key_123")


def test_production_jwt_secret_valid_key_accepted():
    """Verify production environment accepts strong 32+ char secret."""
    s = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="a_very_strong_cryptographic_production_secret_key_32_chars!",
    )
    assert s.ENVIRONMENT == "production"
    assert s.JWT_SECRET.startswith("a_very_strong")


def test_database_url_normalization_for_render():
    """Verify postgres:// and postgresql:// are normalized to postgresql+asyncpg://."""
    s1 = Settings(DATABASE_URL="postgres://user:pass@ep-cool-db.render.com/mydb")
    assert s1.DATABASE_URL == "postgresql+asyncpg://user:pass@ep-cool-db.render.com/mydb"

    s2 = Settings(DATABASE_URL="postgresql://user:pass@ep-cool-db.render.com/mydb")
    assert s2.DATABASE_URL == "postgresql+asyncpg://user:pass@ep-cool-db.render.com/mydb"

    s3 = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@host/db")
    assert s3.DATABASE_URL == "postgresql+asyncpg://user:pass@host/db"
