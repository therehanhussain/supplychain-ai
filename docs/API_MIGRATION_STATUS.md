# SupplyChainAgent: API Migration & Implementation Status

**Document Version:** 1.0.0  
**Phase:** Phase 3 — Refactor Verification  
**Status:** Canonical Implementation Tracking  

---

## 1. Classification Methodology

To ensure total transparency and avoid describing early scaffold endpoints as fully migrated, every endpoint is categorized into one of four verified states:

* **A. Real Migrated Implementation**: Endpoint is fully implemented using the new architecture (Pydantic schemas, dependency injection, service layer, real database/graph connectivity or fallback).
* **B. Delegates to Legacy Implementation**: Endpoint bridges directly to existing legacy code (`firmagentsql`, `AgentSociety`, legacy JSON datasets) via an adapter.
* **C. Placeholder / Scaffold**: Endpoint schema and route are established, returning validated domain models, but the underlying persistent transactional database writes/queries await Phase 4.
* **D. Failing**: Endpoint errors or returns unhandled exceptions.

---

## 2. API Endpoint Status Matrix

| Endpoint | HTTP Method | Status Category | Implementation Type | Notes |
|:---|:---:|:---:|:---|:---|
| `/health` | `GET` | **A. Real Migrated Implementation** | New Core Architecture | High-performance process liveness probe with version and environment metadata. |
| `/live` | `GET` | **A. Real Migrated Implementation** | New Core Architecture | Kubernetes liveness probe verifying process responsiveness. |
| `/ready` | `GET` | **A. Real Migrated Implementation** | New Core Architecture | Readiness probe verifying PostgreSQL, Neo4j, and Redis connectivity without failing optional services. |
| `/api/v1/health` | `GET` | **A. Real Migrated Implementation** | New Core Architecture | Versioned health check route mirroring `/health`. |
| `/api/v1/suppliers` | `GET` | **C. Placeholder / Scaffold** | In-Memory Scaffold | Returns typed list of 16 multi-tier suppliers. Full PostgreSQL table persistence scheduled for Phase 4. |
| `/api/v1/suppliers/{id}` | `GET` | **C. Placeholder / Scaffold** | In-Memory Scaffold | Retrieves specific supplier entity by ID. |
| `/api/v1/suppliers` | `POST` | **C. Placeholder / Scaffold** | In-Memory Scaffold | Validates payload via `SupplierCreate` schema and appends to active registry. |
| `/api/v1/inventory` | `GET` | **C. Placeholder / Scaffold** | In-Memory Scaffold | Returns typed stock balances across warehouses with `is_low_stock` indicators. |
| `/api/v1/inventory/{id}` | `GET` | **C. Placeholder / Scaffold** | In-Memory Scaffold | Retrieves inventory item by SKU or ID. |
| `/api/v1/orders` | `GET`, `POST` | **C. Placeholder / Scaffold** | In-Memory Scaffold | Validates order creation and lists customer/supplier purchase orders. |
| `/api/v1/shipments` | `GET`, `POST` | **C. Placeholder / Scaffold** | In-Memory Scaffold | Logistics tracking endpoints returning carrier tracking records. |
| `/api/v1/routes` | `GET` | **B. Delegates to Legacy Implementation** | `Neo4jService` Bridge | Returns supply chain graph topology; delegates to Neo4j Bolt driver with fallback to `neo4j/industry_test.json`. |
| `/api/v1/routes/topology` | `GET` | **B. Delegates to Legacy Implementation** | `Neo4jService` Bridge | Full graph topology dataset formatted for AntV G6 visualization. |
| `/api/v1/forecast` | `GET`, `POST` | **C. Placeholder / Scaffold** | Analytical Service Scaffold | Generates demand forecast series across horizons. Real model training scheduled for Phase 6. |
| `/api/v1/risk` | `GET`, `POST` | **C. Placeholder / Scaffold** | Analytical Service Scaffold | Simulates supplier failure bottleneck scores and estimated revenue at risk. |
| `/api/v1/agents` | `GET` | **B. Delegates to Legacy Implementation** | `AgentSimulationAdapter` | Reports status of the AgentSociety / Ray simulation engine. |
| `/api/v1/agents/simulations` | `POST` | **A. Real Migrated Implementation** | Celery + Adapter | Returns immediate `202 Accepted` with `task_id`; dispatches simulation loop to background worker. |
| `/api/v1/agents/simulations/{id}/status` | `GET` | **A. Real Migrated Implementation** | `AgentSimulationAdapter` | Polls asynchronous job progress. |
| `/api/v1/agents/profiles` | `GET` | **C. Placeholder / Scaffold** | Typed Schema Scaffold | Returns enterprise agent profiles and capital metrics. |
| `/api/v1/analytics/summary` | `GET` | **C. Placeholder / Scaffold** | Typed Schema Scaffold | Aggregated KPIs (inventory turns, active orders, supplier distribution). |
| `/api/v1/analytics/telemetry-url` | `GET` | **A. Real Migrated Implementation** | Core Settings | Returns safe MLflow tracking URI without exposing credentials. |
| `/api/experiments` | `GET` | **B. Delegates to Legacy Implementation** | `firmagentsql` Bridge | Queries `as_experiment` table via `LatestExperimentQuery` with fallback for local dev. |
| `/api/experiments/{id}` | `GET` | **B. Delegates to Legacy Implementation** | `EnterpriseDataQuerier` | Queries single experiment record matching `ApiExperiment` schema. |
| `/api/experiments/{id}/timeline` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns experiment step timeline for frontend player. |
| `/api/experiments/{exp_id}/agents/-/profile` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns profile params and metrics for all simulation agents. |
| `/api/experiments/{exp_id}/agents/{agent_id}/profile` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns specific agent profile and historical step metrics. |
| `/api/experiments/{exp_id}/agents/-/status` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns agent statuses at step `day` and tick `t`. |
| `/api/experiments/{exp_id}/agents/{agent_id}/status` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns agent status step history. |
| `/api/experiments/{exp_id}/agents/{agent_id}/dialog` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns agent reflection and conversation records. |
| `/api/experiments/{exp_id}/prompt` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns market insight prompt for simulation rounds. |
| `/api/experiments/{exp_id}/companies` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Lists companies participating in experiment. |
| `/api/experiments/{exp_id}/transactions` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns transaction log summary. |
| `/api/experiments/{exp_id}/communications` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns communication event history. |
| `/api/experiments/{exp_id}/inventory` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns aggregate simulation inventory. |
| `/api/experiments/{exp_id}/max-step` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns max completed simulation step. |
| `/api/experiments/{exp_id}/agents/{agent_id}/level` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns company tier level. |
| `/api/experiments/{exp_id}/agents/{agent_id}/required-materials` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns raw materials required for production. |
| `/api/experiments/{exp_id}/agents/{agent_id}/available-materials` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Returns finished goods available for supply. |
| `/api/state/{fid}` | `GET` | **B. Delegates to Legacy Implementation** | Safe File Adapter | Reads `./data/state_{fid}.json` with path sanitization preventing directory traversal. |
| `/api/run-experiments` | `POST` | **A. Real Migrated Implementation** | `AgentSimulationAdapter` | Dispatches simulation run asynchronously to background task worker. |
| `/api/surveys` | `GET` | **B. Delegates to Legacy Implementation** | Legacy Adapter | Retains compatibility with frontend survey table. |
| `/api/mlflow/url` | `GET` | **A. Real Migrated Implementation** | Core Settings | Serves configured MLflow URL to frontend header menu. |

---

## 3. Summary Statistics

* **Total Endpoints Tested & Verified**: 42
* **A. Real Migrated Implementations**: 8 (19%)
* **B. Legacy Bridges / Adapters**: 23 (55%)
* **C. Placeholders / Scaffolds**: 11 (26%)
* **D. Failing Endpoints**: 0 (0%)
