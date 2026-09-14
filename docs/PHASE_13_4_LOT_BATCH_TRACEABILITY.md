# Phase 13.4 — Lot / Batch Traceability for Manufacturing Materials

## 1. Problem Overview & Scope

In industrial manufacturing operations, tracking materials solely at an aggregate SKU or warehouse level is insufficient for quality compliance, auditability, warranty recall, and material integrity.

Prior to Phase 13.4:
- Warehouse inventory tracked aggregate SKU quantities per facility (`inventory.quantity`).
- Material issues moved bulk stock into work order holdings (`material_requirement.issued_quantity`).
- However, materials could not be distinguished by specific supplier heat, batch, mill roll, production lot, or expiration date.
- Once issued to a shop floor, multiple lots could be mixed together without discrete accounting.

**Phase 13.4 introduces authoritative Lot / Batch Traceability without compromising or redesigning previous phases:**
1. **Inbound Lot Receipt**: Raw materials are received directly into tracked `MaterialLot` records (with unique lot number, supplier origin, warehouse location, quantity, and optional expiry/manufacturing dates).
2. **Lot-Aware Warehouse Issuance**: When storekeepers fulfill approved material requests or issue stock, they specify the material lot. Warehouse stock and lot balance decrement atomically.
3. **Multi-Lot Floor Holding Isolation**: Each work order tracks physical holdings per lot via `WorkOrderLotHolding`. Multiple lots held for the same component remain isolated and cannot cross-contaminate.
4. **Lot-Specific Floor Operations**: Floor operators consume, return, or report scrap against specific lots. Consumption never double-decrements central warehouse inventory.
5. **End-to-End Lifecycle Traceability API**: Dedicated endpoint `GET /api/v1/manufacturing/lots/{id}/traceability` produces a complete, chronological movement report reconciling initial receipt, current warehouse balance, active floor holdings, consumption, returns, and scrap.

---

## 2. Complete Material Lifecycle with Lot Traceability

```
   [ Supplier Inbound Shipment ]
                 │
                 ▼
     ┌────────────────────────┐
     │      MaterialLot       │  (Initial Receipt: 100 kg)
     │   (Warehouse Balance)  │  (Aggregate Inventory: +100 kg)
     └───────────┬────────────┘
                 │
                 ▼  [ Approved Material Requisition ]
       [ Issue to Work Order ]
                 │
                 ├─────────────────────────────────┐
                 ▼                                 ▼
     ┌────────────────────────┐       ┌────────────────────────┐
     │      MaterialLot       │       │  WorkOrderLotHolding   │
     │   (Warehouse: 80 kg)   │       │  (WO Floor: 20 kg)     │
     └────────────────────────┘       └────────────┬───────────┘
                                                   │
                         ┌─────────────────────────┼─────────────────────────┐
                         ▼                         ▼                         ▼
                  [ CONSUMPTION ]             [ RETURN ]                 [ WASTAGE ]
                         │                         │                         │
                         ▼                         ▼                         ▼
                 Assembled into FG          Returned to WH             Scrapped/Kerf
              WO Holding: -15 kg         WO Holding: -3 kg          WO Holding: -2 kg
              (WH Stock Untouched)       (WH Stock & Lot: +3 kg)    (WH Stock Untouched)
```

### Physical Conservation Equation:
Because material returns are restored directly into the warehouse inventory balance (`current_quantity`), the physical conservation invariant for every lot holds strictly:
$$\text{Initial Received} = \text{Current Warehouse Balance} + \sum \text{Current Floor Holding} + \text{Total Consumed} + \text{Total Wastage}$$

### Movement Dispatch Reconciliation:
For physical stock dispatched to production work orders:
$$\text{Total Issued} = \text{Total Consumed} + \text{Total Returned} + \text{Total Wastage} + \sum \text{Current Floor Holding}$$

---

## 3. Database Schema & Data Models

### 3.1 `MaterialLot` (`material_lots`)
Represents a physical inbound lot or batch of raw material or intermediate inventory.
- `id`: UUID Primary Key
- `organization_id`: Multi-tenant organization scope
- `product_id`: Target component/product FK
- `warehouse_id`: Current storage facility FK
- `supplier_id`: Inbound vendor FK (nullable)
- `lot_number`: Unique lot/batch identifier (string)
- `received_quantity`: Original receipt quantity (float, immutable)
- `current_quantity`: Current unissued warehouse balance (float, mutable via ledger)
- `unit_of_measure`: Standard engineering unit (e.g. `kg`, `meters`, `pieces`)
- `status`: `ACTIVE`, `DEPLETED`, `QUARANTINED`
- `received_at`: Inbound receipt timestamp
- `expiry_at`: Quality expiration / shelf-life limit (nullable)
- `manufacturing_date`: Inbound mill / fabrication date (nullable)
- `notes`: Quality certificates or inspection remarks
- **Unique Constraint**: `(organization_id, product_id, lot_number)`

