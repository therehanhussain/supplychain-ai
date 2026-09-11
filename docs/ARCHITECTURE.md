# SupplyChainAgent: Target Production SaaS Architecture

**Document Version:** 1.1.0  
**Phase:** Phase 3 — Refactor & Migration Scaffold  
**Status:** Phase 3 Scaffold & Health Verification Complete  

---

## 1. Architectural Vision & Core Principles

The goal of this architectural evolution is to transform **SupplyChainAgent** from an experimental multi-agent research simulator into a scalable, secure, multi-tenant Software-as-a-Service (SaaS) supply chain decision intelligence platform.

### Core Architectural Directives:
1. **Preserve Domain Intelligence**: Retain the simulation mechanics, agent decision logic, and industry graph topology algorithms without premature rewrites.
2. **Decouple Edge from Persistent Services**: Ensure the React frontend is 100% decoupled from the backend compute layer, enabling edge deployment to Vercel/Netlify.
3. **Consolidate Backend Endpoints**: Unify the dual-server architecture (`webapi` on port 8080 and `enterprise_Api` on port 8000) into a single production FastAPI service under `backend/app/`.
4. **Isolate Asynchronous Long-Running Compute**: Separate synchronous HTTP query endpoints from compute-intensive Ray/AgentSociety simulation loops using Celery/Redis task workers.
5. **Enforce Strict Security & Zero Plaintext Secrets**: Purge all hardcoded credentials; enforce JWT authentication, RBAC, parameterized database queries, and secure CORS headers.

---

## 2. Target Production Architecture

```mermaid
flowchart TB
    subgraph ClientLayer [Client & Edge Presentation Layer]
        BrowserUser[Browser / Enterprise User]
        VercelNetlify[React 18 + TypeScript + Vite SPA<br/>Hosted on Vercel / Netlify CDN<br/>Configured via VITE_API_URL]
    end

    subgraph IngressLayer [Security & Edge Ingress]
        CloudLB[HTTPS Cloud Load Balancer / API Gateway<br/>TLS Termination, Rate Limiting, CORS, HSTS]
    end

    subgraph ApplicationLayer [Containerized Backend Service - ECS / Cloud Run / K8s]
        FastAPIService[FastAPI Production ASGI Server<br/>• /api/v1/* Versioned API Endpoints<br/>• Backward-Compatible Legacy Route Adapters<br/>• JWT Authentication & RBAC Middleware<br/>• Structured JSON Logger with Request IDs<br/>• Pydantic v2 Request/Response Validation]
        
        LLMServiceLayer[Centralized AI / LLM Service Layer<br/>• Multi-Model Routing (OpenAI, Qwen, DeepSeek)<br/>• Secret Masking & Token Telemetry<br/>• Automatic Retries & Circuit Breakers]
    end

    subgraph AsyncWorkerLayer [Asynchronous Background Processing]
        CeleryWorker[Celery Worker Cluster<br/>• Long-Running Agent Simulation Jobs<br/>• Monte-Carlo Disruption Simulations<br/>• Demand & Risk Forecast Computations]
        RayCluster[Ray Distributed Actor Runtime<br/>Firm Agents & Message Interception]
    end

    subgraph PersistenceLayer [State, Data & Cache Tier]
        PostgreSQL[(Managed PostgreSQL 15+<br/>• Users, Organizations, Roles<br/>• Suppliers, Inventory, Orders, Shipments<br/>• Historical Experiment Records & Metrics)]
        
        Neo4jGraph[(Managed Neo4j Graph DB<br/>• Multi-Tier Supply Topology<br/>• BOM Material Dependency Trees<br/>• Disruption Propagation Paths)]
        
        RedisCache[(Managed Redis 7+<br/>• Celery Task Queue & Result Backend<br/>• Session Caching & Rate Limiting Buckets)]
        
        MLflowService[(MLflow Tracking Service<br/>• Simulation Param & Metric Telemetry)]
    end

    BrowserUser -->|HTTPS| VercelNetlify
    VercelNetlify -->|API Requests: Bearer JWT| CloudLB
    CloudLB -->|Proxy| FastAPIService
    
    FastAPIService --> LLMServiceLayer
    FastAPIService -->|Read/Write Application State| PostgreSQL
    FastAPIService -->|Graph Queries: Cypher| Neo4jGraph
    FastAPIService -->|Rate Limiting & Cache| RedisCache
    FastAPIService -->|Enqueue Simulation Job| RedisCache
    
    RedisCache -->|Dequeue Task| CeleryWorker
    CeleryWorker --> RayCluster
    CeleryWorker --> LLMServiceLayer
    CeleryWorker --> PostgreSQL
    CeleryWorker --> Neo4jGraph
    CeleryWorker --> MLflowService
```

