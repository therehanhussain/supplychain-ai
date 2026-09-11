"""Integration tests verifying standardized API collection pagination."""
import pytest
from fastapi.testclient import TestClient


def test_suppliers_pagination_with_page_and_size(client: TestClient):
    """Verify suppliers collection supports page, page_size, and returns pagination headers."""
    # Register tenant
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "pagination_test@corp.com",
            "password": "PasswordPage2026!",
            "full_name": "Page Tester",
            "organization_name": "Pagination Testing Org",
        },
    )
    assert res.status_code == 201
    headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

    # Create 5 suppliers
    for i in range(1, 6):
        client.post(
            "/api/v1/suppliers",
            headers=headers,
            json={
                "name": f"Pagination Supplier {i}",
                "country": "Germany",
                "tier": 1,
                "rating": 4.5,
            },
        )

    # Page 1, size 2
    res_p1 = client.get("/api/v1/suppliers?page=1&page_size=2", headers=headers)
    assert res_p1.status_code == 200
    assert len(res_p1.json()) == 2
    assert res_p1.headers.get("X-Page") == "1"
    assert res_p1.headers.get("X-Page-Size") == "2"

    # Page 2, size 2
    res_p2 = client.get("/api/v1/suppliers?page=2&page_size=2", headers=headers)
    assert res_p2.status_code == 200
    assert len(res_p2.json()) == 2
    assert res_p2.headers.get("X-Page") == "2"

    # Ensure items on page 1 and page 2 are distinct
    p1_ids = {s["id"] for s in res_p1.json()}
    p2_ids = {s["id"] for s in res_p2.json()}
    assert p1_ids.isdisjoint(p2_ids)

    # Verify legacy skip/limit still works
    res_legacy = client.get("/api/v1/suppliers?skip=0&limit=3", headers=headers)
    assert res_legacy.status_code == 200
    assert len(res_legacy.json()) == 3
