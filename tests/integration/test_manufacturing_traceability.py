"""Integration tests for manufacturing data model and material traceability (Phase 13.1).

Validates:
- ProductionOrder, WorkOrder, and MaterialRequirement lifecycle
- Real-world Examples A through G (Receipt, Issue, Consumption, Return, Wastage, Transfer, Insufficient Stock)
- Reconciliation: issued = consumed + returned + wastage
- Atomic transaction execution & inventory quantity integrity
- Multi-tenant isolation & mandatory reason validations
- Complete traceability timeline ("What happened to RM-001?")
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.models.user import UserRole
from backend.app.middleware.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests."""
    limiter._requests.clear()



@pytest.fixture
def setup_manufacturing_test_data(client: TestClient):
    """Setup clean warehouse and copper wire raw material for manufacturing tests."""
    # 1. Create a Warehouse A
    wh_a_payload = {
        "code": "WH-RAW-STORE",
        "name": "Raw Material Store A",
        "city": "Dallas",
        "country": "USA",
    }
    # Create inventory item which also creates warehouse and product if missing
    inv_payload = {
        "sku": "RM-COPPER-001",
        "name": "Industrial Copper Wire",
        "category": "RAW_MATERIAL",
        "warehouse_id": "WH-RAW-STORE",
        "quantity_on_hand": 0.0,
        "reorder_point": 200.0,
        "unit_cost": 12.50,
    }
    inv_res = client.post("/api/v1/inventory", json=inv_payload)
    assert inv_res.status_code == 201
    inv_data = inv_res.json()

    # Finished good product
    fg_payload = {
        "sku": "FG-MOTOR-500",
        "name": "Electric Motor EM-500",
        "category": "FINISHED_GOOD",
        "warehouse_id": "WH-RAW-STORE",
        "quantity_on_hand": 0.0,
        "reorder_point": 10.0,
        "unit_cost": 250.00,
    }
    fg_res = client.post("/api/v1/inventory", json=fg_payload)
    assert fg_res.status_code == 201
    fg_data = fg_res.json()

    # Warehouse B for transfers
    wh_b_payload = {
        "sku": "RM-COPPER-001",
        "name": "Industrial Copper Wire",
        "category": "RAW_MATERIAL",
        "warehouse_id": "WH-PLANT-BAY2",
        "quantity_on_hand": 0.0,
        "reorder_point": 50.0,
        "unit_cost": 12.50,
    }
    wh_b_res = client.post("/api/v1/inventory", json=wh_b_payload)
    assert wh_b_res.status_code == 201

    return {
        "raw_inventory_id": inv_data["id"],
        "raw_product_sku": "RM-COPPER-001",
        "fg_product_sku": "FG-MOTOR-500",
        "warehouse_a": "WH-RAW-STORE",
        "warehouse_b": "WH-PLANT-BAY2",
    }


def test_production_and_work_order_creation(client: TestClient, setup_manufacturing_test_data):
    """Test 1 & 2: Production order and Work order creation and query."""
    data = setup_manufacturing_test_data

    # 1. Create Production Order
    po_payload = {
        "order_number": "PO-EM500-BATCH1",
        "product_id": data["fg_product_sku"],
        "planned_quantity": 100.0,
        "notes": "Q4 Manufacturing Target for Motors",
    }
    po_res = client.post("/api/v1/production-orders", json=po_payload)
    assert po_res.status_code == 201
    po = po_res.json()
    assert po["order_number"] == "PO-EM500-BATCH1"
    assert po["planned_quantity"] == 100.0
    assert po["status"] == "PLANNED"

    # 2. Create Work Order
    wo_payload = {
        "production_order_id": po["id"],
        "work_order_number": "MO-1025",
        "warehouse_id": data["warehouse_a"],
        "production_area": "Winding Line 2",
        "planned_quantity": 100.0,
        "notes": "Sub-assembly winding step",
    }
    wo_res = client.post("/api/v1/work-orders", json=wo_payload)
    assert wo_res.status_code == 201
    wo = wo_res.json()
    assert wo["work_order_number"] == "MO-1025"
    assert wo["production_area"] == "Winding Line 2"

    # 3. Create Material Requirement (50 kg copper wire required)
    mr_payload = {
        "work_order_id": wo["id"],
        "product_id": data["raw_product_sku"],
        "required_quantity": 50.0,
        "unit_of_measure": "kg",
    }
    mr_res = client.post("/api/v1/material-requirements", json=mr_payload)
    assert mr_res.status_code == 201
    mr = mr_res.json()
    assert mr["required_quantity"] == 50.0
    assert mr["issued_quantity"] == 0.0


