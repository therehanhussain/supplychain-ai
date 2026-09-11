# Phase 13.1 — Manufacturing Data Model & Material Traceability Foundation

**Application**: SupplyChainAgent — Manufacturing Supply Chain Control Tower
**Architecture Layer**: Domain Data Models, Immutable Stock Ledger, Enterprise RBAC, and Audit Foundation
**Version**: 13.1.0
**Status**: Implemented, Migrated & Verified (67/67 Tests Passing)

---

## 1. Why Manufacturing Operations Are Introduced

Prior to Phase 13.1, SupplyChainAgent operated on a generic distribution inventory model: products were stored in warehouses and could be updated via CRUD operations. While functional for high-level logistics simulations, real-world manufacturing plants operate under rigorous physical and accounting constraints:

1. **Physical Transformation**: In manufacturing, raw materials and components are not merely shipped; they are cut, molded, soldered, assembled, and transformed into finished goods.
2. **Accountability & Custody**: Stock leaves a central store and moves into plant floor custody (a work cell or assembly line) before it is actually consumed. If 100 kg of copper resin is taken, it is no longer in the warehouse rack, but it has not yet become finished wire either.
3. **Scrap, Returns, and Losses**: Industrial processes generate scrap, defective parts, trimming loss, and surplus returns. A realistic control tower must reconcile what was issued against what was actually consumed, returned to store, or lost as wastage.
4. **Regulatory Auditability**: Traceability regulations (such as ISO 9001, AS9100, IATF 16949, and FDA 21 CFR Part 11) mandate that every movement records:
   - **WHO** authorized and handled the material.
   - **WHAT** specific material batch/SKU was transferred.
   - **HOW MUCH** was moved.
   - **WHEN** the physical movement occurred.
   - **WHERE** it originated and where it was placed.
   - **WHY** it was moved (the production or work order authorization).

Phase 13.1 establishes this rock-solid, multi-tenant manufacturing data and transaction backbone in PostgreSQL.

---

## 2. Inventory State vs. Transaction History (The Immutable Ledger Pattern)

A critical design principle enforced in Phase 13.1 is the **separation of current balance from historical movement**:

```
+-------------------------------------------------------------+
|                       CURRENT STATE                         |
|                    Inventory (Snapshots)                    |
|      - warehouse_id + product_id (unique per tenant)        |
|      - quantity (current on-hand balance)                   |
|      - minimum_stock (reorder threshold)                    |
|      - average_daily_consumption                            |
+------------------------------^------------------------------+
                               |
               Atomically mutated via Row Locks
               (SELECT ... FOR UPDATE)
                               |
+------------------------------v------------------------------+
|                    IMMUTABLE LEDGER                         |
|             StockTransaction (Double-Entry Audit)           |
|      - transaction_type (RECEIPT, ISSUE, CONSUMPTION...)    |
|      - quantity, balance_before, balance_after              |
|      - user_id, organization_id, work_order_id              |
|      - source_location, destination_location, reason        |
|      - timestamp (chronological record)                     |
+-------------------------------------------------------------+
```

### Core Invariants:
* **No Direct State Overwrite**: Employees and clients are prohibited from executing arbitrary `PUT /inventory/{id}` quantity overrides.
* **Double-Entry Ledger Integrity**: Every balance modification on `Inventory` creates an immutable `StockTransaction` row recording `balance_before` and `balance_after`.
* **Mathematical Invariant**:
  $$\text{balance\_after} = \text{balance\_before} \pm \text{quantity}$$
* **Current Balance Derivation**: At any point in time, the `Inventory.quantity` must match the net sum of all historical `StockTransaction` records for that product and warehouse:
  $$\text{Current Quantity} = \sum \text{Receipts} + \sum \text{Returns} + \sum \text{Transfers In} - \sum \text{Issues} - \sum \text{Wastage} - \sum \text{Transfers Out} \pm \sum \text{Adjustments}$$

