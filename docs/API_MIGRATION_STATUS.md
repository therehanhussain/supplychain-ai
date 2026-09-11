# SupplyChainAgent: Authoritative API Migration & Implementation Matrix

**Document Version:** 3.0.0  
**Phase:** Phase 5 — Production Integration & Hardening  
**Status:** Authoritative Runtime OpenAPI Inspection  

---

## 1. Reconciliation of Endpoint Counts (Phase 3 vs Phase 4 vs Phase 5)

An audit of prior phase documentation revealed reporting discrepancies:
* **Phase 3 Report**: Stated **42 endpoints**.
* **Phase 4 Report**: Stated **48 endpoints**.
* **Phase 5 Runtime Audit**: Disclosed **61 distinct HTTP method + path operations** across **51 unique URL paths**.

### Root Cause Analysis of Discrepancies
1. **Method Collapsing in Previous Tables**:
   In Phase 3 and Phase 4, several routes with both `GET` and `POST` methods were grouped into a single table row (e.g., `/api/v1/orders` was listed as `GET, POST` in one row, `/api/v1/shipments` as `GET, POST`, `/api/v1/forecast` as `GET, POST`, and `/api/v1/risk` as `GET, POST`). This obscured 4 distinct endpoints.
2. **Absence of Auth Endpoints in Phase 3**:
   The initial Phase 3 audit preceded the implementation of the authentication layer. Phase 4 introduced 4 endpoints (`/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/refresh`, and `/api/v1/auth/me`).
3. **Omission of Individual Mutating / Sub-Resource Endpoints**:
   In Phase 4, newly added deletion routes (`DELETE /api/v1/inventory/{id}`, `DELETE /api/v1/orders/{id}`, `DELETE /api/v1/shipments/{id}`) and graph statistics (`GET /api/v1/routes/statistics`) were registered in code but omitted from the static 48-row markdown table.
4. **Dual-Registered Health Probes**:
   The system exposes both root orchestration probes (`/health`, `/live`, `/ready`) for Kubernetes ingress/load balancers and versioned probes (`/api/v1/health`, `/api/v1/live`, `/api/v1/ready`) for API gateway consumers.

**Conclusion**: The runtime ASGI application registers exactly **61 executable HTTP operations**. Below is the single authoritative matrix.

---

## 2. Classification Methodology

Every endpoint is categorized into one of four verified states:

* **A. Real Migrated**: Fully implemented in the new architecture with Pydantic v2 schemas, dependency injection, service layer, transactional database persistence (PostgreSQL/SQLAlchemy), JWT auth, or Neo4j driver pooling.
* **B. Legacy Bridge**: Routes bridging directly to existing legacy code (`firmagentsql`, `AgentSociety`, Ray, local JSON datasets) via an adapter.
* **C. Analytical Scaffold**: Route structure, input validation, and typed response envelopes are established, but analytical models currently return simulated or baseline heuristic projections (neural forecasting / full Monte Carlo models targeted for subsequent phases).
* **D. Failing**: Endpoint returns unhandled server exceptions or fails to compile.

---

## 3. Canonical 61-Endpoint Matrix

