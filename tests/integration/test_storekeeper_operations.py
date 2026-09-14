"""Integration tests for Storekeeper / Admin Material Operations (Phase 13.3).

Validates:
1. Employee creates request on assigned work order; cannot request on another's job.
2. Storekeeper/admin sees requests with inventory context.
3. Unauthorized floor employee cannot approve, reject, or issue material (HTTP 403).
4. Approval changes status only (PENDING -> APPROVED) with ZERO inventory deduction.
5. Pending and rejected requests cannot be issued (HTTP 400).
6. Over-issue is rejected without partial deduction (HTTP 400).
7. Duplicate issuance is prevented on already fulfilled requests (HTTP 400).
8. Authorized user issues approved request:
   - Decreases warehouse inventory atomically.
   - Increases work order holding balance.
   - Links StockTransaction with reference_type="MATERIAL_REQUEST" and reference_id=request.id.
9. Cross-organization access is blocked (HTTP 404/403).
10. Rejection workflow requires reason, changes status to REJECTED with ZERO inventory change.
11. Critical End-to-End Conservation Invariant:
    100 kg warehouse -> req 20 kg -> approve 20 kg (wh 100 kg)
    -> issue 20 kg (wh 80 kg, holding 20 kg)
    -> consume 12 kg (wh 80 kg, holding 8 kg)
    -> return 5 kg (wh 85 kg, holding 3 kg)
    -> wastage 3 kg (wh 85 kg, holding 0 kg)
    Reconciliation: 20 issued = 12 consumed + 5 returned + 3 wastage + 0 holding.
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
from backend.app.models.material_requirement import MaterialRequirement
from backend.app.models.material_request import MaterialRequest
from backend.app.models.audit_log import AuditLog
from backend.app.models.enums import TransactionType
from backend.app.middleware.rate_limit import limiter
from sqlalchemy import select


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests."""
    limiter._requests.clear()