---

## 3. Production Order -> Work Order -> Material Requirement Hierarchy

To support realistic manufacturing routing, Phase 13.1 introduces a hierarchical execution structure:

```
+-------------------------------------------------------------------+
|                          ProductionOrder                          |
|  - order_number: "PO-2026-001"                                    |
|  - product_id: Finished Good SKU ("FG-DRONE-X1")                  |
|  - planned_quantity: 50 units                                     |
|  - status: PLANNED -> RELEASED -> IN_PROGRESS -> COMPLETED        |
+---------------------------------T---------------------------------+
                                  | 1 to N
                                  v
+-------------------------------------------------------------------+
|                             WorkOrder                             |
|  - work_order_number: "WO-2026-001-A"                             |
|  - warehouse_id: Central Warehouse / Plant                        |
|  - production_area: "Assembly Line 2 - Electronics"               |
|  - assigned_user_id: Floor Supervisor UUID                        |
|  - status: PENDING -> IN_PROGRESS -> COMPLETED                    |
+---------------------------------T---------------------------------+
                                  | 1 to N
                                  v
+-------------------------------------------------------------------+
|                        MaterialRequirement                        |
|  - product_id: Component/Raw Material SKU ("COMP-ESC-30A")        |
|  - required_quantity: 200 units                                   |
|  - issued_quantity:   100 units (moved from store to line)        |
|  - consumed_quantity: 95 units (incorporated into assemblies)     |
|  - returned_quantity: 3 units (sent back to store)                |
|  - wastage_quantity:  2 units (damaged during testing)            |
|  - remaining_issued_holding: 0 units                              |
+-------------------------------------------------------------------+
```

---

## 4. Stock Transaction Lifecycle & Types

Phase 13.1 formalizes 10 explicit transaction types in `TransactionType`:

| Transaction Type | Physical Meaning | Warehouse Stock Impact | Holding / WIP Impact | Reason Mandatory? |
| :--- | :--- | :--- | :--- | :--- |
| `RECEIPT` | Inward shipment from supplier or dock | **+ Increases** warehouse stock | None | No |
| `ISSUE` | Dispatch from store to shop floor holding | **- Decreases** warehouse stock | **+ Increases** issued holding | No (linked to WO) |
| `CONSUMPTION` | Part installed into product assembly | None (already out of store) | **- Decreases** issued holding | No (linked to WO) |
| `RETURN` | Surplus material returned from line to store | **+ Increases** warehouse stock | **- Decreases** issued holding | No |
| `TRANSFER_OUT` | Stock leaves source warehouse in-transit | **- Decreases** source stock | None | Optional |
| `TRANSFER_IN` | Stock arrives at destination warehouse | **+ Increases** dest stock | None | Optional |
| `WASTAGE` | Trimmings, process residue, scrap | Decreases store or holding | Decreases holding (if floor) | **YES** |
| `DAMAGE` | Material broken, dropped, or corrupted | **- Decreases** warehouse stock | Decreases holding (if floor) | **YES** |
| `EXPIRY` | Chemical, adhesive, or lot expiration | **- Decreases** warehouse stock | Decreases holding (if floor) | **YES** |
| `ADJUSTMENT` | Physical stock take / cycle count discrepancy | **+- Increases/Decreases** | None | **YES** |

---

## 5. Issue vs. Consumption vs. Return vs. Wastage Reconciliation

A common failure mode in naive inventory systems is conflating **Issue** and **Consumption**. Phase 13.1 strictly separates these two events:

* **ISSUE (Material Store -> Production Floor Custody)**:
  - Material physically exits the warehouse shelving.
  - Warehouse `Inventory.quantity` is decreased immediately so other work orders cannot double-allocate it.
  - `MaterialRequirement.issued_quantity` increases.
  - Material is now in the custody of the work order / assigned employee in `remaining_issued_holding`.

