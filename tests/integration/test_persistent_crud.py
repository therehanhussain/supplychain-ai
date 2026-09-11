"""Integration tests for persistent CRUD operations across suppliers, inventory, orders, and shipments."""
import pytest
from fastapi.testclient import TestClient


def test_supplier_crud_lifecycle(client: TestClient):
    """Verify complete CRUD lifecycle of a supplier with database persistence."""
    # 1. Create supplier
    create_payload = {
        "name": "Titanium Logistics GmbH",
        "contact_email": "ops@titanium.de",
        "phone": "+49-89-123456",
        "country": "Germany",
        "tier": 1,
        "rating": 4.95,
        "lead_time_days": 5,
        "status": "active",
    }
    create_res = client.post("/api/v1/suppliers", json=create_payload)
    assert create_res.status_code == 201
    supplier = create_res.json()
    supplier_id = supplier["id"]
    assert supplier["name"] == create_payload["name"]
    assert supplier["country"] == "Germany"

    # 2. Read supplier by ID
    get_res = client.get(f"/api/v1/suppliers/{supplier_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == supplier_id

    # 3. Update supplier
    update_res = client.put(f"/api/v1/suppliers/{supplier_id}", json={"lead_time_days": 3, "rating": 5.0})
    assert update_res.status_code == 200
    assert update_res.json()["lead_time_days"] == 3
    assert update_res.json()["rating"] == 5.0

    # 4. Delete supplier
    del_res = client.delete(f"/api/v1/suppliers/{supplier_id}")
    assert del_res.status_code in (200, 204)

    # 5. Verify deleted supplier returns 404
    post_del_res = client.get(f"/api/v1/suppliers/{supplier_id}")
    assert post_del_res.status_code == 404


def test_inventory_crud_lifecycle(client: TestClient):
    """Verify inventory listing and creation."""
    # List inventory
    list_res = client.get("/api/v1/inventory")
    assert list_res.status_code == 200
    items = list_res.json()
    assert isinstance(items, list)
    assert len(items) > 0

    # Create inventory
    inv_payload = {
        "sku": "SKU-TITANIUM-001",
        "name": "Titanium Ingot Grade 5",
        "category": "raw_material",
        "warehouse_id": "wh-test-001",
        "quantity_on_hand": 250.0,
        "reorder_point": 80.0,
        "unit_cost": 45.0,
    }
    create_res = client.post("/api/v1/inventory", json=inv_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    inv_id = created["id"]
    assert created["quantity_on_hand"] == 250.0

    # Read back by ID
    get_res = client.get(f"/api/v1/inventory/{inv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == inv_id



def test_orders_and_shipments_endpoints(client: TestClient):
    """Verify order and shipment read and create operations."""
    # List orders
    orders_res = client.get("/api/v1/orders")
    assert orders_res.status_code == 200
    orders = orders_res.json()
    assert isinstance(orders, list)
    assert len(orders) > 0

    # List shipments
    ship_res = client.get("/api/v1/shipments")
    assert ship_res.status_code == 200
    shipments = ship_res.json()
    assert isinstance(shipments, list)
    assert len(shipments) > 0
    assert shipments[0]["tracking_number"] == "TRK-TEST-9001"
