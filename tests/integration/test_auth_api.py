"""Integration tests for Authentication API endpoints (/api/v1/auth/*)."""
import pytest
from fastapi.testclient import TestClient


def test_register_new_tenant_and_user(client: TestClient):
    """Verify registration creates new organization and admin user with JWT tokens."""
    payload = {
        "email": "new_director@logitech-supply.corp",
        "password": "SecurePassword2026!",
        "full_name": "Logitech Director",
        "organization_name": "Logitech Supply Corp",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["role"] in ("ADMIN", "admin")
    assert data["user"]["organization_id"] is not None


def test_register_duplicate_email_fails(client: TestClient):
    """Verify attempting to register with existing email returns 409 conflict."""
    payload = {
        "email": "duplicate@logitech-supply.corp",
        "password": "SecurePassword2026!",
        "full_name": "First User",
        "organization_name": "First Corp",
    }
    # First registration
    res1 = client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Duplicate registration
    res2 = client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    err = res2.json()
    assert err["error_code"] == "EMAIL_ALREADY_EXISTS"


def test_login_flow(client: TestClient):
    """Verify login with correct credentials returns tokens, and invalid credentials fail."""
    # Register user first
    email = "login_test@apex.corp"
    password = "CorrectPassword123!"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Apex Lead",
            "organization_name": "Apex Corp",
        },
    )

    # Success login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Invalid password login
    bad_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_res.status_code == 401
    assert bad_res.json()["error_code"] == "INVALID_CREDENTIALS"

    # Non-existent user login
    missing_res = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@apex.corp", "password": password},
    )
    assert missing_res.status_code == 401
    assert missing_res.json()["error_code"] == "INVALID_CREDENTIALS"


def test_token_refresh(client: TestClient):
    """Verify refresh token endpoint issues new access token."""
    email = "refresh_test@apex.corp"
    password = "CorrectPassword123!"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Refresh User",
            "organization_name": "Refresh Org",
        },
    ).json()

    refresh_token = reg["refresh_token"]

    # Exchange refresh token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_user_profile(client: TestClient):
    """Verify /api/v1/auth/me returns authenticated user data when bearer token is provided."""
    email = "me_test@apex.corp"
    password = "CorrectPassword123!"
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Current Profile User",
            "organization_name": "Profile Org",
        },
    ).json()

    access_token = reg["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_data = me_res.json()
    assert user_data["email"] == email
    assert user_data["role"] in ("ADMIN", "admin")


    # Unauthorized access check
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401
