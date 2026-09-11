"""Security tests for authentication edge cases, token integrity, and account deactivation."""
import pytest
from fastapi.testclient import TestClient
from backend.app.models.user import UserRole


@pytest.mark.asyncio
async def test_inactive_user_token_rejected_with_403(client: TestClient, create_test_user, auth_header_for_user, db_session_factory):
    """Verify deactivated user account cannot access authenticated endpoints."""
    user = await create_test_user("inactive@test.corp", role=UserRole.VIEWER)
    headers = auth_header_for_user(user)

    # Deactivate the user in database
    async with db_session_factory() as session:
        from backend.app.repositories.users import UserRepository
        repo = UserRepository(session)
        user_db = await repo.get_by_id(user.id)
        await repo.update(user_db, {"is_active": False})

    # Attempt access with existing token
    res = client.get("/api/v1/auth/me", headers=headers)
    assert res.status_code == 403
    assert res.json()["error_code"] == "ACCOUNT_INACTIVE"


def test_malformed_auth_headers_fail(client: TestClient):
    """Verify various malformed Authorization headers fail safely with 401."""
    # Garbage token
    res1 = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.jwt.payload"})
    assert res1.status_code == 401

    # Missing Bearer prefix
    res2 = client.get("/api/v1/auth/me", headers={"Authorization": "Token eyJhbGciOiJIUzI1NiJ9..."})
    assert res2.status_code == 401

    # Empty Bearer
    res3 = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer "})
    assert res3.status_code == 401
