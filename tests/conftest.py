"""Pytest Fixtures and Global Test Configuration."""

import os
import pytest
from fastapi.testclient import TestClient

# Enforce testing environment variables prior to importing application modules
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "false"
os.environ["JWT_SECRET"] = "testing_secret_key_with_at_least_32_chars"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"
os.environ["OPENAI_API_KEY"] = ""

from backend.app.main import app
from backend.app.core.config import settings


@pytest.fixture(scope="session")
def client():
    """Shared FastAPI test client instance."""
    with TestClient(app) as test_client:
        yield test_client