* **CONSUMPTION (Production Floor Custody -> Finished Goods)**:
  - Material is assembled or processed into the final product.
  - Warehouse stock is **NOT** decreased again (it was already deducted at issue).
  - `MaterialRequirement.consumed_quantity` increases.
  - `MaterialRequirement.remaining_issued_holding` decreases.

### The Reconciliation Conservation Law:
At any stage of production or upon Work Order closing:
$$\text{issued\_quantity} = \text{consumed\_quantity} + \text{returned\_quantity} + \text{wastage\_quantity} + \text{remaining\_issued\_holding}$$

$$\text{remaining\_issued\_holding} = \text{issued\_quantity} - (\text{consumed\_quantity} + \text{returned\_quantity} + \text{wastage\_quantity}) \ge 0$$

The system strictly rejects any consumption, return, or shop-floor scrap event where:
$$\text{consumed} + \text{returned} + \text{wastage} > \text{issued}$$

---

## 6. Inventory Consistency Rules & Atomicity

To guarantee zero negative stock and eliminate race conditions under concurrent operations, all inventory balance changes follow strict ACID transactional controls:

1. **Pessimistic Locking**: All balance checks and updates perform a pessimistic database lock:
   ```sql
   SELECT * FROM inventories
   WHERE warehouse_id = :wid AND product_id = :pid AND organization_id = :org_id
   FOR UPDATE;
   ```
2. **Strict Non-Negative Guard**: If a requested operation causes `Inventory.quantity - deduction < 0`, the transaction raises `InsufficientStockException (HTTP 400)` and aborts before any state is written.
3. **Atomic Commit**: The `Inventory` row update, the `MaterialRequirement` tracking update, the `StockTransaction` ledger insert, and the `AuditLog` row generation occur inside the exact same database transaction block. If any step fails, all operations roll back completely.
4. **Mandatory Audit Logging**: In addition to `StockTransaction`, every action emits a structured `AuditLog` record containing IP address, user agent, actor ID, action verb, and entity identifier for platform-wide compliance.

---

## 7. Role-Based Access Control (RBAC) & Permission Matrix

Permissions are enforced at the API route layer via FastAPI dependency injection:
`Security(require_permission(Permissions.INVENTORY_ISSUE))`

| Role | Receive Stock | Issue to Floor | Consume on WO | Return to Store | Waste / Damage | Transfer Warehouses | Cycle Count Adjust | Manage Prod Orders |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Admin** | YES | YES | YES | YES | YES | YES | YES | YES |
| **Manager** | YES | YES | YES | YES | YES | YES | YES | YES |
| **Analyst** | NO (View) | NO (View) | NO (View) | NO (View) | NO (View) | NO (View) | NO (View) | NO (View) |
| **Viewer** | NO (View) | NO (View) | NO (View) | NO (View) | NO (View) | NO (View) | NO (View) | NO (View) |

---

## 8. Multi-Tenant Organization Isolation

Multi-tenant isolation is enforced at the data model and repository layers:
1. **Never Trust Client Body Context**: The client cannot specify `organization_id` or `user_id` in the request body to impersonate another tenant or user.
2. **Context Derivation**: Both `user_id` and `organization_id` are derived exclusively from the verified JWT bearer token via `get_current_user` and `get_current_org_id`.
3. **Tenant Query Filtering**: Every query executed by `MaterialService`, `StockTransactionRepository`, and `ManufacturingRepositories` includes:
   ```python
   filter(Model.organization_id == current_user.organization_id)
   ```
4. **Foreign Key Integrity**: Work orders, production orders, inventory records, and stock transactions belonging to Organization A can never be linked to or modified by Organization B.

---

## 9. Reorder Data Foundation

While automated AI reordering and supplier auto-replenishment are scheduled for subsequent phases, Phase 13.1 establishes the deterministic data foundation:

