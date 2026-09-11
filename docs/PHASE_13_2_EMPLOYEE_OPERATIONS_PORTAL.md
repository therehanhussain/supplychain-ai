# Phase 13.2 — Employee Operations Portal Documentation

**Application**: SupplyChainAgent — Manufacturing Supply Chain Control Tower
**Architecture Layer**: Employee Operations Portal (Backend REST API + Frontend UI/UX)
**Version**: 13.2.0
**Status**: Implemented, Verified, and Cleanly Tested (73/73 Tests Passing)

---

## 1. Objective

Phase 13.2 builds a practical, responsive, touch-friendly **Employee Operations Portal** directly on top of the Phase 13.1 manufacturing material traceability foundation.

Prior to this phase, shop-floor operators lacked dedicated workflows for interacting with their assigned jobs, consuming issued materials, returning surplus inventory, reporting scrap, or requesting additional components. Phase 13.2 bridges this gap with an intuitive interface designed for industrial operators, while preserving strict accounting invariants and non-negative stock controls.

---

## 2. Architecture Overview

The Employee Operations Portal operates as a dedicated subsystem within the unified SupplyChainAgent architecture:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       SHOP FLOOR OPERATOR UI                            │
│                                                                         │
│   /employee             /employee/work-orders   /employee/activity      │
│   (Dashboard & KPIs)    (Assigned Jobs & BOM)   (Personal Audit Trail)  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                 Authenticated HTTPS Requests (Bearer JWT)
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FASTAPI MANUFACTURING ROUTER                        │
│                /api/v1/manufacturing/* & /api/v1/*                      │
│                                                                         │
│  - get_auth_tenant_context (extracts user_id, org_id from JWT)          │
│  - Work order assignment authorization guards                           │
│  - Idempotency key tracking (prevents duplicate submissions)            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 DOMAIN SERVICE: MaterialTraceabilityService             │
│                                                                         │
│  - Atomically mutates Inventory with row-level locks (FOR UPDATE)       │
│  - Enforces Conservation Invariant:                                     │
│      Issued = Consumed + Returned + Wastage + Remaining Holding         │
│  - Records immutable StockTransaction ledger entries                    │
│  - Emits platform-wide AuditLog records                                 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                  POSTGRESQL RELATIONAL PERSISTENCE                      │
│  - users & organizations (Multi-Tenant Isolation)                       │
│  - work_orders & production_orders (Hierarchical Jobs)                  │
│  - material_requirements (Floor Staging Balances)                       │
│  - material_requests (Floor Requisitions)                               │
│  - stock_transactions (Double-Entry Audit Ledger)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Primary Employee Workflows

1. **Employee Dashboard (`/employee`)**:
   - Operator shift summary.
   - Live KPI cards: Active Jobs, Materials in Holding with Operator, Today's Consumed, Today's Returned, Today's Scrap/Loss.
   - Quick job table with direct links to active assemblies.
   - Recent personal movement history.

2. **My Work Orders (`/employee/work-orders`)**:
   - Filterable view of jobs assigned to the authenticated employee (`assigned_user_id == current_user.id`).
   - Displays Work Order #, Production Order #, Assembly Name/SKU, Production Line, Planned Qty, and Material Status.
   - Search by order number, SKU, or production bay.

3. **Work Order Details & Materials (`/employee/work-orders/:id`)**:
   - Header with target assembly, production line, planned quantity, and supervisor notes.
   - Interactive Materials Table displaying:
     - Required Quantity
     - Issued Quantity (dispatched from store to line)
     - Consumed Quantity (used in assembly)
     - Returned Quantity (sent back to store)
     - Wastage / Scrap Quantity (process losses)
     - **Holding Available to Use** (`remaining_issued_holding`)
   - Context-aware action buttons enabled only when holding is positive.

4. **Consume Material (Modal Form)**:
   - Records material incorporated into the final assembly.
   - Decreases floor holding balance.
   - **Does NOT double-decrement warehouse inventory.**

5. **Return Surplus Material (Modal Form)**:
   - Returns unused material from floor holding back to central store shelving.
   - Decreases floor holding balance; increments central warehouse inventory.

6. **Report Scrap / Wastage (Modal Form)**:
   - Records trimmings, kerf loss, or damaged materials.
   - Enforces mandatory reason string for compliance.
   - Decreases floor holding balance; does NOT touch central warehouse inventory.

7. **Request Additional Material (Modal Form)**:
   - Submits formal requisition (`MaterialRequest`) to the store room without altering balances.
   - Storekeeper reviews and issues stock via standard `ISSUE` transaction.

8. **My Activity Ledger (`/employee/activity`)**:
   - Operator's personal audit trail.
   - Filterable by transaction type (`CONSUMPTION`, `RETURN`, `WASTAGE`, `RECEIPT`, `ISSUE`).
   - Displays timestamps, material SKUs, quantities, work order references, and reasons.

---

## 4. Business Semantics: Issue vs. Consumption

| Dimension | `ISSUE` | `CONSUMPTION` |
| :--- | :--- | :--- |
| **Physical Origin** | Central Warehouse / Raw Material Store | Shop Floor Staging / Work Cell Holding |
| **Physical Destination** | Shop Floor Work Order Custody | Finished Product Assembly |
| **Warehouse Inventory Impact** | **Decrements** warehouse inventory balance | **Zero impact** on warehouse inventory |
| **Holding Balance Impact** | **Increments** `remaining_issued_holding` | **Decrements** `remaining_issued_holding` |
| **Executed By** | Storekeeper / Material Handler | Shop Floor Operator / Assembly Technician |

---

## 5. End-to-End Material Flow Lifecycle

```
[Storekeeper]                                              [Floor Operator]
      │                                                           │
      │ 1. Inward Receipt (Supplier -> Warehouse Stock)           │
      │                                                           │
      │ 2. Issue to Work Order (Warehouse Stock -> Holding)       │
      │──────────────────────────────────────────────────────────>│
      │                                                           │
      │                                                           │ 3. Consume Material (Holding -> Assembly)
      │                                                           │    (No warehouse decrement!)
      │                                                           │
      │                                                           │ 4. Report Scrap (Holding -> Scrap)
      │                                                           │    (Mandatory compliance reason)
      │                                                           │
      │ 5. Return Surplus (Holding -> Warehouse Stock)            │
      │<──────────────────────────────────────────────────────────│
      │    (Warehouse stock restored!)                            │
      │                                                           │
      ▼                                                           ▼
                      [INVARIANT FULLY RECONCILED]
           Issued = Consumed + Returned + Wastage + Holding
```

---

## 6. Authentication and Authorization

1. **Token Identity Source of Truth**:
   - User identity is extracted strictly from the JWT Bearer token (`sub: user_id`, `claims: org_id, role`).
   - The frontend cannot spoof `user_id` or `organization_id` via route parameters or request bodies.
2. **Strict Assignment Guards**:
   - Operators can only view work orders where `assigned_user_id == current_user.id` and `organization_id == current_user.organization_id`.
   - Attempts by an operator to access or mutate another operator's work order are rejected with `HTTP 403 Forbidden` (`NOT_ASSIGNED_TO_WORK_ORDER`).
   - Administrators retain supervisory oversight and can inspect or manage all orders across their organization.
3. **Unauthenticated Access Denial**:
   - All employee endpoints use `get_auth_tenant_context`, returning `HTTP 401 Unauthorized` if credentials are missing or expired.

---

## 7. Multi-Tenant Organization Isolation

- Tenant boundary is determined by `current_user.organization_id`.
- All database queries for work orders, material requirements, material requests, and stock transactions filter strictly by `Model.organization_id == current_user.organization_id`.
- A user from Tenant A cannot see, query, or execute transactions against work orders or inventory belonging to Tenant B (returns `403` or `404`).

---

## 8. API Endpoints Matrix

Mounted under `/api/v1/manufacturing` (and `/api/v1`):

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `GET` | `/api/v1/manufacturing/my-work-orders` | List work orders assigned to current operator | Yes |
| `GET` | `/api/v1/manufacturing/work-orders/{id}` | Detailed work order view with materials & assembly info | Yes |
| `GET` | `/api/v1/manufacturing/work-orders/{id}/materials` | List material requirements & holding balances | Yes |
| `GET` | `/api/v1/manufacturing/employee/dashboard-stats` | Aggregated shift KPIs (active jobs, holding, today's sums) | Yes |
| `GET` | `/api/v1/manufacturing/employee/activity` | Personal transaction history for authenticated operator | Yes |
| `POST` | `/api/v1/manufacturing/material-requests` | Create formal material requisition | Yes |
| `GET` | `/api/v1/manufacturing/material-requests` | List requisitions for work order or operator | Yes |
| `POST` | `/api/v1/manufacturing/transactions/consume` | Consume material from work order holding | Yes |
| `POST` | `/api/v1/manufacturing/transactions/return` | Return surplus material from holding to warehouse | Yes |
| `POST` | `/api/v1/manufacturing/transactions/waste` | Log scrap/wastage from holding with reason | Yes |

---

## 9. Frontend Routes

| Route | Page Component | Purpose |
| :--- | :--- | :--- |
| `/employee` | [`EmployeeDashboard.tsx`](file:///frontend/src/pages/Employee/EmployeeDashboard.tsx) | Operator hub with KPIs, active jobs, and quick actions |
| `/employee/work-orders` | [`MyWorkOrders.tsx`](file:///frontend/src/pages/Employee/MyWorkOrders.tsx) | Filterable table of assigned manufacturing jobs |
| `/employee/work-orders/:id` | [`WorkOrderDetail.tsx`](file:///frontend/src/pages/Employee/WorkOrderDetail.tsx) | Deep work order detail with live BOM and action modals |
| `/employee/activity` | [`MyActivity.tsx`](file:///frontend/src/pages/Employee/MyActivity.tsx) | Personal chronological ledger of material movements |

---

## 10. Inventory Invariants & Idempotency

1. **Non-Negative Stock Guard**:
   - Deductions that would drive inventory below zero are rejected with `HTTP 400 Bad Request` (`INSUFFICIENT_INVENTORY`).
2. **Holding Upper-Bound Guard**:
   - `quantity <= remaining_issued_holding` for all consumption, return, and scrap actions.
3. **Double-Decrement Prevention**:
   - Consumption and shop-floor scrap do not mutate `Inventory.quantity`.
4. **Idempotent Transaction Handling**:
   - Mutation endpoints support an optional `idempotency_key` (persisted in `StockTransaction.reference_id`).
   - If a client double-clicks or retries after a network drop, the backend detects the existing transaction and returns the original record without duplicating balance changes.

---

## 11. Test Coverage Summary

Full regression test suite: **73 tests passing (100%)**.

Integration test suite [`tests/integration/test_employee_operations.py`](file:///tests/integration/test_employee_operations.py) validates:
- **Test A**: Operator can query assigned work orders.
- **Test B**: Operator cannot query or operate on another operator's work order (`HTTP 403`).
- **Test C**: Operator can consume material within holding quantity.
- **Test D**: Over-consumption is rejected (`HTTP 400`).
- **Test E**: Operator can return surplus material within holding quantity.
- **Test F**: Over-return is rejected (`HTTP 400`).
- **Test G**: Operator can report scrap with mandatory reason.
- **Test H**: Scrap reporting beyond holding quantity is rejected (`HTTP 400`).
- **Test I**: Multi-tenant organization isolation is strictly enforced.
- **Test J**: Unauthenticated requests are rejected (`HTTP 401`).
- **Test K**: Actions persist `StockTransaction` with snapshot balances.
- **Test L**: Actions emit `AuditLog` records containing authenticated actor ID.
- **Test M**: Inventory is NOT double-decremented (verified warehouse stock remains exact).
- **Test N**: Repeated submissions with idempotency keys do not produce duplicate stock mutations.
- **Test O**: Complete reconciliation verified: $20 = 12 	ext{ consumed} + 5 	ext{ returned} + 3 	ext{ scrap} + 0 	ext{ holding}$.

---

## 12. Known Limitations

1. **No Hardware Scanners**: Barcode and QR code scanning are not integrated; material selection uses SKU/name dropdowns and identifiers.
2. **No Offline PWA Sync**: Requires network connectivity to the Render backend API.
3. **No Multi-Stage Quality Gates**: Scrap is logged directly without quarantine hold inspections.

---

## 13. Future Phase 13.3 Scope (Deferred)

The following items are deferred to Phase 13.3:
- Barcode/QR scanning for physical lot identifiers.
- Multi-step QA quarantine and lot release inspection workflows.
- Floor dispatch notifications and operator-supervisor messaging.
- Mobile PWA offline synchronization.
