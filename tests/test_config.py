"""Test Configuration and Environment Loading."""

from backend.app.core.config import Settings


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
