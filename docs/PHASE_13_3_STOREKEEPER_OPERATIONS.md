# Phase 13.3 — Storekeeper & Admin Material Operations

## 1. Problem Overview

In a realistic manufacturing shop floor, material requisition and warehouse issuance cannot be handled as arbitrary quantity edits or automated silent deductions. 

Prior to Phase 13.3:
- Floor employees could create requisitions via the Employee Operations Portal (Phase 13.2).
- However, warehouse storekeepers and supervisors lacked a unified operational queue to review pending requests against live bulk inventory balances, formally approve or reject requisitions, and execute the physical warehouse dispatch.

Phase 13.3 closes this operational loop from both sides:
1. Floor employees submit requisitions for work orders and monitor live status (`PENDING`, `APPROVED`, `REJECTED`, `FULFILLED`).
2. Storekeepers and administrators review requests in a dedicated Queue (`/inventory/requests`), inspect available warehouse stock, approve or reject with audit rationale, and execute the physical stock issuance.
3. Every step enforces strict material conservation, multi-tenant organization boundaries, and server-side RBAC.

---

## 2. Material Request Lifecycle

```
             [ Floor Employee Requisition ]
                           │
                           ▼
                    ┌──────────────┐
                    │   PENDING    │
                    └──────┬───────┘
                           │
             ┌─────────────┴─────────────┐
             │                           │
  [ Storekeeper Rejection ]   [ Storekeeper Approval ]
             │                           │
             ▼                           ▼
      ┌──────────────┐            ┌──────────────┐
      │   REJECTED   │            │   APPROVED   │
      └──────────────┘            └──────┬───────┘
             │                           │
             ✕                           ▼
     (Terminal State)           [ Physical Store Issue ]
                                         │
                                         ▼
                                  ┌──────────────┐
                                  │  FULFILLED   │
                                  └──────────────┘
```

### State Transitions & Validations:
- **`PENDING` $	o$ `APPROVED`**: Administrative decision by authorized administrator or supervisor. **Zero inventory change.**
- **`PENDING` $	o$ `REJECTED`**: Administrative refusal. Requires a mandatory rationale string (e.g. *"Insufficient warehouse lot; alternate SKU required"*). **Zero inventory change.**
- **`APPROVED` $	o$ `FULFILLED`**: Physical stock dispatch from warehouse to floor. Decrements warehouse inventory and increments work order holding.
- **Illegal Transitions (Blocked with `HTTP 400`)**:
  - `PENDING` $	o$ `ISSUE` (Blocked: *"Material request must be approved before issuance."*)
  - `REJECTED` $	o$ `ISSUE` (Blocked: *"Cannot issue a rejected material request."*)
  - `FULFILLED` $	o$ `ISSUE` (Blocked: *"Material request has already been fulfilled."*)
  - `APPROVED` $	o$ `APPROVED` (Blocked: *"Material request is already approved."*)

---

## 3. Core Architectural Rule: Approval $
eq$ Issue

| Phase | Action | Actor | Database Changes | Warehouse Stock | Work Order Holding |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **1. Requisition** | `POST /material-requests` | Operator | `MaterialRequest(status=PENDING)` | **Unchanged** | **Unchanged** |
| **2. Approval** | `POST /material-requests/{id}/approve` | Admin / Storekeeper | `status=APPROVED`, `reviewed_by_user_id`, `AuditLog(REQUEST_APPROVED)` | **Unchanged** | **Unchanged** |
| **3. Rejection** | `POST /material-requests/{id}/reject` | Admin / Storekeeper | `status=REJECTED`, `rejection_reason`, `AuditLog(REQUEST_REJECTED)` | **Unchanged** | **Unchanged** |
| **4. Physical Issue** | `POST /material-requests/{id}/issue` | Admin / Storekeeper | `Inventory.quantity -= Qty`, `MaterialRequirement.issued_quantity += Qty`, `StockTransaction(ISSUE)`, `status=FULFILLED`, `AuditLog(MATERIAL_ISSUED)` | **Decreased** | **Increased** |
| **5. Floor Consumption** | `POST /transactions/consume` | Operator | `MaterialRequirement.consumed_quantity += Qty`, `StockTransaction(CONSUMPTION)` | **Unchanged** (0 double-decrement) | **Decreased** |

---

## 4. End-to-End Inventory Conservation Example

The system maintains exact conservation across the entire requisition and production lifecycle:

$$	ext{issued} = 	ext{consumed} + 	ext{returned} + 	ext{wastage} + 	ext{remaining\_holding}$$

### Step-by-Step Ledger Audit:
1. **Initial Warehouse Balance**: 100 kg Aerospace Aluminum in Storehouse A.
2. **Requisition**: Operator requests 20 kg for Work Order WO-1042.
   - Warehouse: `100 kg` | Holding: `0 kg`
3. **Approval**: Storekeeper approves requisition.
   - Warehouse: `100 kg` | Holding: `0 kg` *(Zero inventory modification)*
4. **Physical Issue**: Storekeeper issues 20 kg to WO-1042.
   - Warehouse: `80 kg` (100 - 20) | Holding: `20 kg` (0 + 20)
   - `StockTransaction(type=ISSUE, qty=20, ref=MATERIAL_REQUEST)`
5. **Consumption**: Operator consumes 12 kg for frame chassis fabrication.
   - Warehouse: `80 kg` *(Store stock untouched!)* | Holding: `8 kg` (20 - 12)
   - `StockTransaction(type=CONSUMPTION, qty=12)`
6. **Surplus Return**: Operator returns 5 kg unused bar stock to Storehouse A.
   - Warehouse: `85 kg` (80 + 5) | Holding: `3 kg` (8 - 5)
   - `StockTransaction(type=RETURN, qty=5)`
