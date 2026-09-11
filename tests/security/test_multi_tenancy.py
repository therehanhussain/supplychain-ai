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


def test_cross_tenant_inventory_and_orders_isolation(client: TestClient):
    """Verify Tenant B cannot read or delete Tenant A's inventory, orders, or shipments."""
    # 1. Register Tenant A
    res_a = client.post(
        "/api/v1/auth/register",
        json={
            "email": "corp_a_lead@tenanta.com",
            "password": "PasswordTenA2026!",
            "full_name": "Tenant A Admin",
            "organization_name": "Tenant A Logistics",
        },
    )
    assert res_a.status_code == 201
    headers_a = {"Authorization": f"Bearer {res_a.json()['access_token']}"}

    # 2. Register Tenant B
    res_b = client.post(
        "/api/v1/auth/register",
        json={
            "email": "corp_b_lead@tenantb.com",
            "password": "PasswordTenB2026!",
            "full_name": "Tenant B Admin",
            "organization_name": "Tenant B Logistics",
        },
    )
    assert res_b.status_code == 201
    headers_b = {"Authorization": f"Bearer {res_b.json()['access_token']}"}

    # 3. Tenant A creates inventory item
    inv_res = client.post(
        "/api/v1/inventory",
        headers=headers_a,
        json={
            "sku": "MAT-ALPHA-WAFER-01",
            "name": "Alpha Silicon Wafer Grade 9",
            "warehouse_id": "wh-alpha-001",
            "quantity_on_hand": 5000.0,
            "quantity_reserved": 200.0,
            "reorder_point": 1000.0,
            "unit_cost": 45.0,
        },
    )
    assert inv_res.status_code == 201
    alpha_inv_id = inv_res.json()["id"]

    # 4. Tenant B cannot see Tenant A's inventory item
    list_inv_b = client.get("/api/v1/inventory", headers=headers_b)
    assert list_inv_b.status_code == 200
    assert all(item["id"] != alpha_inv_id for item in list_inv_b.json())

    # 5. Tenant B cannot get or delete Tenant A's inventory item
    assert client.get(f"/api/v1/inventory/{alpha_inv_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/api/v1/inventory/{alpha_inv_id}", headers=headers_b).status_code == 404

    # 6. Tenant A creates an order
    order_res = client.post(
        "/api/v1/orders",
        headers=headers_a,
        json={
            "customer_name": "Alpha Defense Logistics",
            "supplier_id": "supp-dummy-alpha",
            "status": "pending",
            "total_amount": 75000.0,
            "items": [
                {
                    "product_id": "prod-001",
                    "product_name": "Silicon Ingot",
                    "quantity": 100.0,
                    "unit_price": 750.0,
                }
            ],
        },
    )
    assert order_res.status_code == 201
    alpha_order_id = order_res.json()["id"]

    # 7. Tenant B cannot get or delete Tenant A's order
    assert client.get(f"/api/v1/orders/{alpha_order_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/api/v1/orders/{alpha_order_id}", headers=headers_b).status_code == 404

    # 8. Tenant A creates a shipment
    ship_res = client.post(
        "/api/v1/shipments",
        headers=headers_a,
        json={
            "order_id": alpha_order_id,
            "carrier": "DHL Global Forwarding",
            "tracking_number": "TRK-ALPHA-001",
            "origin": "Hamburg Port",
            "destination": "Munich Distribution Hub",
            "status": "in_transit",
        },
    )
    assert ship_res.status_code == 201
    alpha_shipment_id = ship_res.json()["id"]

    # 9. Tenant B cannot get or delete Tenant A's shipment
    assert client.get(f"/api/v1/shipments/{alpha_shipment_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/api/v1/shipments/{alpha_shipment_id}", headers=headers_b).status_code == 404