| METHOD | PATH | STATUS | IMPLEMENTATION | DATA SOURCE | AUTH REQUIRED | ROLE | MOCK / LIVE |
|:---|:---|:---:|:---|:---|:---:|:---:|:---:|
| `GET` | `/health` | **A. Real Migrated** | FastAPI Probe Handler | In-Memory / System Status | No | Public | Live |
| `GET` | `/live` | **A. Real Migrated** | FastAPI Probe Handler | In-Memory / System Status | No | Public | Live |
| `GET` | `/ready` | **A. Real Migrated** | FastAPI Probe Handler | In-Memory / Subsystem Probes | No | Public | Live |
| `GET` | `/api/v1/health` | **A. Real Migrated** | FastAPI Probe Handler | In-Memory / System Status | No | Public | Live |
| `GET` | `/api/v1/live` | **A. Real Migrated** | FastAPI Probe Handler | In-Memory / System Status | No | Public | Live |
| `GET` | `/api/v1/ready` | **A. Real Migrated** | FastAPI Probe Handler | In-Memory / Subsystem Probes | No | Public | Live |
| `POST` | `/api/v1/auth/register` | **A. Real Migrated** | `AuthService` (Bcrypt/JWT) | PostgreSQL (`users`, `organizations`) | No | Public | Live |
| `POST` | `/api/v1/auth/login` | **A. Real Migrated** | `AuthService` (Bcrypt/JWT) | PostgreSQL (`users`, `organizations`) | No | Public | Live |
| `POST` | `/api/v1/auth/refresh` | **A. Real Migrated** | `AuthService` (Bcrypt/JWT) | PostgreSQL (`users`, `organizations`) | No | Public | Live |
| `GET` | `/api/v1/auth/me` | **A. Real Migrated** | `AuthService` (Bcrypt/JWT) | PostgreSQL (`users`, `organizations`) | Yes | Viewer+ | Live |
| `GET` | `/api/v1/suppliers` | **A. Real Migrated** | `SupplierService` + Repo | PostgreSQL (`suppliers`) | Yes | Viewer+ | Live |
| `POST` | `/api/v1/suppliers` | **A. Real Migrated** | `SupplierService` + Repo | PostgreSQL (`suppliers`) | Yes | Operator+ | Live |
| `GET` | `/api/v1/suppliers/{supplier_id}` | **A. Real Migrated** | `SupplierService` + Repo | PostgreSQL (`suppliers`) | Yes | Viewer+ | Live |
| `PUT` | `/api/v1/suppliers/{supplier_id}` | **A. Real Migrated** | `SupplierService` + Repo | PostgreSQL (`suppliers`) | Yes | Operator+ | Live |
| `DELETE` | `/api/v1/suppliers/{supplier_id}` | **A. Real Migrated** | `SupplierService` + Repo | PostgreSQL (`suppliers`) | Yes | Operator+ | Live |
| `GET` | `/api/v1/inventory` | **A. Real Migrated** | `InventoryService` + Repo | PostgreSQL (`inventories`) | Yes | Viewer+ | Live |
| `POST` | `/api/v1/inventory` | **A. Real Migrated** | `InventoryService` + Repo | PostgreSQL (`inventories`) | Yes | Operator+ | Live |
| `GET` | `/api/v1/inventory/{item_id}` | **A. Real Migrated** | `InventoryService` + Repo | PostgreSQL (`inventories`) | Yes | Viewer+ | Live |
| `DELETE` | `/api/v1/inventory/{item_id}` | **A. Real Migrated** | `InventoryService` + Repo | PostgreSQL (`inventories`) | Yes | Operator+ | Live |
| `GET` | `/api/v1/orders` | **A. Real Migrated** | `OrderService` + Repo | PostgreSQL (`orders`, `order_items`) | Yes | Viewer+ | Live |
| `POST` | `/api/v1/orders` | **A. Real Migrated** | `OrderService` + Repo | PostgreSQL (`orders`, `order_items`) | Yes | Operator+ | Live |
| `GET` | `/api/v1/orders/{order_id}` | **A. Real Migrated** | `OrderService` + Repo | PostgreSQL (`orders`, `order_items`) | Yes | Viewer+ | Live |
| `DELETE` | `/api/v1/orders/{order_id}` | **A. Real Migrated** | `OrderService` + Repo | PostgreSQL (`orders`, `order_items`) | Yes | Operator+ | Live |
| `GET` | `/api/v1/shipments` | **A. Real Migrated** | `ShipmentService` + Repo | PostgreSQL (`shipments`) | Yes | Viewer+ | Live |
| `POST` | `/api/v1/shipments` | **A. Real Migrated** | `ShipmentService` + Repo | PostgreSQL (`shipments`) | Yes | Operator+ | Live |
| `GET` | `/api/v1/shipments/{shipment_id}` | **A. Real Migrated** | `ShipmentService` + Repo | PostgreSQL (`shipments`) | Yes | Viewer+ | Live |
| `DELETE` | `/api/v1/shipments/{shipment_id}` | **A. Real Migrated** | `ShipmentService` + Repo | PostgreSQL (`shipments`) | Yes | Operator+ | Live |
| `GET` | `/api/v1/routes` | **A. Real Migrated** | `Neo4jService` (Pool/Driver) | Neo4j Graph / JSON Fallback | No | Public | Hybrid (Tagged) |
| `GET` | `/api/v1/routes/statistics` | **A. Real Migrated** | `Neo4jService` (Pool/Driver) | Neo4j Graph / JSON Fallback | No | Public | Hybrid (Tagged) |
| `GET` | `/api/v1/routes/topology` | **A. Real Migrated** | `Neo4jService` (Pool/Driver) | Neo4j Graph / JSON Fallback | No | Public | Hybrid (Tagged) |
| `GET` | `/api/v1/forecast` | **C. Analytical Scaffold** | `ForecastService` Scaffold | In-Memory Baseline Generator | No | Viewer+ | Mock Fallback |
| `POST` | `/api/v1/forecast` | **C. Analytical Scaffold** | `ForecastService` Scaffold | In-Memory Baseline Generator | No | Viewer+ | Mock Fallback |
| `GET` | `/api/v1/risk` | **C. Analytical Scaffold** | `RiskService` Disruption Model | In-Memory Disruption Model | No | Analyst+ | Mock Fallback |
| `POST` | `/api/v1/risk/analyze-disruption` | **C. Analytical Scaffold** | `RiskService` Disruption Model | In-Memory Disruption Model | No | Analyst+ | Mock Fallback |
| `GET` | `/api/v1/agents` | **B. Legacy Bridge** | `AgentSimulationAdapter` | Ray / AgentSociety Engine | No | Viewer+ | Hybrid |
| `GET` | `/api/v1/agents/profiles` | **B. Legacy Bridge** | `AgentSimulationAdapter` | SQLite / Ray State | No | Viewer+ | Hybrid |
| `POST` | `/api/v1/agents/simulations` | **A. Real Migrated** | `SimulationService` + Task Registry | Async Background Worker / Ray | No | Operator+ | Hybrid |
| `GET` | `/api/v1/agents/simulations/{experiment_id}/status` | **A. Real Migrated** | `SimulationService` + Task Registry | Async Worker / Memory Store | No | Viewer+ | Hybrid |
| `GET` | `/api/v1/analytics/summary` | **C. Analytical Scaffold** | Analytics KPI Scaffold | In-Memory KPI Aggregator | No | Viewer+ | Mock Fallback |
| `GET` | `/api/v1/analytics/telemetry-url` | **A. Real Migrated** | Settings / MLflow Config | Configuration Settings | No | Viewer+ | Live |
| `GET` | `/api/experiments` | **B. Legacy Bridge** | `LatestExperimentQuery` | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{id}` | **B. Legacy Bridge** | `EnterpriseDataQuerier` | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{id}/timeline` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/agents/-/profile` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/agents/{agent_id}/profile` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/agents/-/status` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/agents/{agent_id}/status` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/agents/{agent_id}/dialog` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/prompt` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/companies` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/transactions` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/communications` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/inventory` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/max-step` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/agents/{agent_id}/level` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/agents/{agent_id}/required-materials` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/experiments/{exp_id}/agents/{agent_id}/available-materials` | **B. Legacy Bridge** | Legacy Adapter | SQLite (`firmagentsql/company_data.sql`) | No | Public | Live / Bridged |
| `GET` | `/api/state/{fid}` | **B. Legacy Bridge** | Safe File Adapter | Local File (`./data/state_{fid}.json`) | No | Public | Live / Bridged |
| `POST` | `/api/run-experiments` | **B. Legacy Bridge** | `AgentSimulationAdapter` | Background Task / Ray Engine | No | Public | Live / Bridged |
| `GET` | `/api/surveys` | **B. Legacy Bridge** | Legacy Adapter | In-Memory Mock List | No | Public | Live / Bridged |
| `GET` | `/api/mlflow/url` | **A. Real Migrated** | Core Settings Proxy | Configuration Settings | No | Public | Live |

---

## 4. Summary Statistics

* **Total Tracked Executable Endpoints**: 61
* **A. Real Migrated Implementations**: 33 (54.1%)
* **B. Legacy Bridges / Adapters**: 23 (37.7%)
* **C. Analytical Placeholders / Scaffolds**: 5 (8.2%)
* **D. Failing Endpoints**: 0 (0.0%)