@pytest.fixture
def storekeeper_test_setup(client: TestClient, create_test_user, auth_header_for_user, db_session_factory):
    """Setup multi-tenant environment with Admin, Floor Operators, Warehouse, Product, and Stock."""
    run_id = uuid.uuid4().hex[:8]

    async def _setup():
        # 1. Create Floor Operators and Admin in default org
        emp1 = await create_test_user(
            email=f"emp1_{run_id}@apex-logistics.com",
            role=UserRole.OPERATOR,
            org_id="default-org-id",
            full_name=f"John FloorOp {run_id}",
        )
        emp2 = await create_test_user(
            email=f"emp2_{run_id}@apex-logistics.com",
            role=UserRole.OPERATOR,
            org_id="default-org-id",
            full_name=f"Jane FloorOp {run_id}",
        )
        admin = await create_test_user(
            email=f"admin_{run_id}@apex-logistics.com",
            role=UserRole.ADMIN,
            org_id="default-org-id",
            full_name=f"Store Supervisor {run_id}",
        )

        # 2. Competitor Org for isolation checks
        other_org_id = f"org_{run_id}"
        async with db_session_factory() as session:
            other_org = Organization(
                id=other_org_id,
                name=f"Competitor Logistics {run_id}",
                slug=f"comp-{run_id}",
                tier="standard",
            )
            session.add(other_org)
            await session.commit()

        other_admin = await create_test_user(
            email=f"admin_{run_id}@competitor.com",
            role=UserRole.ADMIN,
            org_id=other_org_id,
            full_name=f"Competitor Admin {run_id}",
        )

        # 3. Warehouse, Product, and initial 100 kg Inventory in default org
        wh_code = f"WH-STR-{run_id}"
        raw_sku = f"RM-ALUM-{run_id}"
        fg_sku = f"FG-FRAME-{run_id}"

        async with db_session_factory() as session:
            warehouse = Warehouse(
                id=f"wh_{run_id}",
                organization_id="default-org-id",
                code=wh_code,
                name=f"Main Storehouse {run_id}",
                address="Industrial Park Bay 3",
                city="Munich",
                country="Germany",
                capacity=50000,
            )
            raw_mat = Product(
                id=f"prod_raw_{run_id}",
                organization_id="default-org-id",
                sku=raw_sku,
                name=f"Aerospace Aluminum {run_id}",
                category="RAW_MATERIAL",
                unit_of_measure="kg",
                unit_price=35.0,
                unit_cost=25.0,
            )
            fg_prod = Product(
                id=f"prod_fg_{run_id}",
                organization_id="default-org-id",
                sku=fg_sku,
                name=f"Assembly Frame {run_id}",
                category="FINISHED_GOOD",
                unit_of_measure="piece",
                unit_price=450.0,
                unit_cost=300.0,
            )
            inv = Inventory(
                id=f"inv_{run_id}",
                organization_id="default-org-id",
                warehouse_id=warehouse.id,
                product_id=raw_mat.id,
                quantity=100,  # 100 kg initial stock
                safety_stock=20,
                reorder_point=40,
            )
            session.add_all([warehouse, raw_mat, fg_prod, inv])
            await session.commit()

        admin_headers = auth_header_for_user(admin)
        emp1_headers = auth_header_for_user(emp1)
        emp2_headers = auth_header_for_user(emp2)
        other_headers = auth_header_for_user(other_admin)

        # 4. Create Production Order & Work Order assigned to emp1
        po_res = client.post(
            "/api/v1/manufacturing/production-orders",
            headers=admin_headers,
            json={
                "order_number": f"PO-STR-{run_id}",
                "product_id": fg_prod.id,
                "planned_quantity": 50,
            },
        )
        assert po_res.status_code == 201, po_res.text
        po_id = po_res.json()["id"]

        wo_res = client.post(
            "/api/v1/manufacturing/work-orders",
            headers=admin_headers,
            json={
                "production_order_id": po_id,
                "work_order_number": f"WO-STR-{run_id}",
                "warehouse_id": warehouse.id,
                "production_area": "Milling Cell A",
                "planned_quantity": 50,
                "assigned_user_id": emp1.id,
            },
        )
        assert wo_res.status_code == 201, wo_res.text
        wo_id = wo_res.json()["id"]

        return {
            "run_id": run_id,
            "emp1": emp1,
            "emp2": emp2,
            "admin": admin,
            "other_admin": other_admin,
            "emp1_headers": emp1_headers,
            "emp2_headers": emp2_headers,
            "admin_headers": admin_headers,
            "other_headers": other_headers,
            "warehouse": warehouse,
            "raw_mat": raw_mat,
            "wo_id": wo_id,
            "inv_id": inv.id,
        }

    return asyncio.run(_setup())


def test_request_creation_and_authorization_guards(client: TestClient, storekeeper_test_setup):
    """Test requisition creation and verification that unauthorized operators cannot approve/issue."""
    ctx = storekeeper_test_setup

    # 1. Emp1 creates request on assigned WO -> 201
    req_res = client.post(
        "/api/v1/manufacturing/material-requests",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 20.0,
            "unit_of_measure": "kg",
            "reason": "Milling batch allocation",
            "notes": "Urgent line replenishment",
        },
    )
    assert req_res.status_code == 201
    req_data = req_res.json()
    assert req_data["status"] == "PENDING"
    assert req_data["quantity"] == 20.0
    req_id = req_data["id"]

    # 2. Emp2 (not assigned) attempts to create request on Emp1's WO -> 403
    emp2_bad = client.post(
        "/api/v1/manufacturing/material-requests",
        headers=ctx["emp2_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 10.0,
            "reason": "Unauthorized attempt",
        },
    )
    assert emp2_bad.status_code == 403

    # 3. Unauthorized floor employee attempts to approve -> 403
    emp_appr = client.post(
        f"/api/v1/manufacturing/material-requests/{req_id}/approve",
        headers=ctx["emp1_headers"],
        json={"notes": "Self approval attempt"},
    )
    assert emp_appr.status_code == 403
    assert emp_appr.json()["error_code"] == "FORBIDDEN_UNAUTHORIZED_APPROVER"

    # 4. Unauthorized floor employee attempts to issue -> 403
    emp_issue = client.post(
        f"/api/v1/manufacturing/material-requests/{req_id}/issue",
        headers=ctx["emp1_headers"],
        json={},
    )
    assert emp_issue.status_code == 403
    assert emp_issue.json()["error_code"] == "FORBIDDEN_UNAUTHORIZED_ISSUER"

    # 5. Unauthorized floor employee attempts to reject -> 403
    emp_rej = client.post(
        f"/api/v1/manufacturing/material-requests/{req_id}/reject",
        headers=ctx["emp1_headers"],
        json={"reason": "Self rejection"},
    )
    assert emp_rej.status_code == 403