---

## 3. Identification of Existing Subsystem Functionality

| Subsystem | Existing Location | Primary Responsibilities | Target Production Destination |
|:---|:---|:---|:---|
| **Enterprise API** | `SupplyChainAgent/enterprise/enterprise_Api.py`, `Api.py` | Querying experiments, timeline, agent profiles, transactions, communications, inventory, metrics. | `backend/app/api/v1/` + `backend/app/api/legacy.py` |
| **AgentSociety Core** | `agentsociety/` | City agent framework, message syncer, ray simulation runtime, environment lifecycle. | `backend/app/agents/`, isolated background modules |
| **Neo4j Graph Engine** | `neo4j/neo4j_industry_chain.py`, `industry_chain_generator.py` | Building graph topologies, supplier-consumer relations, querying company products and level stats. | `backend/app/services/neo4j_service.py` |
| **Data Analysis & SQL** | `firmagentsql/select.py`, `latest_experiment_query.py`, `hanlde_data.py` | PostgreSQL database queriers, MLflow metric extraction, clustering, transaction aggregation. | `backend/app/repositories/`, `backend/app/services/` |
| **Frontend UI** | `frontend/src/` | Interactive dashboard, Console, Replay player, AntV G6 Industry Graph, Survey manager. | `frontend/` (Modernized with production API client) |
| **Simulation CLI** | `SupplyChainAgent/enterprise/main.py` | Local script to initialize Ray, load config, execute AgentSociety simulation loop. | `backend/app/workers/tasks.py` (Dispatched via Celery) |

---

## 4. Execution Model: HTTP APIs vs. Persistent Background Workers

A critical architectural distinction in SaaS platforms is separating fast, stateless HTTP requests from long-running or distributed compute tasks.

### 4.1 Safe Synchronous HTTP API Requests (< 500ms)
These operations execute within standard request-response lifecycles and require no long-running workers:
* **System Health & Probes**: `/health`, `/ready`, `/live`.
* **Authentication & User Management**: `/api/v1/auth/*`, `/api/v1/users/*`.
* **Transactional CRUD**: Querying and creating suppliers, orders, inventory items, and shipments.
* **Graph Topology Queries**: Fetching node networks, level statistics, and upstream/downstream supplier links from Neo4j.
* **Experiment Telemetry Queries**: Reading past experiment summaries, agent dialog history, and communication records from PostgreSQL.
* **Single-Agent Decision Inquiries**: Fast LLM reasoning calls for single negotiation evaluation with timeout thresholds (< 5s).

### 4.2 Tasks Requiring Persistent Background Workers
These tasks cannot run inside a serverless or synchronous HTTP request due to execution duration, compute intensity, and statefulness:
* **Multi-Agent Simulation Cycles**: Simulating days/rounds across 16+ competing firms using Ray actors and LLM negotiations (execution: minutes to hours).
* **Massive Multi-Tier Graph Propagation**: Traversing and stress-testing multi-layer supply chains for cascading bottleneck disruptions.
* **Batch Scenario Forecasting**: Generating Monte-Carlo demand and risk forecasts across thousands of product lines.
* **Telemetry Aggregation & MLflow Logging**: Asynchronous batch writes of simulation metrics, inventory levels, and financial records.