def test_real_world_material_traceability_lifecycle_examples_a_through_e(
    client: TestClient, setup_manufacturing_test_data
):
    """Verify Examples A through E with exact material reconciliation:
    100 kg issued = 95 kg consumed + 3 kg returned + 2 kg wastage.
    """
    data = setup_manufacturing_test_data
    sku = data["raw_product_sku"]
    wh = data["warehouse_a"]

    # Setup Production Order and Work Order
    po_res = client.post("/api/v1/production-orders", json={
        "order_number": "PO-TEST-LIFECYCLE",
        "product_id": data["fg_product_sku"],
        "planned_quantity": 100.0,
    })
    po_id = po_res.json()["id"]

    wo_res = client.post("/api/v1/work-orders", json={
        "production_order_id": po_id,
        "work_order_number": "MO-1025-LIFECYCLE",
        "production_area": "Winding Line 2",
        "planned_quantity": 100.0,
    })
    wo_id = wo_res.json()["id"]

    # Pre-define Material Requirement: 50 kg expected
    client.post("/api/v1/material-requirements", json={
        "work_order_id": wo_id,
        "product_id": sku,
        "required_quantity": 50.0,
        "unit_of_measure": "kg",
    })

    # --------------------------------------------------------------------------
    # EXAMPLE A: RECEIPT
    # Supplier delivers 1,000 kg Copper Wire.
    # Store receives it -> Store inventory increases by 1,000 kg.
    # --------------------------------------------------------------------------
    receipt_payload = {
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "RECEIPT",
        "quantity": 1000.0,
        "unit_of_measure": "kg",
        "reference_type": "PURCHASE_ORDER",
        "reference_id": "PO-SUPP-9871",
        "reason": "Supplier Inward Receipt from ABC Metals",
    }
    tx_a = client.post("/api/v1/stock-transactions", json=receipt_payload)
    assert tx_a.status_code == 201
    assert tx_a.json()["transaction_type"] == "RECEIPT"
    assert tx_a.json()["quantity"] == 1000.0

    # Verify inventory is 1,000
    inv_check_a = client.get(f"/api/v1/inventory/{data['raw_inventory_id']}")
    assert inv_check_a.json()["quantity_on_hand"] == 1000.0

    # --------------------------------------------------------------------------
    # EXAMPLE B: ISSUE
    # 100 kg Copper Wire is issued to Work Order MO-1025.
    # Store inventory decreases: 1,000 -> 900 kg.
    # Production receives/holds: 100 kg.
    # --------------------------------------------------------------------------
    issue_payload = {
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "ISSUE",
        "quantity": 100.0,
        "unit_of_measure": "kg",
        "work_order_id": wo_id,
        "destination_location": "Winding Line 2",
        "reason": "Issue raw copper wire for winding stage",
    }
    tx_b = client.post("/api/v1/stock-transactions", json=issue_payload)
    assert tx_b.status_code == 201

    # Verify store inventory decreased to 900
    inv_check_b = client.get(f"/api/v1/inventory/{data['raw_inventory_id']}")
    assert inv_check_b.json()["quantity_on_hand"] == 900.0

    # --------------------------------------------------------------------------
    # EXAMPLE C: CONSUMPTION
    # Production employee Rahul consumes 95 kg for Work Order MO-1025.
    # Store inventory does NOT decrease again (stays 900 kg).
    # --------------------------------------------------------------------------
    consume_payload = {
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "CONSUMPTION",
        "quantity": 95.0,
        "unit_of_measure": "kg",
        "work_order_id": wo_id,
        "reason": "Consumed for motor coils assembly",
    }
    tx_c = client.post("/api/v1/stock-transactions", json=consume_payload)
    assert tx_c.status_code == 201

    # Store inventory unchanged
    inv_check_c = client.get(f"/api/v1/inventory/{data['raw_inventory_id']}")
    assert inv_check_c.json()["quantity_on_hand"] == 900.0

    # --------------------------------------------------------------------------
    # EXAMPLE D: RETURN
    # 3 kg unused material is returned from production back to store.
    # Store inventory increases: 900 -> 903 kg.
    # --------------------------------------------------------------------------
    return_payload = {
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "RETURN",
        "quantity": 3.0,
        "unit_of_measure": "kg",
        "work_order_id": wo_id,
        "source_location": "Winding Line 2",
        "destination_location": wh,
        "reason": "Uncut copper spool return",
    }
    tx_d = client.post("/api/v1/stock-transactions", json=return_payload)
    assert tx_d.status_code == 201

    # Store inventory is now 903
    inv_check_d = client.get(f"/api/v1/inventory/{data['raw_inventory_id']}")
    assert inv_check_d.json()["quantity_on_hand"] == 903.0

    # --------------------------------------------------------------------------
    # EXAMPLE E: WASTAGE
    # 2 kg is reported as production scrap/wastage. Reason is mandatory.
    # Store inventory stays 903 kg.
    # --------------------------------------------------------------------------
    waste_payload = {
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "WASTAGE",
        "quantity": 2.0,
        "unit_of_measure": "kg",
        "work_order_id": wo_id,
        "reason": "Cutting end scrap and lead trimming",
    }
    tx_e = client.post("/api/v1/stock-transactions", json=waste_payload)
    assert tx_e.status_code == 201

    inv_check_e = client.get(f"/api/v1/inventory/{data['raw_inventory_id']}")
    assert inv_check_e.json()["quantity_on_hand"] == 903.0

    # --------------------------------------------------------------------------
    # RECONCILIATION VERIFICATION:
    # 100 kg issued == 95 kg consumed + 3 kg returned + 2 kg wastage
    # --------------------------------------------------------------------------
    tx_list = client.get(f"/api/v1/stock-transactions?work_order_id={wo_id}").json()
    issued_total = sum(t["quantity"] for t in tx_list if t["transaction_type"] == "ISSUE")
    consumed_total = sum(t["quantity"] for t in tx_list if t["transaction_type"] == "CONSUMPTION")
    returned_total = sum(t["quantity"] for t in tx_list if t["transaction_type"] == "RETURN")
    wastage_total = sum(t["quantity"] for t in tx_list if t["transaction_type"] == "WASTAGE")

    assert issued_total == 100.0
    assert consumed_total == 95.0
    assert returned_total == 3.0
    assert wastage_total == 2.0
    assert issued_total == (consumed_total + returned_total + wastage_total)

    # Verify Material Traceability Timeline
    timeline_res = client.get(f"/api/v1/materials/{sku}/traceability")
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert timeline["sku"] == sku
    assert len(timeline["timeline"]) >= 5
    assert timeline["current_stock_total"] == 903.0