* **Product Level**:
  - `material_type`: Categorizes item as `RAW_MATERIAL`, `COMPONENT`, `FINISHED_GOOD`, or `OTHER`.
  - `unit_of_measure`: Standardizes dimensions (`kg`, `g`, `meter`, `liter`, `piece`, `box`, `pallet`).
  - `preferred_supplier_id`: Links the preferred source supplier for replenishment.
* **Inventory Level**:
  - `minimum_stock`: Deterministic safety buffer threshold.
  - `average_daily_consumption`: Moving rate of shop floor consumption.
* **Deterministic Reorder Flag**:
  $$\text{Reorder Recommended} \iff \text{quantity} \le \text{minimum\_stock}$$

---

## 10. Validated Material Traceability Scenarios (Examples A - G)

The test suite validates realistic end-to-end industrial scenarios:

### Example A: Inward Material Receipt
* **Action**: 1,000 kg of Aluminum Alloy received from supplier.
* **Ledger Record**: Type `RECEIPT`, quantity `+1000`, `balance_before: 0`, `balance_after: 1000`.
* **State**: Warehouse stock = `1000 kg`.

### Example B: Material Issue to Work Order
* **Action**: 100 kg issued from store to Assembly Line 1 for `WO-2026-001`.
* **Ledger Record**: Type `ISSUE`, quantity `100`, `balance_before: 1000`, `balance_after: 900`.
* **State**: Warehouse stock = `900 kg`. Work order holding = `100 kg`.

### Example C: Actual Production Consumption
* **Action**: 95 kg processed into finished airframe parts.
* **Ledger Record**: Type `CONSUMPTION`, quantity `95`, linked to `WO-2026-001`.
* **State**: Warehouse stock = `900 kg` (unchanged). Work order holding = `5 kg`.

### Example D: Surplus Return to Store
* **Action**: 3 kg unused cut-off returned to warehouse shelving.
* **Ledger Record**: Type `RETURN`, quantity `3`, `balance_before: 900`, `balance_after: 903`.
* **State**: Warehouse stock = `903 kg`. Work order holding = `2 kg`.

### Example E: Shop-Floor Scrap / Wastage
* **Action**: 2 kg contaminated during milling; logged with reason `"Contaminated during milling process"`.
* **Ledger Record**: Type `WASTAGE`, quantity `2`, reason recorded.
* **Reconciliation Check**:
  $$\text{Issued (100)} = \text{Consumed (95)} + \text{Returned (3)} + \text{Wastage (2)} + \text{Holding (0)}$$
  *Status*: Fully reconciled ($100 = 100$). Holding balance = $0$.

### Example F: Mandatory Reason Validation
* Attempting `ADJUSTMENT`, `WASTAGE`, `DAMAGE`, or `EXPIRY` without a descriptive reason string immediately raises `HTTP 400 Bad Request` (`"Reason is required"`).

### Example G: Inter-Warehouse Stock Transfer
* **Action**: Transfer 150 kg from Central Store to Plant Satellite Depot.
* **Source Ledger**: `TRANSFER_OUT`, quantity `150`, source stock drops from `903` to `753`.
* **Destination Ledger**: `TRANSFER_IN`, quantity `150`, destination stock increases from `0` to `150`.
* **Audit Trail**: Linked across both warehouses with transfer reference ID.

---

## 11. Scope Intentionally Deferred to Phase 13.2

To preserve system stability and follow modular architectural progression, the following features are intentionally deferred to Phase 13.2:

1. **Frontend Material Movement UI**: Employee material issue forms, scrap declaration modals, and visual WIP dashboards.
2. **Real-Time WebSockets**: Live floor dispatch notifications.
3. **Automated Purchase Order Triggering**: Automated generation of `Order` rows upon `quantity <= minimum_stock`.
4. **Barcode & QR Generation**: Scanning physical lots with mobile or handheld devices.
5. **Multi-Step Quality Inspection Workflows**: Quarantine hold and laboratory release gates prior to `RECEIPT` availability.