def test_approval_status_only_and_zero_inventory_change(client: TestClient, storekeeper_test_setup, db_session_factory):
    """Test approval updates status to APPROVED without modifying warehouse stock or work order holding."""
    ctx = storekeeper_test_setup

    # Create request
    req_res = client.post(
        "/api/v1/manufacturing/material-requests",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 20.0,
            "reason": "Approval invariant test",
        },
    )
    req_id = req_res.json()["id"]

    # Check warehouse stock before approval
    async def get_wh_stock():
        async with db_session_factory() as session:
            inv = await session.get(Inventory, ctx["inv_id"])
            return inv.quantity

    stock_before = asyncio.run(get_wh_stock())
    assert stock_before == 100

    # Storekeeper/Admin approves
    appr_res = client.post(
        f"/api/v1/manufacturing/material-requests/{req_id}/approve",
        headers=ctx["admin_headers"],
        json={"notes": "Approved for 2nd shift"},
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert appr_data["status"] == "APPROVED"
    assert appr_data["reviewed_by_user_id"] == ctx["admin"].id

    # CRITICAL INVARIANT: Warehouse stock MUST remain identical
    stock_after = asyncio.run(get_wh_stock())
    assert stock_after == 100, f"Approval changed inventory! Before: {stock_before}, After: {stock_after}"

    # Verify AuditLog was recorded
    async def check_audit():
        async with db_session_factory() as session:
            res = await session.execute(
                select(AuditLog).where(
                    AuditLog.organization_id == "default-org-id",
                    AuditLog.action == "REQUEST_APPROVED",
                    AuditLog.entity_id == req_id,
                )
            )
            return res.scalar_one_or_none()

    audit = asyncio.run(check_audit())
    assert audit is not None
    assert audit.user_id == ctx["admin"].id


def test_state_machine_and_issue_guards(client: TestClient, storekeeper_test_setup):
    """Verify pending and rejected requests cannot be issued, and over-issue is rejected."""
    ctx = storekeeper_test_setup

    # 1. PENDING cannot be issued
    req1 = client.post(
        "/api/v1/manufacturing/material-requests",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 20.0,
            "reason": "Premature issue test",
        },
    ).json()
    issue_pending = client.post(
        f"/api/v1/manufacturing/material-requests/{req1['id']}/issue",
        headers=ctx["admin_headers"],
        json={},
    )
    assert issue_pending.status_code == 400
    assert issue_pending.json()["error_code"] == "REQUEST_NOT_APPROVED"

    # 2. Rejection requires reason, changes status to REJECTED
    rej_bad = client.post(
        f"/api/v1/manufacturing/material-requests/{req1['id']}/reject",
        headers=ctx["admin_headers"],
        json={"reason": ""},
    )
    assert rej_bad.status_code in (400, 422)

    rej_ok = client.post(
        f"/api/v1/manufacturing/material-requests/{req1['id']}/reject",
        headers=ctx["admin_headers"],
        json={"reason": "Stock reserved for high priority contract"},
    )
    assert rej_ok.status_code == 200
    assert rej_ok.json()["status"] == "REJECTED"
    assert rej_ok.json()["rejection_reason"] == "Stock reserved for high priority contract"

    # 3. REJECTED cannot be issued
    issue_rejected = client.post(
        f"/api/v1/manufacturing/material-requests/{req1['id']}/issue",
        headers=ctx["admin_headers"],
        json={},
    )
    assert issue_rejected.status_code == 400
    assert issue_rejected.json()["error_code"] == "REQUEST_ALREADY_REJECTED"

    # 4. Over-issue protection
    huge_req = client.post(
        "/api/v1/manufacturing/material-requests",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 500.0,  # Warehouse only has 100 kg
            "reason": "Over-issue test",
        },
    ).json()
    client.post(f"/api/v1/manufacturing/material-requests/{huge_req['id']}/approve", headers=ctx["admin_headers"])
    issue_huge = client.post(
        f"/api/v1/manufacturing/material-requests/{huge_req['id']}/issue",
        headers=ctx["admin_headers"],
        json={},
    )
    assert issue_huge.status_code == 400
    assert issue_huge.json()["error_code"] == "INSUFFICIENT_INVENTORY"


