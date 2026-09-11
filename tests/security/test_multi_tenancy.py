"""Security tests verifying strict organization-based multi-tenant data isolation."""
import pytest
from fastapi.testclient import TestClient


def test_cross_tenant_data_isolation(client: TestClient):
    """Verify that Tenant A's data is completely invisible and immutable to Tenant B."""
    # 1. Register Tenant A
    res_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@tenant-alpha.com",
            "password": "PasswordAlpha2026!",
            "full_name": "Alpha Owner",
            "organization_name": "Tenant Alpha Inc",
        },
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Tenant B
    res_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@tenant-beta.com",
            "password": "PasswordBeta2026!",
            "full_name": "Beta Owner",
            "organization_name": "Tenant Beta Corp",
        },
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Tenant A creates a private supplier
    create_res = client.post(
        "/api/v1/suppliers",
        headers=headers_a,
        json={
            "name": "Alpha Secret High-Yield Foundry",
            "contact_email": "alpha.foundry@secret.com",
            "country": "Taiwan",
            "tier": 1,
            "rating": 4.99,
        },
    )
    assert create_res.status_code == 201
    alpha_supplier_id = create_res.json()["id"]

    # 4. Tenant B lists suppliers - must NOT include Tenant A's supplier
    list_b = client.get("/api/v1/suppliers", headers=headers_b)
    assert list_b.status_code == 200
    b_supplier_ids = [s["id"] for s in list_b.json()]
    assert alpha_supplier_id not in b_supplier_ids

    # 5. Tenant B attempts direct read of Tenant A's supplier by ID - must return 404 (not found in tenant scope)
    read_b = client.get(f"/api/v1/suppliers/{alpha_supplier_id}", headers=headers_b)
    assert read_b.status_code == 404

    # 6. Tenant B attempts unauthorized update of Tenant A's supplier - must return 404
    update_b = client.put(
        f"/api/v1/suppliers/{alpha_supplier_id}",
        headers=headers_b,
        json={"name": "Hacked Supplier Name"},
    )
    assert update_b.status_code == 404

    # 7. Tenant B attempts unauthorized deletion of Tenant A's supplier - must return 404
    delete_b = client.delete(f"/api/v1/suppliers/{alpha_supplier_id}", headers=headers_b)
    assert delete_b.status_code == 404

    # 8. Verify Tenant A's supplier is unchanged
    verify_a = client.get(f"/api/v1/suppliers/{alpha_supplier_id}", headers=headers_a)
    assert verify_a.status_code == 200
    assert verify_a.json()["name"] == "Alpha Secret High-Yield Foundry"
