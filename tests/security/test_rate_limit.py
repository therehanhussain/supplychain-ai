"""Security tests verifying tiered request rate limiting."""
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.middleware.rate_limit import limiter


@pytest.mark.asyncio
async def test_rate_limiting_enforcement(client: TestClient):
    """Verify that exceeding rate limit triggers 429 Too Many Requests."""
    await limiter.reset()

    # Configure a very tight limit for testing
    original_limit = settings.RATE_LIMIT_UNAUTHENTICATED
    settings.RATE_LIMIT_UNAUTHENTICATED = 3

    try:
        # First 3 requests succeed
        for _ in range(3):
            res = client.get("/api/v1/forecast")
            assert res.status_code == 200

        # 4th request exceeds rate limit
        res_blocked = client.get("/api/v1/forecast")
        assert res_blocked.status_code == 429
        assert res_blocked.json()["error_code"] == "RATE_LIMIT_EXCEEDED"
        assert "Retry-After" in res_blocked.headers

        # Exempt probe (/health) should still succeed
        res_exempt = client.get("/health")
        assert res_exempt.status_code == 200
    finally:
        # Restore configuration and reset state
        settings.RATE_LIMIT_UNAUTHENTICATED = original_limit
        await limiter.reset()