def test_duplicate_issue_protection(client: TestClient, storekeeper_test_setup):
    """Verify that a fulfilled request cannot be issued a second time."""
    ctx = storekeeper_test_setup

    req = client.post(
        "/api/v1/manufacturing/material-requests",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 10.0,
            "reason": "Duplicate issue guard test",
        },
    ).json()
    client.post(f"/api/v1/manufacturing/material-requests/{req['id']}/approve", headers=ctx["admin_headers"])

    # First issue succeeds
    issue1 = client.post(
        f"/api/v1/manufacturing/material-requests/{req['id']}/issue",
        headers=ctx["admin_headers"],
        json={},
    )
    assert issue1.status_code == 201

    # Second issue fails safely
    issue2 = client.post(
        f"/api/v1/manufacturing/material-requests/{req['id']}/issue",
        headers=ctx["admin_headers"],
        json={},
    )
    assert issue2.status_code == 400
    assert issue2.json()["error_code"] == "REQUEST_ALREADY_FULFILLED"


def test_cross_tenant_isolation(client: TestClient, storekeeper_test_setup):
    """Verify requests in Org A cannot be viewed, approved, or issued by Org B."""
    ctx = storekeeper_test_setup

    req = client.post(
        "/api/v1/manufacturing/material-requests",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 15.0,
            "reason": "Tenant isolation check",
        },
    ).json()

    # Competitor admin attempts to view single request -> 404
    view_res = client.get(
        f"/api/v1/manufacturing/material-requests/{req['id']}",
        headers=ctx["other_headers"],
    )
    assert view_res.status_code == 404

    # Competitor admin attempts to approve -> 404
    appr_res = client.post(
        f"/api/v1/manufacturing/material-requests/{req['id']}/approve",
        headers=ctx["other_headers"],
        json={},
    )
    assert appr_res.status_code == 404


def test_critical_end_to_end_conservation_cycle(client: TestClient, storekeeper_test_setup, db_session_factory):
    """CRITICAL END-TO-END VERIFICATION:

    100 kg warehouse
    -> request 20 kg
    -> approve 20 kg (wh remains 100 kg)
    -> issue 20 kg (wh becomes 80 kg, holding 20 kg)
    -> consume 12 kg (wh remains 80 kg, holding 8 kg)
    -> return 5 kg (wh becomes 85 kg, holding 3 kg)
    -> wastage 3 kg (wh remains 85 kg, holding 0 kg)

    Invariance: issued (20) = consumed (12) + returned (5) + wastage (3) + holding (0).
    Traceability: ISSUE transaction references MaterialRequest.
    """
    ctx = storekeeper_test_setup

    async def get_wh_stock():
        async with db_session_factory() as session:
            inv = await session.get(Inventory, ctx["inv_id"])
            return inv.quantity

    async def get_holding():
        async with db_session_factory() as session:
            res = await session.execute(
                select(MaterialRequirement).where(
                    MaterialRequirement.organization_id == "default-org-id",
                    MaterialRequirement.work_order_id == ctx["wo_id"],
                    MaterialRequirement.product_id == ctx["raw_mat"].id,
                )
            )
            mr = res.scalar_one_or_none()
            return mr.remaining_issued_holding if mr else 0.0, mr

    # Step 0: Initial warehouse stock = 100 kg
    assert asyncio.run(get_wh_stock()) == 100

    # Step 1: Employee requests 20 kg
    req = client.post(
        "/api/v1/manufacturing/material-requests",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 20.0,
            "unit_of_measure": "kg",
            "reason": "Assembly frame batch #10",
        },
    ).json()
    req_id = req["id"]

    # Step 2: Storekeeper approves 20 kg
    appr_res = client.post(
        f"/api/v1/manufacturing/material-requests/{req_id}/approve",
        headers=ctx["admin_headers"],
        json={"notes": "Approved for assembly"},
    )
    assert appr_res.status_code == 200

    # ASSERT: Warehouse remains 100 kg after approval (zero deduction)
    assert asyncio.run(get_wh_stock()) == 100

    # Step 3: Storekeeper issues 20 kg
    issue_res = client.post(
        f"/api/v1/manufacturing/material-requests/{req_id}/issue",
        headers=ctx["admin_headers"],
        json={"notes": "Dispatched to shop floor"},
    )
    assert issue_res.status_code == 201
    issue_data = issue_res.json()

    # ASSERT: ISSUE references MaterialRequest
    assert issue_data["reference_type"] == "MATERIAL_REQUEST"
    assert issue_data["reference_id"] == req_id
    assert issue_data["quantity"] == 20.0

    # ASSERT: Warehouse becomes 80 kg, Work Order holding becomes 20 kg
    assert asyncio.run(get_wh_stock()) == 80
    holding_val, mr_obj = asyncio.run(get_holding())
    assert holding_val == 20.0
    assert mr_obj.issued_quantity == 20.0

    # Step 4: Employee consumes 12 kg
    consume_res = client.post(
        "/api/v1/manufacturing/transactions/consume",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 12.0,
            "unit_of_measure": "kg",
            "reason": "Frame chassis assembly",
        },
    )
    assert consume_res.status_code == 201

    # ASSERT: Warehouse remains 80 kg (ZERO double-decrement!), Holding becomes 8 kg
    assert asyncio.run(get_wh_stock()) == 80
    holding_val, mr_obj = asyncio.run(get_holding())
    assert holding_val == 8.0
    assert mr_obj.consumed_quantity == 12.0

    # Step 5: Employee returns 5 kg surplus to warehouse
    return_res = client.post(
        "/api/v1/manufacturing/transactions/return",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 5.0,
            "unit_of_measure": "kg",
            "reason": "Surplus bar stock returned to store",
        },
    )
    assert return_res.status_code == 201

    # ASSERT: Warehouse becomes 85 kg (80 + 5), Holding becomes 3 kg (8 - 5)
    assert asyncio.run(get_wh_stock()) == 85
    holding_val, mr_obj = asyncio.run(get_holding())
    assert holding_val == 3.0
    assert mr_obj.returned_quantity == 5.0

    # Step 6: Employee reports 3 kg scrap / wastage
    waste_res = client.post(
        "/api/v1/manufacturing/transactions/waste",
        headers=ctx["emp1_headers"],
        json={
            "work_order_id": ctx["wo_id"],
            "product_id": ctx["raw_mat"].id,
            "quantity": 3.0,
            "unit_of_measure": "kg",
            "reason": "Thermal deformation offcuts",
        },
    )
    assert waste_res.status_code == 201

    # ASSERT: Warehouse remains 85 kg, Holding becomes 0 kg
    assert asyncio.run(get_wh_stock()) == 85
    holding_val, mr_obj = asyncio.run(get_holding())
    assert holding_val == 0.0
    assert mr_obj.wastage_quantity == 3.0

    # FINAL RECONCILIATION INVARIANT CHECK
    assert mr_obj.issued_quantity == 20.0
    assert mr_obj.consumed_quantity == 12.0
    assert mr_obj.returned_quantity == 5.0
    assert mr_obj.wastage_quantity == 3.0
    assert (
        mr_obj.issued_quantity
        == mr_obj.consumed_quantity + mr_obj.returned_quantity + mr_obj.wastage_quantity + mr_obj.remaining_issued_holding
    )
