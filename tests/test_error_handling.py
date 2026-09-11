"""Test Unified Error Handling and Exception Concealment."""

from fastapi.testclient import TestClient


def test_404_not_found_structured_response(client: TestClient):
    """Verify 404 response returns structured JSON with error code and request ID."""
    response = client.get("/api/v1/non-existent-endpoint-xyz")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == 404
    assert "code" in data
    assert "message" in data
    assert "request_id" in data
    assert "X-Request-ID" in response.headers


def test_validation_error_structured_response(client: TestClient):
    """Verify 422 validation failure produces clean structured details."""
    # Posting invalid data type for horizon_days (should be integer, sending string "invalid")
    response = client.post("/api/v1/forecast", json={"product_id": "prod_1", "horizon_days": "not_a_number"})
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == 422
    assert data["code"] == "VALIDATION_ERROR"
    assert "request_id" in data
    assert "details" in data