**Worker Execution Architecture**:
* **Broker & Result Store**: Redis.
* **Task Engine**: Celery worker processes running alongside the FastAPI web application in containerized environments.
* **Workflow**:
  1. Frontend sends `POST /api/v1/agents/simulations` with simulation parameters.
  2. FastAPI validates parameters, generates an `experiment_id`, enqueues a Celery task, and immediately returns `202 Accepted` with `task_id` and status URL.
  3. Celery worker executes the Ray/AgentSociety simulation asynchronously, persisting incremental step states to PostgreSQL.
  4. Frontend polls `GET /api/v1/agents/simulations/{id}/status` or listens for completion events.

---

## 5. Architectural Boundaries

### 5.1 Service Boundaries
* **Web Service (`backend/app/`)**: Pure stateless ASGI application handling client traffic, request validation, authentication, authorization, and dispatching.
* **Worker Service (`backend/app/workers/`)**: Stateful compute service running asynchronous jobs with direct access to Ray runtime and LLM providers.
* **AI Service Layer (`backend/app/services/llm_service.py`)**: Centralized gateway for LLM calls with automated retries, rate limiting, and token audit trails.
* **Graph Service Layer (`backend/app/services/neo4j_service.py`)**: Interface isolating Cypher query execution and topological transformations.

### 5.2 API Boundaries
* **`/api/v1/`**: Immutable, strictly typed, versioned production API endpoints adhering to standard REST conventions and OpenAPI specifications.
* **`/api/` (Legacy Adapter)**: Transitional compatibility layer routing legacy frontend requests (`/api/experiments/*`, `/api/surveys/*`) to underlying repositories without UI disruption.

### 5.3 Database Boundaries
* **Relational (PostgreSQL)**: Source of truth for transactional data (users, organizations, orders, shipments, inventory records, simulation logs).
* **Graph (Neo4j)**: Source of truth for structural topology (enterprise nodes, supply dependencies, material formulas, multi-tier connections).
* **Cache & Key-Value (Redis)**: Ephemeral storage for rate limiting counters, Celery message queues, session tokens, and short-term query caching.

### 5.4 Deployment Boundaries
* **Client Tier**: Static React SPA bundle deployed to edge CDNs (Vercel / Netlify). No backend Python runtime on Vercel/Netlify.
* **Backend Tier**: Containerized service running on Linux container platforms (AWS ECS / Cloud Run / Kubernetes).
* **Data Tier**: Cloud-managed PostgreSQL, Neo4j (AuraDB or container), and Redis.

---

## 6. Target Environment Variables

```bash
# Server Environment
ENVIRONMENT=development                # development, staging, production
LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR
PORT=8000                              # HTTP port

# PostgreSQL Connection
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/supplychain

# Redis Connection
REDIS_URL=redis://:password@localhost:6379/0

# Neo4j Connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# LLM Gateway
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Security & JWT
JWT_SECRET=your_super_secret_jwt_key_at_least_32_characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS Allowed Origins
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# MLflow Tracking (Optional)
MLFLOW_TRACKING_URI=http://localhost:59000
```

---

## 7. Key Identified Risks & Mitigation Strategies

| Risk | Description | Mitigation Strategy |
|:---|:---|:---|
| **Simulation Concurrency** | Ray runtime spawning multiple heavyweight processes concurrently could exhaust worker RAM. | Enforce task concurrency limits in Celery (`--concurrency=2`) and set memory limits per worker container. |
| **Neo4j Dependency During Local Dev** | Developers or automated CI testing without a running Neo4j instance would fail. | Implement a fallback mode in `neo4j_service.py` that serves static graph JSON mock data when Neo4j is offline. |
| **Frontend Breaking Changes** | Upgrading API endpoints to `/api/v1/` might break existing Replay and Console views. | Retain `backend/app/api/legacy.py` bridging old URLs (`/api/experiments/*`) to new repository methods during migration. |
| **Long-Running Simulation Timeouts** | Direct HTTP calls to trigger simulations would hit 30s gateway timeouts on cloud load balancers. | Fully decouple simulation dispatch: HTTP triggers return `202 Accepted` immediately, delegating execution to Celery. |
