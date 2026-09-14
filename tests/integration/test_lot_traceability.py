"""Integration tests for Phase 13.4 — Lot / Batch Traceability.

Validates:
1. MaterialLot receipt creates lot and aggregate warehouse balance atomically.
2. Only ADMIN can receive material lots (OPERATOR gets HTTP 403).
3. Material issue explicitly with lot_id decrements lot warehouse balance and credits WorkOrderLotHolding.
4. Over-issue from a lot balance is rejected (HTTP 400 INSUFFICIENT_LOT_INVENTORY).
5. Consumption by lot decrements WorkOrderLotHolding without touching warehouse aggregate inventory.
6. Over-consumption from lot holding is rejected (HTTP 400 EXCEEDS_LOT_HOLDING).
7. Return by lot restores lot warehouse balance and warehouse aggregate, decrementing WorkOrderLotHolding.
8. Wastage by lot decrements WorkOrderLotHolding without returning stock to warehouse.
9. Full traceability API returns complete supplier, balance, work-order holding, and movement ledger.
10. Multi-tenant isolation blocks cross-organization lot queries and actions (HTTP 404/403).
11. Critical E2E physical conservation cycle:
    100 kg received -> 20 kg issued -> 12 kg consumed -> 5 kg returned -> 3 kg wasted
    Reconciliation: 20 issued = 12 consumed + 5 returned + 3 wastage
    Total physical: 85 warehouse + 12 consumed + 3 scrap = 100 original.
"""