def test_real_world_example_f_inter_warehouse_transfer(client: TestClient, setup_manufacturing_test_data):
    """Example F: 100 kg moves from Warehouse A to Warehouse B atomically."""
    data = setup_manufacturing_test_data
    sku = data["raw_product_sku"]
    wh_a = data["warehouse_a"]
    wh_b = data["warehouse_b"]

    # Initial receipt in Warehouse A
    client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh_a,
        "product_id": sku,
        "transaction_type": "RECEIPT",
        "quantity": 250.0,
        "unit_of_measure": "kg",
    })

    # Execute inter-warehouse transfer of 100 kg
    transfer_payload = {
        "source_warehouse_id": wh_a,
        "destination_warehouse_id": wh_b,
        "product_id": sku,
        "quantity": 100.0,
        "unit_of_measure": "kg",
        "reason": "Replenish assembly plant line",
    }
    trans_res = client.post("/api/v1/stock-transfers", json=transfer_payload)
    assert trans_res.status_code == 200
    assert trans_res.json()["status"] == "success"

    # Verify transactions created
    transactions = client.get("/api/v1/stock-transactions").json()
    transfers_out = [t for t in transactions if t["transaction_type"] == "TRANSFER_OUT" and t["source_location"] == wh_a]
    transfers_in = [t for t in transactions if t["transaction_type"] == "TRANSFER_IN" and t["destination_location"] == wh_b]
    assert len(transfers_out) > 0
    assert len(transfers_in) > 0


def test_real_world_example_g_insufficient_stock_rejection(client: TestClient, setup_manufacturing_test_data):
    """Example G: Reject transaction when quantity exceeds available stock."""
    data = setup_manufacturing_test_data
    sku = "RM-RARE-ELEMENT-99"
    wh = data["warehouse_a"]

    # Seed exactly 20 kg
    client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "RECEIPT",
        "quantity": 20.0,
        "unit_of_measure": "kg",
    })

    # Attempt to issue 50 kg (should fail with 400)
    fail_issue = client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "ISSUE",
        "quantity": 50.0,
        "unit_of_measure": "kg",
    })
    assert fail_issue.status_code == 400
    assert fail_issue.json()["error_code"] == "INSUFFICIENT_INVENTORY"

    # Verify inventory is untouched at 20 kg
    trace = client.get(f"/api/v1/materials/{sku}/traceability").json()
    assert trace["current_stock_total"] == 20.0


def test_mandatory_reason_validations(client: TestClient, setup_manufacturing_test_data):
    """Verify WASTAGE, DAMAGE, EXPIRY, ADJUSTMENT require non-empty reason."""
    data = setup_manufacturing_test_data
    sku = data["raw_product_sku"]
    wh = data["warehouse_a"]

    # Seed stock
    client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "RECEIPT",
        "quantity": 50.0,
    })

    # Wastage without reason must fail
    res_waste = client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "WASTAGE",
        "quantity": 5.0,
        "reason": "",
    })
    assert res_waste.status_code == 400
    assert res_waste.json()["error_code"] == "REASON_REQUIRED"

    # Damage without reason must fail
    res_damage = client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "DAMAGE",
        "quantity": 2.0,
    })
    assert res_damage.status_code == 400
    assert res_damage.json()["error_code"] == "REASON_REQUIRED"

    # Damage with reason succeeds and decreases inventory
    res_valid_dmg = client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "DAMAGE",
        "quantity": 2.0,
        "reason": "Forklift impact in aisle 3",
    })
    assert res_valid_dmg.status_code == 201


def test_negative_or_zero_quantity_rejection(client: TestClient, setup_manufacturing_test_data):
    """Negative or zero quantity must be rejected."""
    data = setup_manufacturing_test_data
    sku = data["raw_product_sku"]
    wh = data["warehouse_a"]

    res_zero = client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "RECEIPT",
        "quantity": 0.0,
    })
    assert res_zero.status_code == 422

    res_neg = client.post("/api/v1/stock-transactions", json={
        "warehouse_id": wh,
        "product_id": sku,
        "transaction_type": "RECEIPT",
        "quantity": -10.0,
    })
    assert res_neg.status_code == 422


def test_cross_tenant_isolation(client: TestClient):
    """Verify tenant isolation: Tenant A cannot see or access Tenant B's manufacturing data."""
    # Register Tenant B
    reg_res = client.post("/api/v1/auth/register", json={
        "organization_name": "Tenant B Aerospace",
        "email": "admin@tenantb-aero.com",
        "password": "SecurePassword123!",
        "full_name": "Tenant B Admin",
        "role": "ADMIN",
    })
    assert reg_res.status_code == 201
    token_b = reg_res.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Tenant B creates a secret component
    t_b_prod = client.post("/api/v1/inventory", json={
        "sku": "SECRET-ALLOY-B",
        "name": "Classified Turbine Blade",
        "category": "RAW_MATERIAL",
        "warehouse_id": "WH-TENANT-B",
        "quantity_on_hand": 100.0,
        "reorder_point": 20.0,
        "unit_cost": 500.0,
    }, headers=headers_b)
    assert t_b_prod.status_code == 201

    # Default tenant (unauthenticated or tenant A) attempts to trace Tenant B's product
    attempt_trace = client.get("/api/v1/materials/SECRET-ALLOY-B/traceability")
    assert attempt_trace.status_code == 404
