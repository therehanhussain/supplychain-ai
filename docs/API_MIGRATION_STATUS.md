# SupplyChainAgent: API Migration & Implementation Status

**Document Version:** 2.0.0  
**Phase:** Phase 4 — Persistence, Multi-Tenancy & Security Verification  
**Status:** Canonical Implementation Tracking  

---

## 1. Classification Methodology

To ensure total transparency and avoid describing early scaffold endpoints as fully migrated, every endpoint is categorized into one of four verified states:

* **A. Real Migrated Implementation**: Endpoint is fully implemented using the new architecture (Pydantic schemas, dependency injection, service layer, real PostgreSQL/SQLAlchemy persistence, JWT auth, or Neo4j driver pooling).
* **B. Delegates to Legacy Implementation**: Endpoint bridges directly to existing legacy code (`firmagentsql`, `AgentSociety`, legacy JSON datasets) via an adapter.
* **C. Placeholder / Scaffold**: Endpoint schema and route are established, returning validated domain models, awaiting deep analytical models (e.g. Monte Carlo simulation or neural demand forecasting).
* **D. Failing**: Endpoint errors or returns unhandled exceptions.

---

## 2. API Endpoint Status Matrix

| Endpoint | HTTP Method | Status Category | Implementation Type | Notes |
|:---|:---:|:---:|:---|:---|
| `/health` | `GET` | **A. Real Migrated** | New Core Architecture | Process liveness probe with version and environment metadata. |
| `/live` | `GET` | **A. Real Migrated** | New Core Architecture | Kubernetes liveness probe verifying process responsiveness. |
| `/ready` | `GET` | **A. Real Migrated** | New Core Architecture | Readiness probe verifying PostgreSQL, Neo4j, and Redis connectivity without failing optional services. |
| `/api/v1/health` | `GET` | **A. Real Migrated** | New Core Architecture | Versioned health check route mirroring `/health`. |
| `/api/v1/auth/register` | `POST` | **A. Real Migrated** | Security / Auth Layer | Registers organization and administrator account with bcrypt hashing and JWT tokens. |
| `/api/v1/auth/login` | `POST` | **A. Real Migrated** | Security / Auth Layer | Authenticates user credentials and issues signed JWT access and refresh tokens. |
| `/api/v1/auth/refresh` | `POST` | **A. Real Migrated** | Security / Auth Layer | Exchanges valid refresh token for renewed access token. |
| `/api/v1/auth/me` | `GET` | **A. Real Migrated** | Security / Auth Layer | Returns profile and RBAC role of currently authenticated user. |
| `/api/v1/suppliers` | `GET` | **A. Real Migrated** | SQLAlchemy + Service Layer | Returns paginated, tenant-scoped suppliers from PostgreSQL. |
| `/api/v1/suppliers/{id}` | `GET` | **A. Real Migrated** | SQLAlchemy + Service Layer | Retrieves single supplier with tenant isolation. |
| `/api/v1/suppliers` | `POST` | **A. Real Migrated** | SQLAlchemy + Service Layer | Creates new supplier under tenant organization with validation. |
| `/api/v1/suppliers/{id}` | `PUT` | **A. Real Migrated** | SQLAlchemy + Service Layer | Updates existing supplier fields with tenant isolation. |
| `/api/v1/suppliers/{id}` | `DELETE` | **A. Real Migrated** | SQLAlchemy + Service Layer | Deletes supplier with strict tenant ownership verification. |
| `/api/v1/inventory` | `GET` | **A. Real Migrated** | SQLAlchemy + Service Layer | Returns stock balances with warehouse and product relations. |
| `/api/v1/inventory/{id}` | `GET` | **A. Real Migrated** | SQLAlchemy + Service Layer | Retrieves inventory item by ID scoped to tenant. |
| `/api/v1/inventory` | `POST` | **A. Real Migrated** | SQLAlchemy + Service Layer | Creates new inventory record with stock quantities. |
| `/api/v1/orders` | `GET`, `POST` | **A. Real Migrated** | SQLAlchemy + Service Layer | Manages purchase orders with order items and tenant scoping. |
| `/api/v1/shipments` | `GET`, `POST` | **A. Real Migrated** | SQLAlchemy + Service Layer | Real-time logistics telemetry and shipment tracking. |
| `/api/v1/routes` | `GET` | **A. Real Migrated** | `Neo4jService` Pooled Driver | Returns multi-tier graph topology with fallback mode and status reporting. |
| `/api/v1/routes/topology` | `GET` | **A. Real Migrated** | `Neo4jService` Pooled Driver | Full graph topology formatted for AntV G6 visualization. |
| `/api/v1/forecast` | `GET`, `POST` | **C. Placeholder / Scaffold** | Analytical Service Scaffold | Generates demand forecast series. Full neural forecasting in Phase 6. |
| `/api/v1/risk` | `GET`, `POST` | **C. Placeholder / Scaffold** | Analytical Service Scaffold | Simulates supplier failure bottleneck scores and revenue at risk. |
| `/api/v1/agents` | `GET` | **B. Delegates to Legacy** | `AgentSimulationAdapter` | Reports status of AgentSociety / Ray simulation engine. |
| `/api/v1/agents/simulations` | `POST` | **A. Real Migrated** | Celery + Adapter | Returns immediate `202 Accepted` with `task_id`; dispatches simulation loop. |
| `/api/v1/agents/simulations/{id}/status` | `GET` | **A. Real Migrated** | `AgentSimulationAdapter` | Polls asynchronous job progress. |
| `/api/v1/agents/profiles` | `GET` | **C. Placeholder / Scaffold** | Typed Schema Scaffold | Returns enterprise agent profiles and capital metrics. |
| `/api/v1/analytics/summary` | `GET` | **C. Placeholder / Scaffold** | Typed Schema Scaffold | Aggregated KPIs (inventory turns, active orders, supplier distribution). |
| `/api/v1/analytics/telemetry-url` | `GET` | **A. Real Migrated** | Core Settings | Returns safe MLflow tracking URI without exposing credentials. |
| `/api/experiments` | `GET` | **B. Delegates to Legacy** | `firmagentsql` Bridge | Queries `as_experiment` table via `LatestExperimentQuery`. |
| `/api/experiments/{id}` | `GET` | **B. Delegates to Legacy** | `EnterpriseDataQuerier` | Queries single experiment record matching `ApiExperiment` schema. |
| `/api/experiments/{id}/timeline` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns experiment step timeline for frontend player. |
| `/api/experiments/{exp_id}/agents/-/profile` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns profile params and metrics for all simulation agents. |
| `/api/experiments/{exp_id}/agents/{agent_id}/profile` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns specific agent profile and historical step metrics. |
| `/api/experiments/{exp_id}/agents/-/status` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns agent statuses at step `day` and tick `t`. |
| `/api/experiments/{exp_id}/agents/{agent_id}/status` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns agent status step history. |
| `/api/experiments/{exp_id}/agents/{agent_id}/dialog` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns agent reflection and conversation records. |
| `/api/experiments/{exp_id}/prompt` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns market insight prompt for simulation rounds. |
| `/api/experiments/{exp_id}/companies` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Lists companies participating in experiment. |
| `/api/experiments/{exp_id}/transactions` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns transaction log summary. |
| `/api/experiments/{exp_id}/communications` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns communication event history. |
| `/api/experiments/{exp_id}/inventory` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns aggregate simulation inventory. |
| `/api/experiments/{exp_id}/max-step` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns max completed simulation step. |
| `/api/experiments/{exp_id}/agents/{agent_id}/level` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns company tier level. |
| `/api/experiments/{exp_id}/agents/{agent_id}/required-materials` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns raw materials required for production. |
| `/api/experiments/{exp_id}/agents/{agent_id}/available-materials` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Returns finished goods available for supply. |
| `/api/state/{fid}` | `GET` | **B. Delegates to Legacy** | Safe File Adapter | Reads `./data/state_{fid}.json` with path sanitization preventing directory traversal. |
| `/api/run-experiments` | `POST` | **A. Real Migrated** | `AgentSimulationAdapter` | Dispatches simulation run asynchronously to background task worker. |
| `/api/surveys` | `GET` | **B. Delegates to Legacy** | Legacy Adapter | Retains compatibility with frontend survey table. |
| `/api/mlflow/url` | `GET` | **A. Real Migrated** | Core Settings | Serves configured MLflow URL to frontend header menu. |

---

## 3. Summary Statistics

* **Total Tracked Endpoints**: 48
* **A. Real Migrated Implementations**: 24 (50%)
* **B. Legacy Bridges / Adapters**: 20 (42%)
* **C. Analytical Placeholders / Scaffolds**: 4 (8%)
* **D. Failing Endpoints**: 0 (0%)