import uuid
import pytest
import asyncio
from fastapi.testclient import TestClient
from backend.app.models.user import User, UserRole
from backend.app.models.organization import Organization
from backend.app.models.warehouse import Warehouse
from backend.app.models.supplier import Supplier
from backend.app.models.product import Product
from backend.app.models.inventory import Inventory
from backend.app.models.stock_transaction import StockTransaction
from backend.app.models.material_requirement import MaterialRequirement
from backend.app.models.material_request import MaterialRequest
from backend.app.models.material_lot import MaterialLot, WorkOrderLotHolding
from backend.app.models.production_order import ProductionOrder
from backend.app.models.work_order import WorkOrder
from backend.app.models.enums import TransactionType, ProductionOrderStatus, WorkOrderStatus
from backend.app.middleware.rate_limit import limiter
from sqlalchemy import select


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests."""
    limiter._requests.clear()


@pytest.fixture
def lot_test_setup(client: TestClient, create_test_user, auth_header_for_user, db_session_factory):
    """Setup multi-tenant environment with Admin, Operator, Warehouse, Supplier, Products, and Orders."""
    run_id = uuid.uuid4().hex[:8]

    async def _setup():
        # 1. Create Users
        admin = await create_test_user(
            email=f"admin_lot_{run_id}@apex-logistics.com",
            role=UserRole.ADMIN,
            org_id="default-org-id",
            full_name=f"Store Supervisor {run_id}",
        )
        operator = await create_test_user(
            email=f"op_lot_{run_id}@apex-logistics.com",
            role=UserRole.OPERATOR,
            org_id="default-org-id",
            full_name=f"Floor Operator {run_id}",
        )

        # 2. Competitor Org for isolation checks
        other_org_id = f"org_comp_{run_id}"
        async with db_session_factory() as session:
            other_org = Organization(
                id=other_org_id,
                name=f"Competitor Corp {run_id}",
                slug=f"comp-{run_id}",
                tier="standard",
            )
            session.add(other_org)
            await session.commit()

        other_admin = await create_test_user(
            email=f"admin_comp_{run_id}@competitor.com",
            role=UserRole.ADMIN,
            org_id=other_org_id,
            full_name=f"Competitor Admin {run_id}",
        )

        # 3. Warehouse, Supplier, Products, Orders
        wh_code = f"WH-LOT-{run_id}"
        raw_sku = f"RM-STEEL-{run_id}"
        fg_sku = f"FG-GEAR-{run_id}"

        async with db_session_factory() as session:
            supplier = Supplier(
                organization_id="default-org-id",
                name=f"Apex Steel Foundry {run_id}",
                status="active",
                is_active=True,
            )
            session.add(supplier)

            wh = Warehouse(
                organization_id="default-org-id",
                code=wh_code,
                name=f"Central Metal Store {run_id}",
            )
            session.add(wh)

            raw_prod = Product(
                organization_id="default-org-id",
                sku=raw_sku,
                name=f"High Tensile Steel Sheet {run_id}",
                category="RAW_MATERIAL",
                material_type="RAW_MATERIAL",
                unit_of_measure="kg",
            )
            session.add(raw_prod)

            fg_prod = Product(
                organization_id="default-org-id",
                sku=fg_sku,
                name=f"Precision Drive Gear {run_id}",
                category="FINISHED_GOOD",
                material_type="FINISHED_GOOD",
                unit_of_measure="piece",
            )
            session.add(fg_prod)
            await session.flush()

            po = ProductionOrder(
                organization_id="default-org-id",
                order_number=f"PO-LOT-{run_id}",
                product_id=fg_prod.id,
                planned_quantity=50.0,
                completed_quantity=0.0,
                status=ProductionOrderStatus.RELEASED,
            )
            session.add(po)
            await session.flush()

            wo = WorkOrder(
                organization_id="default-org-id",
                production_order_id=po.id,
                work_order_number=f"WO-LOT-{run_id}",
                warehouse_id=wh.id,
                assigned_user_id=operator.id,
                planned_quantity=20.0,
                completed_quantity=0.0,
                status=WorkOrderStatus.RELEASED,
            )
            session.add(wo)
            await session.flush()

            mat_req = MaterialRequirement(
                organization_id="default-org-id",
                production_order_id=po.id,
                work_order_id=wo.id,
                product_id=raw_prod.id,
                required_quantity=50.0,
                issued_quantity=0.0,
                consumed_quantity=0.0,
                returned_quantity=0.0,
                wastage_quantity=0.0,
                unit_of_measure="kg",
            )
            session.add(mat_req)
            await session.commit()

            supplier_id = supplier.id
            supplier_name = supplier.name
            wh_id = wh.id
            raw_prod_id = raw_prod.id
            wo_id = wo.id
            po_id = po.id

        admin_hdr = auth_header_for_user(admin)
        operator_hdr = auth_header_for_user(operator)
        other_hdr = auth_header_for_user(other_admin)

        return {
            "client": client,
            "admin": admin,
            "operator": operator,
            "other_admin": other_admin,
            "admin_headers": admin_hdr,
            "operator_headers": operator_hdr,
            "other_headers": other_hdr,
            "supplier_id": supplier_id,
            "supplier_name": supplier_name,
            "warehouse_id": wh_id,
            "warehouse_code": wh_code,
            "raw_product_id": raw_prod_id,
            "raw_product_sku": raw_sku,
            "work_order_id": wo_id,
            "production_order_id": po_id,
            "run_id": run_id,
            "db_session_factory": db_session_factory,
        }

    return asyncio.run(_setup())


def test_lot_receipt_and_authorization(lot_test_setup):
    """Verify material lot receipt creates lot and inventory atomically, enforced by RBAC."""
    setup = lot_test_setup
    client = setup["client"]
    admin_hdr = setup["admin_headers"]
    operator_hdr = setup["operator_headers"]
    run_id = setup["run_id"]

    lot_number = f"LOT-STL-{run_id}-001"

    # 1. Operator cannot receive material lots (HTTP 403)
    op_res = client.post(
        "/api/v1/manufacturing/lots/receive",
        json={
            "product_id": setup["raw_product_id"],
            "warehouse_id": setup["warehouse_id"],
            "supplier_id": setup["supplier_id"],
            "lot_number": lot_number,
            "quantity": 100.0,
            "unit_of_measure": "kg",
            "notes": "First mill shipment",
        },
        headers=operator_hdr,
    )
    assert op_res.status_code == 403

    # 2. Admin receives 100 kg into lot
    rec_res = client.post(
        "/api/v1/manufacturing/lots/receive",
        json={
            "product_id": setup["raw_product_id"],
            "warehouse_id": setup["warehouse_id"],
            "supplier_id": setup["supplier_id"],
            "lot_number": lot_number,
            "quantity": 100.0,
            "unit_of_measure": "kg",
            "notes": "First mill shipment",
        },
        headers=admin_hdr,
    )
    assert rec_res.status_code == 201
    lot_data = rec_res.json()
    assert lot_data["lot_number"] == lot_number
    assert lot_data["received_quantity"] == 100.0
    assert lot_data["current_quantity"] == 100.0
    assert lot_data["status"] == "ACTIVE"
    assert lot_data["supplier_id"] == setup["supplier_id"]

    # 3. Verify warehouse aggregate inventory updated to 100 kg
    inv_res = client.get("/api/v1/inventory", headers=admin_hdr)
    assert inv_res.status_code == 200
    inv_items = [i for i in inv_res.json() if i["sku"] == setup["raw_product_sku"]]
    assert len(inv_items) == 1
    assert inv_items[0]["quantity_on_hand"] == 100.0

    # 4. Verify StockTransaction logged
    tx_res = client.get(
        f"/api/v1/manufacturing/stock-transactions?lot_id={lot_data['id']}",
        headers=admin_hdr,
    )
    assert tx_res.status_code == 200
    txs = tx_res.json()
    assert len(txs) >= 1
    assert txs[0]["transaction_type"] == "RECEIPT"
    assert txs[0]["quantity"] == 100.0
    assert txs[0]["lot_id"] == lot_data["id"]


def test_lot_issue_and_holding(lot_test_setup):
    """Verify material issue by lot decrements lot balance, aggregate stock, and credits WorkOrderLotHolding."""
    setup = lot_test_setup
    client = setup["client"]
    admin_hdr = setup["admin_headers"]
    operator_hdr = setup["operator_headers"]
    run_id = setup["run_id"]

    lot_number = f"LOT-STL-{run_id}-002"

    # 1. Receive 100 kg
    rec_res = client.post(
        "/api/v1/manufacturing/lots/receive",
        json={
            "product_id": setup["raw_product_id"],
            "warehouse_id": setup["warehouse_id"],
            "supplier_id": setup["supplier_id"],
            "lot_number": lot_number,
            "quantity": 100.0,
            "unit_of_measure": "kg",
        },
        headers=admin_hdr,
    )
    assert rec_res.status_code == 201
    lot_id = rec_res.json()["id"]

    # 2. Operator requests 20 kg
    req_res = client.post(
        "/api/v1/manufacturing/material-requests",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "quantity": 20.0,
            "unit_of_measure": "kg",
            "reason": "Assembly line gear cutting",
        },
        headers=operator_hdr,
    )
    assert req_res.status_code == 201
    mat_req_id = req_res.json()["id"]

    # 3. Admin approves request
    app_res = client.post(
        f"/api/v1/manufacturing/material-requests/{mat_req_id}/approve",
        headers=admin_hdr,
    )
    assert app_res.status_code == 200

    # 4. Over-issue protection from lot: Attempt to issue 150 kg from lot with 100 kg balance
    # Temporarily create a request for 150 kg
    req_over = client.post(
        "/api/v1/manufacturing/material-requests",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "quantity": 150.0,
            "unit_of_measure": "kg",
            "reason": "Excessive request",
        },
        headers=operator_hdr,
    ).json()["id"]
    client.post(f"/api/v1/manufacturing/material-requests/{req_over}/approve", headers=admin_hdr)
    over_res = client.post(
        f"/api/v1/manufacturing/material-requests/{req_over}/issue",
        json={"lot_id": lot_id},
        headers=admin_hdr,
    )
    assert over_res.status_code == 400
    res_data = over_res.json()
    err_code = str(res_data.get("code") or res_data.get("error_code") or "")
    assert "INSUFFICIENT" in err_code

    # 5. Admin issues valid 20 kg specifying lot_id
    issue_res = client.post(
        f"/api/v1/manufacturing/material-requests/{mat_req_id}/issue",
        json={"lot_id": lot_id},
        headers=admin_hdr,
    )
    assert issue_res.status_code == 201

    # 6. Verify Lot warehouse balance is now 80 kg
    lot_get = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot_get["current_quantity"] == 80.0

    # 7. Verify WorkOrderLotHolding created for this work order and lot with 20 kg
    hold_res = client.get(f"/api/v1/manufacturing/work-orders/{setup['work_order_id']}/lots", headers=operator_hdr)
    assert hold_res.status_code == 200
    holdings = hold_res.json()
    assert len(holdings) == 1
    assert holdings[0]["lot_id"] == lot_id
    assert holdings[0]["issued_quantity"] == 20.0
    assert holdings[0]["remaining_holding"] == 20.0


def test_consumption_and_no_double_deduction(lot_test_setup):
    """Verify consumption by lot decrements holding and does NOT double-decrement warehouse stock."""
    setup = lot_test_setup
    client = setup["client"]
    admin_hdr = setup["admin_headers"]
    operator_hdr = setup["operator_headers"]
    run_id = setup["run_id"]

    lot_number = f"LOT-STL-{run_id}-003"

    # 1. Receive 100 kg
    rec_res = client.post(
        "/api/v1/manufacturing/lots/receive",
        json={
            "product_id": setup["raw_product_id"],
            "warehouse_id": setup["warehouse_id"],
            "supplier_id": setup["supplier_id"],
            "lot_number": lot_number,
            "quantity": 100.0,
            "unit_of_measure": "kg",
        },
        headers=admin_hdr,
    )
    lot_id = rec_res.json()["id"]

    # 2. Issue 20 kg directly to work order
    issue_tx = client.post(
        "/api/v1/manufacturing/stock-transactions",
        json={
            "warehouse_id": setup["warehouse_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "work_order_id": setup["work_order_id"],
            "transaction_type": "ISSUE",
            "quantity": 20.0,
            "unit_of_measure": "kg",
            "reason": "Floor delivery",
        },
        headers=admin_hdr,
    )
    assert issue_tx.status_code == 201

    # Verify initial post-issue balances
    lot_after_issue = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot_after_issue["current_quantity"] == 80.0

    # 3. Over-consumption attempt: Try to consume 25 kg (only 20 kg in holding)
    over_consume = client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 25.0,
            "unit_of_measure": "kg",
            "reason": "Over-consumption test",
        },
        headers=operator_hdr,
    )
    assert over_consume.status_code == 400

    # 4. Operator consumes 12 kg from lot
    con_res = client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 12.0,
            "unit_of_measure": "kg",
            "reason": "Stamping and milling",
        },
        headers=operator_hdr,
    )
    assert con_res.status_code == 201

    # 5. Invariant: Warehouse lot balance must STILL be 80 kg (consumption NEVER touches warehouse)
    lot_after_consume = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot_after_consume["current_quantity"] == 80.0

    # 6. Verify WorkOrderLotHolding has remaining holding of 8 kg
    hold_res = client.get(f"/api/v1/manufacturing/work-orders/{setup['work_order_id']}/lots", headers=operator_hdr)
    assert hold_res.status_code == 200
    h = hold_res.json()[0]
    assert h["consumed_quantity"] == 12.0
    assert h["remaining_holding"] == 8.0


def test_return_and_wastage_by_lot(lot_test_setup):
    """Verify return restores lot stock and wastage clears holding without restoring stock."""
    setup = lot_test_setup
    client = setup["client"]
    admin_hdr = setup["admin_headers"]
    operator_hdr = setup["operator_headers"]
    run_id = setup["run_id"]

    lot_number = f"LOT-STL-{run_id}-004"

    # 1. Receive 100 kg and Issue 20 kg
    lot_id = client.post(
        "/api/v1/manufacturing/lots/receive",
        json={
            "product_id": setup["raw_product_id"],
            "warehouse_id": setup["warehouse_id"],
            "supplier_id": setup["supplier_id"],
            "lot_number": lot_number,
            "quantity": 100.0,
            "unit_of_measure": "kg",
        },
        headers=admin_hdr,
    ).json()["id"]

    client.post(
        "/api/v1/manufacturing/stock-transactions",
        json={
            "warehouse_id": setup["warehouse_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "work_order_id": setup["work_order_id"],
            "transaction_type": "ISSUE",
            "quantity": 20.0,
            "unit_of_measure": "kg",
        },
        headers=admin_hdr,
    )

    # 2. Operator consumes 12 kg (leaving 8 kg holding)
    client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 12.0,
            "unit_of_measure": "kg",
        },
        headers=operator_hdr,
    )

    # 3. Operator returns 5 kg to warehouse
    ret_res = client.post(
        "/api/v1/manufacturing/transactions/return",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 5.0,
            "unit_of_measure": "kg",
            "reason": "Surplus metal returned to store",
        },
        headers=operator_hdr,
    )
    assert ret_res.status_code == 201

    # Warehouse lot balance increases to 85 kg
    lot_after_ret = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot_after_ret["current_quantity"] == 85.0

    # Holding decreases to 3 kg
    h_ret = client.get(f"/api/v1/manufacturing/work-orders/{setup['work_order_id']}/lots", headers=operator_hdr).json()[0]
    assert h_ret["returned_quantity"] == 5.0
    assert h_ret["remaining_holding"] == 3.0

    # 4. Operator reports 3 kg scrap/wastage
    waste_res = client.post(
        "/api/v1/manufacturing/transactions/waste",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 3.0,
            "unit_of_measure": "kg",
            "reason": "Trimmings and cutting shavings",
        },
        headers=operator_hdr,
    )
    assert waste_res.status_code == 201

    # Holding is now 0 kg
    h_waste = client.get(f"/api/v1/manufacturing/work-orders/{setup['work_order_id']}/lots", headers=operator_hdr).json()[0]
    assert h_waste["wastage_quantity"] == 3.0
    assert h_waste["remaining_holding"] == 0.0

    # Warehouse lot balance remains 85 kg
    lot_after_waste = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot_after_waste["current_quantity"] == 85.0


def test_lot_traceability_api(lot_test_setup):
    """Verify GET /lots/{id}/traceability derives complete lifecycle breakdown."""
    setup = lot_test_setup
    client = setup["client"]
    admin_hdr = setup["admin_headers"]
    operator_hdr = setup["operator_headers"]
    run_id = setup["run_id"]

    lot_number = f"LOT-STL-{run_id}-005"

    # Lifecycle: Receive 100 -> Issue 20 -> Consume 12 -> Return 5 -> Waste 3
    lot_id = client.post(
        "/api/v1/manufacturing/lots/receive",
        json={
            "product_id": setup["raw_product_id"],
            "warehouse_id": setup["warehouse_id"],
            "supplier_id": setup["supplier_id"],
            "lot_number": lot_number,
            "quantity": 100.0,
            "unit_of_measure": "kg",
        },
        headers=admin_hdr,
    ).json()["id"]

    client.post(
        "/api/v1/manufacturing/stock-transactions",
        json={
            "warehouse_id": setup["warehouse_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "work_order_id": setup["work_order_id"],
            "transaction_type": "ISSUE",
            "quantity": 20.0,
            "unit_of_measure": "kg",
        },
        headers=admin_hdr,
    )

    client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 12.0,
            "unit_of_measure": "kg",
        },
        headers=operator_hdr,
    )

    client.post(
        "/api/v1/manufacturing/transactions/return",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 5.0,
            "unit_of_measure": "kg",
        },
        headers=operator_hdr,
    )

    client.post(
        "/api/v1/manufacturing/transactions/waste",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 3.0,
            "unit_of_measure": "kg",
            "reason": "Scrap residue",
        },
        headers=operator_hdr,
    )

    # Fetch Traceability
    trace_res = client.get(f"/api/v1/manufacturing/lots/{lot_id}/traceability", headers=admin_hdr)
    assert trace_res.status_code == 200
    t = trace_res.json()

    assert t["lot_id"] == lot_id
    assert t["lot_number"] == lot_number
    assert t["supplier_name"] == setup["supplier_name"]
    assert t["initial_received_quantity"] == 100.0
    assert t["current_warehouse_balance"] == 85.0
    assert t["total_issued_to_work_orders"] == 20.0
    assert t["total_consumed_in_production"] == 12.0
    assert t["total_returned_to_warehouse"] == 5.0
    assert t["total_scrapped_or_wasted"] == 3.0
    assert t["total_current_floor_holding"] == 0.0

    # Verify work order summaries
    assert len(t["work_order_holdings"]) == 1
    assert t["work_order_holdings"][0]["work_order_id"] == setup["work_order_id"]

    # Verify movement history contains 5 sequential transactions
    assert len(t["movement_history"]) == 5
    tx_types = [m["transaction_type"] for m in t["movement_history"]]
    assert tx_types == ["RECEIPT", "ISSUE", "CONSUMPTION", "RETURN", "WASTAGE"]


def test_multi_tenant_lot_isolation(lot_test_setup):
    """Verify organization isolation blocks cross-tenant lot access."""
    setup = lot_test_setup
    client = setup["client"]
    admin_hdr = setup["admin_headers"]
    other_hdr = setup["other_headers"]
    run_id = setup["run_id"]

    # Org A creates a lot
    lot_id = client.post(
        "/api/v1/manufacturing/lots/receive",
        json={
            "product_id": setup["raw_product_id"],
            "warehouse_id": setup["warehouse_id"],
            "lot_number": f"LOT-ORGA-{run_id}",
            "quantity": 100.0,
            "unit_of_measure": "kg",
        },
        headers=admin_hdr,
    ).json()["id"]

    # Org B attempts to read Org A lot -> 404
    get_res = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=other_hdr)
    assert get_res.status_code == 404

    # Org B attempts to get traceability -> 404
    trace_res = client.get(f"/api/v1/manufacturing/lots/{lot_id}/traceability", headers=other_hdr)
    assert trace_res.status_code == 404


def test_critical_end_to_end_lot_reconciliation(lot_test_setup):
    """Critical invariant test: Complete multi-step cycle and physical conservation reconciliation."""
    setup = lot_test_setup
    client = setup["client"]
    admin_hdr = setup["admin_headers"]
    operator_hdr = setup["operator_headers"]
    run_id = setup["run_id"]

    lot_number = f"LOT-CRIT-{run_id}"

    # 1. RECEIVE 100 kg into LOT-A
    lot_res = client.post(
        "/api/v1/manufacturing/lots/receive",
        json={
            "product_id": setup["raw_product_id"],
            "warehouse_id": setup["warehouse_id"],
            "supplier_id": setup["supplier_id"],
            "lot_number": lot_number,
            "quantity": 100.0,
            "unit_of_measure": "kg",
        },
        headers=admin_hdr,
    )
    lot_id = lot_res.json()["id"]

    # State: Warehouse = 100, Lot = 100, Holding = 0
    lot = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot["current_quantity"] == 100.0

    # 2. REQUEST 20 kg
    req_id = client.post(
        "/api/v1/manufacturing/material-requests",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "quantity": 20.0,
            "unit_of_measure": "kg",
            "reason": "Critical run",
        },
        headers=operator_hdr,
    ).json()["id"]

    # 3. APPROVE (Zero inventory change)
    client.post(f"/api/v1/manufacturing/material-requests/{req_id}/approve", headers=admin_hdr)
    lot = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot["current_quantity"] == 100.0  # Invariant: Approval does NOT modify inventory

    # 4. ISSUE 20 kg with lot_id
    client.post(
        f"/api/v1/manufacturing/material-requests/{req_id}/issue",
        json={"lot_id": lot_id},
        headers=admin_hdr,
    )
    # State: Warehouse = 80, Holding = 20
    lot = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot["current_quantity"] == 80.0
    h = client.get(f"/api/v1/manufacturing/work-orders/{setup['work_order_id']}/lots", headers=operator_hdr).json()[0]
    assert h["remaining_holding"] == 20.0

    # 5. CONSUME 12 kg
    client.post(
        "/api/v1/manufacturing/transactions/consume",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 12.0,
            "unit_of_measure": "kg",
        },
        headers=operator_hdr,
    )
    # State: Warehouse = 80 (unchanged), Holding = 8, Consumed = 12
    lot = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot["current_quantity"] == 80.0
    h = client.get(f"/api/v1/manufacturing/work-orders/{setup['work_order_id']}/lots", headers=operator_hdr).json()[0]
    assert h["consumed_quantity"] == 12.0
    assert h["remaining_holding"] == 8.0

    # 6. RETURN 5 kg
    client.post(
        "/api/v1/manufacturing/transactions/return",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 5.0,
            "unit_of_measure": "kg",
        },
        headers=operator_hdr,
    )
    # State: Warehouse = 85 (+5), Holding = 3 (-5), Returned = 5
    lot = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot["current_quantity"] == 85.0
    h = client.get(f"/api/v1/manufacturing/work-orders/{setup['work_order_id']}/lots", headers=operator_hdr).json()[0]
    assert h["returned_quantity"] == 5.0
    assert h["remaining_holding"] == 3.0

    # 7. WASTAGE 3 kg
    client.post(
        "/api/v1/manufacturing/transactions/waste",
        json={
            "work_order_id": setup["work_order_id"],
            "product_id": setup["raw_product_id"],
            "lot_id": lot_id,
            "quantity": 3.0,
            "unit_of_measure": "kg",
            "reason": "Damaged trimmings",
        },
        headers=operator_hdr,
    )
    # State: Warehouse = 85 (unchanged), Holding = 0 (-3), Wastage = 3
    lot = client.get(f"/api/v1/manufacturing/lots/{lot_id}", headers=admin_hdr).json()
    assert lot["current_quantity"] == 85.0
    h = client.get(f"/api/v1/manufacturing/work-orders/{setup['work_order_id']}/lots", headers=operator_hdr).json()[0]
    assert h["wastage_quantity"] == 3.0
    assert h["remaining_holding"] == 0.0

    # 8. FINAL MATHEMATICAL RECONCILIATION
    issued = 20.0
    consumed = h["consumed_quantity"]
    returned = h["returned_quantity"]
    wastage = h["wastage_quantity"]
    remaining_holding = h["remaining_holding"]

    # Movement reconciliation: Issued = Consumed + Returned + Wastage + Remaining Floor Holding
    assert issued == consumed + returned + wastage + remaining_holding

    # Physical conservation: Initial Received = Current Warehouse + Current Floor Holding + Consumed + Wastage
    wh_final = lot["current_quantity"]
    total_physical = wh_final + remaining_holding + consumed + wastage
    assert total_physical == 100.0

    # Verify MaterialLot.current_quantity matches warehouse aggregate Inventory.quantity
    inv_res = client.get("/api/v1/inventory", headers=admin_hdr)
    inv_items = [i for i in inv_res.json() if i["sku"] == setup["raw_product_sku"]]
    assert len(inv_items) == 1
    assert inv_items[0]["quantity_on_hand"] == wh_final == 85.0
