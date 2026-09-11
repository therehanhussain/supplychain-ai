"""Test System Health, Liveness, and Readiness Endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient):
    """Verify /health returns 200 OK and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app" in data
    assert "version" in data
    assert "timestamp" in data
    # Ensure correlation and latency headers are injected
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers


def test_liveness_endpoint(client: TestClient):
    """Verify /live Kubernetes liveness probe returns 200."""
    response = client.get("/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


def test_health_live_endpoint(client: TestClient):
    """Verify /health/live Render and container liveness probe alias returns 200."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"


def test_readiness_endpoint(client: TestClient):
    """Verify /ready Kubernetes readiness probe returns 200 with dependency checks."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "dependencies" in data
    assert "database" in data["dependencies"]
    assert "postgres" in data["dependencies"]
    assert "neo4j" in data["dependencies"]
    assert "redis" in data["dependencies"]
    assert "celery" in data["dependencies"]
    assert "llm" in data["dependencies"]


def test_api_v1_health_alias(client: TestClient):
    """Verify versioned /api/v1/health is accessible."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