### 3.2 `WorkOrderLotHolding` (`work_order_lot_holdings`)
Tracks lot-level physical inventory currently staged on the production floor with a work order.
- `id`: UUID Primary Key
- `organization_id`: Multi-tenant organization scope
- `work_order_id`: Assigned work order FK
- `lot_id`: Source material lot FK
- `product_id`: Component product FK
- `issued_quantity`: Total cumulative lot quantity issued to this work order
- `consumed_quantity`: Total quantity consumed into assembly
- `returned_quantity`: Total quantity returned back to warehouse store
- `wastage_quantity`: Total scrap / kerf loss reported
- `unit_of_measure`: Engineering unit
- **Computed Property**: `remaining_holding = issued - consumed - returned - wastage`
- **Unique Constraint**: `(organization_id, work_order_id, lot_id)`

### 3.3 `StockTransaction` Extension
Added optional `lot_id` column and relationship to `stock_transactions`:
- All physical movements (`RECEIPT`, `ISSUE`, `CONSUMPTION`, `RETURN`, `WASTAGE`) retain lot identity when executed against lot-controlled stock.
- Acts as the immutable chronological audit ledger.

---

## 4. API Endpoints Matrix

| Method | Path | Auth / Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/manufacturing/lots/receive` | `ADMIN` | Inbound receipt of raw material batch into a specific lot |
| `GET` | `/api/v1/manufacturing/lots` | `VIEWER+` | Filter lots by product, warehouse, status |
| `GET` | `/api/v1/manufacturing/lots/{id}` | `VIEWER+` | Single lot metadata and warehouse balance |
| `GET` | `/api/v1/manufacturing/lots/{id}/traceability` | `VIEWER+` | End-to-end multi-tier traceability report |
| `GET` | `/api/v1/manufacturing/work-orders/{id}/lots` | `VIEWER+` | List active lot holding balances on a work order |
| `POST` | `/api/v1/manufacturing/material-requests/{id}/issue` | `ADMIN` | Issue approved material request with optional `lot_id` |
| `POST` | `/api/v1/manufacturing/transactions/consume` | `OPERATOR` | Deduct from holding with optional `lot_id` |
| `POST` | `/api/v1/manufacturing/transactions/return` | `OPERATOR` | Return to warehouse with optional `lot_id` |
| `POST` | `/api/v1/manufacturing/transactions/waste` | `OPERATOR` | Log scrap with optional `lot_id` |

---

## 5. Security, RBAC & Multi-Tenant Invariants

1. **Strict Server-Side Context**:
   - `organization_id` and `user_id` are derived exclusively from validated JWT tokens via `get_tenant_context` / `get_auth_tenant_context`.
   - Frontend-supplied tenant IDs or user IDs are strictly ignored.
2. **Role Enforcements**:
   - Only `ADMIN` / storekeeper accounts can receive inbound lots (`receive_material_lot`) or issue stock from warehouse (`issue_material_request`).
   - Floor operators attempting to receive lots are blocked with `HTTP 403 FORBIDDEN`.
   - Operators assigned to a work order can consume, return, and report scrap.
3. **Cross-Tenant Isolation**:
   - Querying or manipulating lots, holdings, or stock transactions across tenant boundaries yields `HTTP 404 NOT_FOUND` or `HTTP 403 FORBIDDEN`.
4. **Approval != Issue Invariant**:
   - Requisition approval creates zero inventory or lot balance movements.
   - Issuance decrements warehouse aggregate inventory and lot balance atomically, simultaneously crediting `WorkOrderLotHolding`.
5. **No Double Deduction**:
   - Consumption from `WorkOrderLotHolding` reduces floor holding. Central warehouse inventory is **not** decremented again.

---

## 6. Verification Summary

- **Backend Integration Tests**: `tests/integration/test_lot_traceability.py` (7/7 passed).
- **Complete Test Suite**: `pytest -q` (86/86 passed, 0 failures, 0 regressions).
- **Frontend Compilation**: `tsc -b` and `vite build` completed cleanly with zero type errors.
- **Alembic Migration**: `a1b2c3d4e5f6_lot_batch_traceability.py` chained correctly from Phase 13.3 (`9c2d3e4f5a6b`), verified via offline SQL generation.