7. **Scrap / Wastage**: Operator reports 3 kg thermal deformation offcuts.
   - Warehouse: `85 kg` | Holding: `0 kg` (3 - 3)
   - `StockTransaction(type=WASTAGE, qty=3)`

### Final Reconciliation:
- Total Issued: `20 kg`
- Consumed: `12 kg`
- Returned: `5 kg`
- Wastage: `3 kg`
- Remaining Holding: `0 kg`
- Invariance Formula: `20 = 12 + 5 + 3 + 0` *(Exact mathematical balance)*

---

## 5. Authorization & RBAC

All endpoints derive actor identity and tenant boundary strictly from validated JWT Bearer tokens:
- **`ADMIN` Role**:
  - Full organization oversight.
  - Review, approve, and reject material requisitions.
  - Execute physical warehouse stock issuance.
- **`OPERATOR` Role**:
  - Submit material requisitions for work orders assigned to them.
  - View live status of their requisitions.
  - Forbidden from approving or rejecting requisitions (`HTTP 403 FORBIDDEN_UNAUTHORIZED_APPROVER`).
  - Forbidden from issuing warehouse stock (`HTTP 403 FORBIDDEN_UNAUTHORIZED_ISSUER`).
- **`ANALYST` & `VIEWER` Roles**:
  - Read-only audit access.

---

## 6. Over-Issue & Duplicate Protection

### Over-Issue Guard:
If an approved requisition requests 50 kg, but warehouse inventory only has 30 kg available:
- `POST /api/v1/material-requests/{id}/issue` fails immediately with `HTTP 400 INSUFFICIENT_INVENTORY`.
- **Zero partial deduction** occurs.
- No `StockTransaction` or fraudulent audit log is written.
- Requisition remains in `APPROVED` status until stock is replenished.

### Duplicate Issue Protection:
- Upon issuance, `MaterialRequest.issued_transaction_id` is linked to the created `StockTransaction.id`.
- Any subsequent issue attempts (caused by double clicks, network retries, or browser refreshes) fail safely with `HTTP 400 REQUEST_ALREADY_FULFILLED`.

---

## 7. Organization Isolation

Every query and mutation filters strictly by `organization_id == tenant.organization_id`:
- Users from Organization B cannot view, approve, reject, or issue requisitions belonging to Organization A (`HTTP 404 / 403`).
- Inventory records, work orders, products, and transactions are strictly multi-tenant isolated.

---

## 8. Bidirectional Traceability

Every physical issuance links to its originating requisition:
- `StockTransaction.reference_type = "MATERIAL_REQUEST"`
- `StockTransaction.reference_id = material_request.id`
- `MaterialRequest.issued_transaction_id = stock_transaction.id`
- `MaterialRequest.reviewed_by_user_id = approver.id`

An auditor can trace in seconds:
- **Who requested?** (Operator name and timestamp)
- **Who approved?** (Supervisor name and timestamp)
- **Who issued?** (Storekeeper name and transaction timestamp)
- **Which warehouse?** (Source facility code)
- **Which work order?** (Destination discrete assembly)
- **How much?** (Exact quantity and unit)
- **Why?** (Requisition rationale and approval notes)

---

## 9. API Endpoints

| Method | Endpoint | Role Required | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/material-requests` | `OPERATOR`, `ADMIN` | Employee submits floor requisition for assigned work order. |
| `GET` | `/api/v1/material-requests` | Authenticated | List requisitions (operators see own; admins see org-wide). |
| `GET` | `/api/v1/material-requests/{id}` | Authenticated | Single requisition detail with warehouse stock & holding context. |
| `POST` | `/api/v1/material-requests/{id}/approve` | `ADMIN` | Approve pending requisition. Zero inventory deduction. |
| `POST` | `/api/v1/material-requests/{id}/reject` | `ADMIN` | Reject pending requisition with mandatory reason. |
| `POST` | `/api/v1/material-requests/{id}/issue` | `ADMIN` | Physical issue from warehouse to work order holding. |

---

## 10. Frontend UI Routes

1. **Storekeeper Material Requests Queue**:
   - Route: `/inventory/requests`
   - Component: `<MaterialRequestsQueue />`
   - Features: Summary KPIs (*Pending Review*, *Approved to Issue*, *Fulfilled*, *Rejected*); status filter tabs; search bar; available warehouse stock indicators; inline `[ Approve ]` and `[ Reject ]` actions; `[ Issue Material ]` confirmation modal.
2. **Inventory Dashboard Operational Link**:
   - Route: `/inventory`
   - Component: `<InventoryPage />`
   - Features: `Open Material Requests` shortcut button in page header.
3. **Employee Work Order Requisitions & Status**:
   - Route: `/employee/work-orders/:id`
   - Component: `<WorkOrderDetail />`
   - Features: Dedicated *Requisitions for this Work Order* table displaying live status badges (`PENDING REVIEW`, `APPROVED (Awaiting Issue)`, `FULFILLED / ISSUED`, `REJECTED`). Floor operators have zero approve/reject buttons.

---

## 11. Database Migration

- Migration File: `backend/alembic/versions/9c2d3e4f5a6b_storekeeper_material_requests.py`
- Parent Revision: `8b1e2c3d4e5f`
- DDL Summary: Adds `reviewed_by_user_id`, `rejection_reason`, and `issued_transaction_id` to `material_requests` with foreign keys and indexes. Verified with offline PostgreSQL SQL generation.

---

## 12. Verification & Test Summary

- Integration Tests: `tests/integration/test_storekeeper_operations.py` (6 test suites, 18+ scenarios, 100% pass).
- Full Test Suite: `pytest -q` (79 passed).
- Frontend Build: `npm run build && npx tsc -b` (0 errors).
- Formatting: `git diff --check` (clean).
