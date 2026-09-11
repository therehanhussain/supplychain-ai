"""Security tests verifying OWASP-recommended HTTP security headers."""
from fastapi.testclient import TestClient


def test_security_headers_present_on_responses(client: TestClient):
    """Verify standard security headers are injected on all HTTP responses."""
    response = client.get("/health")
    assert response.status_code == 200

    # 1. MIME sniffing protection
    assert response.headers.get("X-Content-Type-Options") == "nosniff"

    # 2. Clickjacking protection
    assert response.headers.get("X-Frame-Options") == "DENY"

    # 3. Cross-site scripting protection
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"

    # 4. Strict Referrer Policy
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    # 5. Permissions Policy
    assert "geolocation=()" in response.headers.get("Permissions-Policy", "")


def test_correlation_and_timing_headers_present(client: TestClient):
    """Verify operational tracing headers (X-Request-ID, X-Process-Time) are present."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers
