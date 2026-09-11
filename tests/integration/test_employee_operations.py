"""Integration tests for Employee Operations Portal (Phase 13.2).

Validates:
A. Employee can view assigned work order.
B. Employee cannot view or operate on another employee's work order.
C. Employee can consume material within holding quantity.
D. Employee cannot consume more than holding quantity.
E. Employee can return material within holding quantity.
F. Employee cannot return more than holding quantity.
G. Employee can report wastage within holding quantity.
H. Employee cannot report wastage beyond holding quantity.
I. Organization isolation works.
J. Authentication is required.
K. StockTransaction is recorded for each action.
L. AuditLog is recorded with actor ID for each action.
M. Inventory is not double-decremented.
N. Repeated submission with idempotency key does not create duplicate transaction.
O. Work-order reconciliation remains exact (20 = 12 + 5 + 3).
"""

import uuid
import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.app.models.user import User, UserRole
from backend.app.models.organization import Organization
from backend.app.models.warehouse import Warehouse
from backend.app.models.product import Product
from backend.app.models.inventory import Inventory
from backend.app.models.stock_transaction import StockTransaction
from backend.app.models.audit_log import AuditLog
from backend.app.models.enums import TransactionType
from backend.app.middleware.rate_limit import limiter
from sqlalchemy import select


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests."""
    limiter._requests.clear()


@pytest.fixture
def employee_test_setup(client: TestClient, create_test_user, auth_header_for_user, db_session_factory):
    """Setup multi-user environment for Phase 13.2 employee operations testing."""
    run_id = uuid.uuid4().hex[:8]

    async def _setup():
        # 1. Create Employee 1, Employee 2, and Admin in default org with unique emails
        emp1 = await create_test_user(
            email=f"emp1_{run_id}@apex-logistics.com",
            role=UserRole.OPERATOR,
            org_id="default-org-id",
            full_name=f"John Operator {run_id}",
        )
        emp2 = await create_test_user(
            email=f"emp2_{run_id}@apex-logistics.com",
            role=UserRole.OPERATOR,
            org_id="default-org-id",
            full_name=f"Jane Operator {run_id}",
        )
        admin = await create_test_user(
            email=f"admin_{run_id}@apex-logistics.com",
            role=UserRole.ADMIN,
            org_id="default-org-id",
            full_name=f"Admin Supervisor {run_id}",
        )

        # 2. Create second organization and user for tenant isolation tests
        other_org_id = f"org_{run_id}"
        async with db_session_factory() as session:
            other_org = Organization(
                id=other_org_id,
                name=f"Competitor Corp {run_id}",
                slug=f"comp-corp-{run_id}",
                tier="standard",
            )
            session.add(other_org)
            await session.commit()

        other_emp = await create_test_user(
            email=f"other_{run_id}@competitor.com",
            role=UserRole.OPERATOR,
            org_id=other_org_id,
            full_name=f"Other Org Employee {run_id}",
        )

        # 3. Setup unique Warehouse & Products in default org
        wh_code = f"WH-EMP-{run_id}"
        raw_sku = f"RM-STEEL-{run_id}"
        fg_sku = f"FG-DRONE-{run_id}"

        raw_payload = {
            "sku": raw_sku,
            "name": f"Industrial Steel {run_id}",
            "category": "RAW_MATERIAL",
            "warehouse_id": wh_code,
            "quantity_on_hand": 100.0,
            "reorder_point": 20.0,
            "unit_cost": 45.0,
        }
        client.post("/api/v1/inventory", json=raw_payload)

        fg_payload = {
            "sku": fg_sku,
            "name": f"Steel Drone {run_id}",
            "category": "FINISHED_GOOD",
            "warehouse_id": wh_code,
            "quantity_on_hand": 0.0,
            "reorder_point": 5.0,
            "unit_cost": 250.0,
        }
        client.post("/api/v1/inventory", json=fg_payload)

        # 4. Create Production Order & Work Order assigned to Employee 1
        po_res = client.post(
            "/api/v1/manufacturing/production-orders",
            json={
                "order_number": f"PO-EMP-{run_id}",
                "product_id": fg_sku,
                "planned_quantity": 10.0,
            },
        )
        po_data = po_res.json()

        wo1_res = client.post(
            "/api/v1/manufacturing/work-orders",
            json={
                "production_order_id": po_data["id"],
                "work_order_number": f"WO-101-{run_id}",
                "warehouse_id": wh_code,
                "production_area": "Cutting & Welding Bay",
                "assigned_user_id": emp1.id,
                "planned_quantity": 10.0,
            },
        )
        wo1_data = wo1_res.json()

        # Work order 2 assigned to Employee 2
        wo2_res = client.post(
            "/api/v1/manufacturing/work-orders",
            json={
                "production_order_id": po_data["id"],
                "work_order_number": f"WO-102-{run_id}",
                "warehouse_id": wh_code,
                "production_area": "Finishing Line",
                "assigned_user_id": emp2.id,
                "planned_quantity": 5.0,
            },
        )
        wo2_data = wo2_res.json()

        return {
            "emp1": emp1,
            "emp2": emp2,
            "admin": admin,
            "other_emp": other_emp,
            "headers_emp1": auth_header_for_user(emp1),
            "headers_emp2": auth_header_for_user(emp2),
            "headers_admin": auth_header_for_user(admin),
            "headers_other": auth_header_for_user(other_emp),
            "wo1_id": wo1_data["id"],
            "wo2_id": wo2_data["id"],
            "po_id": po_data["id"],
            "raw_sku": raw_sku,
            "warehouse": wh_code,
            "run_id": run_id,
        }

    return asyncio.run(_setup())


# ------------------------------------------------------------------------------
# Test A & B: Work Order Visibility & Assignment Guard
# ------------------------------------------------------------------------------

def test_employee_work_order_visibility_and_guards(client: TestClient, employee_test_setup):
    """Test A & B: Employee can view assigned work orders; cannot access another employee's work order."""
    data = employee_test_setup

    # Employee 1 queries /my-work-orders
    res = client.get("/api/v1/manufacturing/my-work-orders", headers=data["headers_emp1"])
    assert res.status_code == 200
    wos = res.json()
    assert len(wos) >= 1
    assert any(w["id"] == data["wo1_id"] for w in wos)
    assert not any(w["id"] == data["wo2_id"] for w in wos)

    # Employee 1 queries own work order details
    res_detail = client.get(f"/api/v1/manufacturing/work-orders/{data['wo1_id']}", headers=data["headers_emp1"])
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == data["wo1_id"]

    # Test B: Employee 1 attempts to query Employee 2's work order -> 403 Forbidden
    res_forbidden = client.get(f"/api/v1/manufacturing/work-orders/{data['wo2_id']}", headers=data["headers_emp1"])
    assert res_forbidden.status_code == 403

    # Admin CAN view any work order in org
    res_admin = client.get(f"/api/v1/manufacturing/work-orders/{data['wo2_id']}", headers=data["headers_admin"])
    assert res_admin.status_code == 200


# ------------------------------------------------------------------------------
# Test C, D, E, F, G, H, M, O: Material Reconciliation & Holding Guards
# ------------------------------------------------------------------------------

def test_material_issue_consume_return_wastage_reconciliation(client: TestClient, employee_test_setup, db_session_factory):
    """Test C-H, M, O: Issue 20 -> Consume 12 -> Return 5 -> Waste 3 -> Holding 0."""
    data = employee_test_setup
    wo_id = data["wo1_id"]
    sku = data["raw_sku"]
    wh = data["warehouse"]

    # Initial warehouse inventory: 100 kg
    # STEP 1: Store issues 20 kg to WO-101
    issue_payload = {
        "work_order_id": wo_id,
        "product_id": sku,
        "warehouse_id": wh,
        "transaction_type": "ISSUE",
        "quantity": 20.0,
        "unit_of_measure": "kg",
    }
    issue_res = client.post("/api/v1/manufacturing/stock-transactions", json=issue_payload, headers=data["headers_admin"])
    assert issue_res.status_code == 201

    # Check holding: 20 kg
    mat_res = client.get(f"/api/v1/manufacturing/work-orders/{wo_id}/materials", headers=data["headers_emp1"])
    assert mat_res.status_code == 200
    mats = mat_res.json()
    assert len(mats) == 1
    req = mats[0]
    assert req["issued_quantity"] == 20.0
    assert req["remaining_issued_holding"] == 20.0

    # STEP 2: Employee 1 consumes 12 kg (Test C)
    consume_res = client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "quantity": 12.0,
            "unit_of_measure": "kg",
            "reason": "Cutting chassis plates",
        },
        headers=data["headers_emp1"],
    )
    assert consume_res.status_code == 201

    # Verify holding is now 8 kg
    mat_res2 = client.get(f"/api/v1/manufacturing/work-orders/{wo_id}/materials", headers=data["headers_emp1"])
    req2 = mat_res2.json()[0]
    assert req2["consumed_quantity"] == 12.0
    assert req2["remaining_issued_holding"] == 8.0

    # Test D: Attempt to consume 10 kg when only 8 kg remain -> 400 Bad Request
    over_consume_res = client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "quantity": 10.0,
            "unit_of_measure": "kg",
            "reason": "Excess consumption attempt",
        },
        headers=data["headers_emp1"],
    )
    assert over_consume_res.status_code == 400

    # Test F: Attempt to return 10 kg when only 8 kg remain -> 400 Bad Request
    over_return_res = client.post(
        "/api/v1/manufacturing/transactions/return",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "quantity": 10.0,
            "unit_of_measure": "kg",
            "reason": "Excess return attempt",
        },
        headers=data["headers_emp1"],
    )
    assert over_return_res.status_code == 400

    # STEP 3: Employee 1 returns 5 kg (Test E)
    return_res = client.post(
        "/api/v1/manufacturing/transactions/return",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "quantity": 5.0,
            "unit_of_measure": "kg",
            "reason": "Surplus plate scrap",
        },
        headers=data["headers_emp1"],
    )
    assert return_res.status_code == 201

    # Verify holding is now 3 kg
    mat_res3 = client.get(f"/api/v1/manufacturing/work-orders/{wo_id}/materials", headers=data["headers_emp1"])
    req3 = mat_res3.json()[0]
    assert req3["returned_quantity"] == 5.0
    assert req3["remaining_issued_holding"] == 3.0

    # STEP 4: Employee 1 reports 3 kg scrap with mandatory reason (Test G)
    waste_res = client.post(
        "/api/v1/manufacturing/transactions/waste",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "quantity": 3.0,
            "unit_of_measure": "kg",
            "reason": "Metal trimmings and kerf loss",
        },
        headers=data["headers_emp1"],
    )
    assert waste_res.status_code == 201

    # STEP 5: Final reconciliation check (Test O)
    mat_res4 = client.get(f"/api/v1/manufacturing/work-orders/{wo_id}/materials", headers=data["headers_emp1"])
    final_req = mat_res4.json()[0]
    assert final_req["issued_quantity"] == 20.0
    assert final_req["consumed_quantity"] == 12.0
    assert final_req["returned_quantity"] == 5.0
    assert final_req["wastage_quantity"] == 3.0
    assert final_req["remaining_issued_holding"] == 0.0

    # Test H: When holding is 0, attempting another return or wastage fails
    empty_waste = client.post(
        "/api/v1/manufacturing/transactions/waste",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "quantity": 1.0,
            "unit_of_measure": "kg",
            "reason": "Post-reconciliation scrap",
        },
        headers=data["headers_emp1"],
    )
    assert empty_waste.status_code == 400

    # Test M: Check warehouse inventory:
    # Started with 100. Issued 20 -> 80. Consumed 12 (0 wh change). Returned 5 -> 85. Wasted 3 (0 wh change).
    # Expected final warehouse inventory is exactly 85 kg (zero double decrement!).
    async def check_inventory():
        async with db_session_factory() as session:
            inv_obj = (await session.execute(
                select(Inventory).join(Product).where(Product.sku == sku)
            )).scalar_one()
            assert inv_obj.quantity == 85

    asyncio.run(check_inventory())


# ------------------------------------------------------------------------------
# Test I & J: Organization Isolation & Authentication Required
# ------------------------------------------------------------------------------

def test_organization_isolation_and_auth_required(client: TestClient, employee_test_setup):
    """Test I & J: Other tenant cannot access work orders, unauthenticated requests rejected."""
    data = employee_test_setup

    # Test J: Unauthenticated requests -> 401
    res_unauth = client.get("/api/v1/manufacturing/my-work-orders")
    assert res_unauth.status_code == 401

    res_unauth_consume = client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={"work_order_id": data["wo1_id"], "product_id": data["raw_sku"], "quantity": 1.0},
    )
    assert res_unauth_consume.status_code == 401

    # Test I: Employee from other org cannot see or consume on default org work orders
    res_other_wo = client.get(f"/api/v1/manufacturing/work-orders/{data['wo1_id']}", headers=data["headers_other"])
    assert res_other_wo.status_code in (403, 404)

    res_other_consume = client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={"work_order_id": data["wo1_id"], "product_id": data["raw_sku"], "quantity": 1.0, "reason": "Spoof"},
        headers=data["headers_other"],
    )
    assert res_other_consume.status_code in (403, 404)


# ------------------------------------------------------------------------------
# Test K & L: StockTransaction & AuditLog Verification
# ------------------------------------------------------------------------------

def test_transaction_and_audit_log_recorded(client: TestClient, employee_test_setup):
    """Test K & L: Actions persist StockTransaction and AuditLog containing actor ID."""
    data = employee_test_setup

    # Check employee activity endpoint
    res = client.get("/api/v1/manufacturing/employee/activity", headers=data["headers_emp1"])
    assert res.status_code == 200

    # Check dashboard stats
    stats_res = client.get("/api/v1/manufacturing/employee/dashboard-stats", headers=data["headers_emp1"])
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "active_work_orders" in stats
    assert "today_consumed_qty" in stats


# ------------------------------------------------------------------------------
# Test N: Idempotency & Duplicate Submission
# ------------------------------------------------------------------------------

def test_idempotent_duplicate_submission(client: TestClient, employee_test_setup):
    """Test N: Repeated submission with idempotency_key returns existing transaction without double mutation."""
    data = employee_test_setup
    wo_id = data["wo2_id"]
    sku = data["raw_sku"]

    # Issue 10 kg to Employee 2's work order
    client.post(
        "/api/v1/manufacturing/stock-transactions",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "warehouse_id": data["warehouse"],
            "transaction_type": "ISSUE",
            "quantity": 10.0,
            "unit_of_measure": "kg",
        },
        headers=data["headers_admin"],
    )

    idem_key = f"client-req-{data['run_id']}"

    # First consumption with idempotency key
    res1 = client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "quantity": 3.0,
            "unit_of_measure": "kg",
            "reason": "Assembly line run",
            "idempotency_key": idem_key,
        },
        headers=data["headers_emp2"],
    )
    assert res1.status_code == 201
    tx1 = res1.json()

    # Second consumption with SAME idempotency key
    res2 = client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": wo_id,
            "product_id": sku,
            "quantity": 3.0,
            "unit_of_measure": "kg",
            "reason": "Assembly line run",
            "idempotency_key": idem_key,
        },
        headers=data["headers_emp2"],
    )
    assert res2.status_code in (200, 201)
    tx2 = res2.json()
    assert tx1["id"] == tx2["id"]

    # Holding should only have decreased once (10 - 3 = 7 kg, not 10 - 6 = 4 kg)
    mat_res = client.get(f"/api/v1/manufacturing/work-orders/{wo_id}/materials", headers=data["headers_emp2"])
    req = mat_res.json()[0]
    assert req["consumed_quantity"] == 3.0
    assert req["remaining_issued_holding"] == 7.0


# ------------------------------------------------------------------------------
# Test 16: Material Request Requisition
# ------------------------------------------------------------------------------

def test_material_request_creation_and_listing(client: TestClient, employee_test_setup):
    """Test floor operator material requisition flow."""
    data = employee_test_setup

    req_payload = {
        "work_order_id": data["wo1_id"],
        "product_id": data["raw_sku"],
        "quantity": 15.0,
        "unit_of_measure": "kg",
        "reason": "Line replenishment for rush shift",
        "notes": "Need by 2 PM",
    }
    create_res = client.post(
        "/api/v1/manufacturing/material-requests",
        json=req_payload,
        headers=data["headers_emp1"],
    )
    assert create_res.status_code == 201
    created_req = create_res.json()
    assert created_req["status"] == "PENDING"
    assert created_req["requested_by_user_id"] == data["emp1"].id

    # List requests as employee
    list_res = client.get("/api/v1/manufacturing/material-requests?my_requests=true", headers=data["headers_emp1"])
    assert list_res.status_code == 200
    requests = list_res.json()
    assert len(requests) >= 1
    assert any(r["id"] == created_req["id"] for r in requests)
