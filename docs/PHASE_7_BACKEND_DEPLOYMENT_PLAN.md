# Phase 7 — Production Backend Cloud Deployment Blueprint

**Document Version**: 1.0.0  
**Target Environment**: Cloud Production  
**Frontend URL**: [https://frontend-pi-hazel-83.vercel.app](https://frontend-pi-hazel-83.vercel.app)  
**Status**: Ready for Execution (Planning & Hardening Complete)  

---

## 1. Executive Summary & Current Backend Architecture

The SupplyChainAgent backend is an asynchronous Python 3.11 service built on FastAPI and Uvicorn. It exposes versioned REST APIs (`/api/v1/*`), operational health and readiness probes (`/health`, `/live`, `/ready`), enterprise security middleware (OWASP headers, IP/user tiered rate limiting, request correlation IDs), and multi-tenant persistence.

```
                    ┌──────────────────────────────────────────────┐
                    │          Vercel Production Frontend          │
                    │   https://frontend-pi-hazel-83.vercel.app    │
                    └──────────────────────┬───────────────────────┘
                                           │ HTTPS (CORS Authorized)
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │          FastAPI Backend Service             │
                    │   (ASGI / Uvicorn Multi-Worker, Port 8000)   │
                    └──┬───────────┬────────────┬───────────┬──────┘
                       │           │            │           │
            SQLAlchemy │           │ Cypher/    │ aioredis/ │ HTTP/REST
               asyncpg │           │ Bolt       │ Celery    │
                       ▼           ▼            ▼           ▼
                 ┌──────────┐ ┌─────────┐ ┌───────────┐ ┌─────────────┐
                 │PostgreSQL│ │  Neo4j  │ │   Redis   │ │LLM Gateway  │
                 │ 16 Rel.  │ │5 Comm.  │ │ 7 Cache & │ │OpenAI /     │
                 │  Schema  │ │ Graph   │ │Broker /0  │ │DeepSeek Live│
                 └──────────┘ └─────────┘ └─────┬─────┘ └─────────────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │Celery Worker│
                                         │ Simulations │
                                         └─────────────┘
```

### Component Status Matrix
- **FastAPI Core**: 58 automated unit/integration tests passing (0 failures).
- **PostgreSQL Persistence**: 10 primary enterprise tables defined in SQLAlchemy, fully indexed, multi-tenant with tenant ID isolation.
- **Alembic Migrations**: Initial schema `49f3694a035f_initial_schema.py` verified and syntactically validated in offline SQL DDL generation.
- **Neo4j Graph Service**: Driver with connection pooling, topology traversal, bill-of-materials traversal, and fallback caching.
- **Redis & Celery**: Distributed cache, tiered token-bucket rate limiting, and asynchronous background worker queues.
- **LLM Gateway**: Dual-provider integration (`OpenAI` and `DeepSeek`) with decision provenance tracking and explicit simulated/live modes.

---

## 2. Required Production Services

The production environment requires 7 core services to achieve full functionality:

| # | Service Component | Technology | Role in Architecture |
| :-: | :--- | :--- | :--- |
| **1** | **API Service** | FastAPI / Uvicorn (Python 3.11) | Core application gateway, authentication, business logic, REST APIs. |
| **2** | **Relational DB** | PostgreSQL 16 | Organizations, users, products, suppliers, inventory, orders, shipments, audit logs. |
| **3** | **Graph DB** | Neo4j 5 (Community or AuraDB) | Multi-tier supply chain network topology, component dependency graphs. |
| **4** | **Cache & Broker** | Redis 7 (Standalone or Cluster) | Request rate limiting, session caching, Celery task queue broker. |
| **5** | **Background Worker** | Celery (Python 3.11) | Asynchronous execution of macro disruptions, demand forecasts, and telemetry batching. |
| **6** | **Simulation Runtime** | Python Runtime / Ray | Agent Society simulation execution and macroeconomic event propagation. |
| **7** | **LLM Provider** | OpenAI API / DeepSeek API | Autonomous agent decisions, disruption reasoning, risk narrative generation. |

---

## 3. Recommended Cloud Architecture & Provider Options

To satisfy the user's objective of finding the **simplest production-capable deployment architecture suitable for this project while keeping costs reasonable**, two options have been thoroughly evaluated:

### Option A: Unified Containerized Host (Recommended for Simplicity & Budget)
* **Hosting Model**: Single dedicated Linux VM (Ubuntu 24.04 LTS) running Docker Compose with Caddy reverse proxy.
* **Provider Options**: Hetzner Cloud (CX32 / CPX31: 4 vCPU, 8GB RAM ~€12/mo) or DigitalOcean (Droplet: 4 vCPU, 8GB RAM ~$48/mo) or AWS EC2 (`t4g.xlarge`).
* **Advantages**:
  - **Zero network egress cost** between FastAPI, Postgres, Neo4j, and Redis.
  - **Private internal Docker network** (`supplychain_net`): Databases are not exposed to the public internet.
  - **Automated SSL**: Caddy automatically provisions and renews Let's Encrypt certificates.
  - **Deterministic parity**: Identical configuration to local Docker Compose.
* **Estimated Cost**: **$20 – $48 / month total**.

### Option B: Managed Multi-Cloud PaaS
* **Hosting Model**:
  - FastAPI + Celery: Render Web Service ($25/mo) + Render Background Worker ($25/mo) or Railway ($30/mo).
  - PostgreSQL: Supabase Pro ($25/mo) or Neon Serverless ($19/mo).
  - Neo4j: Neo4j AuraDB Professional ($65/mo) or Free Tier (restricted to 200k nodes).
  - Redis: Upstash Serverless ($10/mo) or Render Redis ($10/mo).
* **Advantages**: Fully managed backups, automatic failover, cloud dashboard.
* **Disadvantages**: Inter-cloud network latency between API and DBs, multi-vendor credential management, higher cost.
* **Estimated Cost**: **$135 – $240 / month total**.

> **Recommendation**: **Option A** (Dedicated Docker Compose host with Caddy reverse proxy) provides the highest performance, simplest troubleshooting, absolute lowest operational cost, and zero inter-service network latency.

---

## 4. Environment Variables Specification

The production deployment requires the following environment variables:

| Variable Name | Required | Default / Value | Description |
| :--- | :---: | :--- | :--- |
| `ENVIRONMENT` | **YES** | `production` | Enables strict production checks (enforces strong JWT, strict CORS). |
| `PORT` | **YES** | `8000` | Port for Uvicorn ASGI server. |
| `DEBUG` | **YES** | `false` | Disables debug stack traces and test endpoints. |
| `LOG_LEVEL` | **YES** | `INFO` | JSON structured log verbosity. |
| `CORS_ORIGINS` | **YES** | `https://frontend-pi-hazel-83.vercel.app` | Comma-separated list of allowed frontend origins. |
| `DATABASE_URL` | **YES** | `postgresql+asyncpg://<user>:<pass>@<host>:5432/<db>` | Production PostgreSQL asyncpg connection string. |
| `REDIS_URL` | **YES** | `redis://:<pass>@<host>:6379/0` | Production Redis connection string for cache and Celery broker. |
| `NEO4J_URI` | **YES** | `bolt://<host>:7687` | Bolt connection protocol URI for Neo4j. |
| `NEO4J_USERNAME` | **YES** | `neo4j` | Neo4j administrative user. |
| `NEO4J_PASSWORD` | **YES** | `<SECURE_PASSWORD>` | Neo4j cluster authentication password. |
| `NEO4J_DATABASE` | Optional | `neo4j` | Neo4j database name. |
| `JWT_SECRET` | **YES** | `<SECURE_RANDOM_KEY_32+_CHARS>` | Secret key for signing HS256 tokens. Enforced >= 32 chars in production. |
| `JWT_ALGORITHM` | Optional | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | `60` | Token expiry duration in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Optional | `7` | Refresh token lifecycle. |
| `LLM_MODE` | **YES** | `live` or `mock` | Set `live` for real LLM reasoning, or `mock` for deterministic baseline. |
| `OPENAI_API_KEY` | Conditional | `sk-...` | Required if `LLM_MODE=live` and OpenAI is default provider. |
| `OPENAI_BASE_URL` | Optional | `https://api.openai.com/v1` | Custom proxy or enterprise gateway endpoint. |
| `DEEPSEEK_API_KEY` | Conditional | `sk-...` | Required if `LLM_MODE=live` and DeepSeek is default provider. |
| `DEFAULT_LLM_MODEL` | Optional | `gpt-4o-mini` | Default reasoning model for agent decisions. |
| `CELERY_WORKER_CONCURRENCY` | Optional | `2` | Number of worker processes per container. |
| `RATE_LIMIT_ENABLED` | Optional | `true` | Enforces tiered rate limiting. |

---

## 5. Secret Handling Strategy

1. **Zero Secret Storage in Code**:
   - Secrets (`DATABASE_URL`, `JWT_SECRET`, `REDIS_URL`, `NEO4J_PASSWORD`, `OPENAI_API_KEY`) must never be committed to Git.
   - Verified: Git repository currently contains zero secrets.
2. **Production Secret Generation**:
   - `JWT_SECRET`: Generated using Python `secrets.token_urlsafe(32)`.
   - `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `NEO4J_PASSWORD`: Generated using 24+ character alphanumeric strings.
3. **Storage Mechanism**:
   - In VPS deployment: Stored in `/etc/supplychain/.env.production` with permissions `chmod 600`.
   - In PaaS deployment: Configured directly in the cloud provider's Secret Manager / Environment dashboard.
4. **Validation Guardrail**:
   - Backend `Settings` validator enforces that `JWT_SECRET` cannot equal the development fallback secret when `ENVIRONMENT="production"`.

---

## 6. Database Migration Strategy

### Step 1: Pre-Deployment Offline Verification (Completed)
- Offline SQL DDL was generated using `alembic upgrade head --sql` and verified without an active database connection.

### Step 2: Target Database Provisioning
- Clean PostgreSQL 16 database created with UTF-8 encoding.

### Step 3: Migration Execution Sequence
- Prior to starting the API service containers, run the migration runner:
  ```bash
  alembic -c backend/alembic.ini upgrade head
  ```
- This creates all 10 core tables, indexes, unique constraints, and the `alembic_version` table.

### Step 4: Verification
- Verify table existence:
  ```sql
  SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
  ```
  Expected tables: `organizations`, `users`, `products`, `suppliers`, `warehouses`, `inventories`, `orders`, `order_items`, `shipments`, `audit_logs`, `alembic_version`.

### Step 5: Initial Data Seeding (Optional)
- For fresh production environments, run `backend/scripts/seed_dev.py` with modified credentials, or register the initial root admin user through `/api/v1/auth/register`.

---

## 7. Neo4j Production Configuration & Topology Ingestion

1. **Engine Version**: Neo4j 5 Community Edition or Neo4j AuraDB.
2. **Authentication**:
   - Dedicated authentication credentials configured via `NEO4J_AUTH=neo4j/<STRONG_PASSWORD>`.
3. **APOC Plugins**:
   - APOC extended library enabled for graph path algorithms.
4. **Topology Seeding**:
   - Initial supply chain graph nodes (Tier 1 suppliers, Tier 2 component vendors, Tier 3 assembly plants) loaded via Cypher import script `neo4j/neo4j_industry_chain.py` or `neo4j/industry_test.json`.
5. **Fallback Resilience**:
   - If the Neo4j cluster is offline or rebooting, `neo4j_service.py` automatically returns cached topological structures (`Neo4jStatus.DEGRADED`), preventing API downtime.

---

## 8. Redis & Celery Production Configuration

1. **Redis Security**:
   - Password authentication enforced (`requirepass <REDIS_PASSWORD>`).
   - Append-Only File (AOF) persistence enabled: `appendonly yes`.
   - Maxmemory policy configured to `allkeys-lru` for cache eviction.
2. **Celery Task Broker**:
   - Redis database `/0` allocated for message broker and task result backend.
   - Tasks configured:
     - `tasks.run_agent_simulation`
     - `tasks.run_demand_forecast`
     - `tasks.run_risk_analysis`
     - `tasks.run_batch_telemetry_aggregation`
3. **Worker Concurrency**:
   - Standard 2 worker threads per 2 CPU cores (`CELERY_WORKER_CONCURRENCY=2`).
   - Late acknowledgments (`task_acks_late=True`) to guarantee no task loss during container recycling.

---

## 9. CORS Configuration for Live Vercel Frontend

- **Production Frontend Origin**: `https://frontend-pi-hazel-83.vercel.app`
- **Fallback / Preview Origins**:
  - `https://frontend-no7djg7ls-supplychain-ai1.vercel.app`
  - `http://localhost:5173` (for local developer debugging)
- **CORS Headers Injected by Backend**:
  - `Access-Control-Allow-Origin: https://frontend-pi-hazel-83.vercel.app`
  - `Access-Control-Allow-Credentials: true`
  - `Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS`
  - `Access-Control-Allow-Headers: Authorization, Content-Type, X-Request-ID`
  - `Access-Control-Expose-Headers: X-Request-ID, X-Process-Time`

---

## 10. Authentication & Security Hardening

1. **JWT RBAC Token Lifecycles**:
   - Access tokens: Expire in 60 minutes.
   - Refresh tokens: Expire in 7 days.
   - Roles: `ADMIN`, `OPERATOR`, `ANALYST`, `VIEWER`.
2. **Multi-Tenant Server Isolation**:
   - Every read and write query in repositories (`suppliers.py`, `inventory.py`, `orders.py`, `shipments.py`) filters strictly on `organization_id == current_user.organization_id`.
3. **OWASP Security Headers**:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
   - `Referrer-Policy: strict-origin-when-cross-origin`
4. **Tiered Rate Limiting**:
   - Unauthenticated endpoints (`/api/v1/auth/*`): 30 req/min per IP.
   - Authenticated business APIs: 120 req/min per user.
   - Heavy simulation endpoints: 10 req/min per tenant.

---

## 11. Health & Readiness Probe Architecture

The backend provides 3 distinct endpoints:

| Endpoint | Probe Type | Purpose | Behavior in Production |
| :--- | :--- | :--- | :--- |
| `/live` | Liveness | Kubernetes / Docker watchdog | Returns `{"status": "alive"}` immediately if process responds. |
| `/health` | Application Health | Basic runtime status | Returns `{"status": "healthy", "version": "0.1.0"}` without external dependencies. |
| `/ready` | Deep Readiness | Traffic router admission | Inspects 6 dependencies: PostgreSQL query, Neo4j status, Redis ping, Celery broker, LLM gateway. |

### `/ready` Response Schema Example:
```json
{
  "status": "ready",
  "dependencies": {
    "postgres": {
      "status": "healthy",
      "latency_ms": 2.4,
      "message": "PostgreSQL database query verified"
    },
    "neo4j": {
      "status": "healthy",
      "message": "Neo4j graph cluster verified"
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 0.8,
      "message": "Redis cache/broker ping verified"
    },
    "celery": {
      "status": "healthy",
      "message": "Celery worker broker linked (concurrency=2)"
    },
    "llm": {
      "status": "healthy",
      "message": "Live LLM provider 'openai' (gpt-4o-mini) configured"
    }
  },
  "timestamp": "2026-09-11T13:45:00Z"
}
```

---

## 12. Docker Deployment Requirements

1. **Backend Dockerfile** ([`infra/docker/backend.Dockerfile`](file:///c:/Users/MD%20REHAN%20HUSSAIN/Documents/Projects/SupplyChainAgent/infra/docker/backend.Dockerfile)):
   - Base image: `python:3.11-slim`.
   - Security: Dedicated non-root `appuser` (UID 10001).
   - Healthcheck: Built-in `curl -f http://localhost:8000/health || exit 1`.
   - Multi-worker: Uvicorn runs 2 worker processes with unbuffered JSON logging.
   - Fixed: Removed invalid `COPY data` directive; build context is clean.
2. **Build Verification Command**:
   ```bash
   docker build -t supplychain-backend:latest -f infra/docker/backend.Dockerfile .
   ```

---

## 13. Logging & Monitoring Requirements

1. **Structured JSON Logs**: All logs output to stdout in JSON Lines format with ISO 8601 timestamps, log level, request correlation ID (`X-Request-ID`), tenant ID, and path.
2. **Monitoring Metrics**:
   - Container CPU/Memory utilization.
   - HTTP response latency (`X-Process-Time`).
   - Error rates (4xx and 5xx).
   - Celery task queue length.

---

## 14. Backup & Disaster Recovery Requirements

1. **PostgreSQL Backups**:
   - Daily automated logical backup via `pg_dump`:
     ```bash
     pg_dump -U supplychain -Fc supplychain > /backups/postgres_$(date +%Y%m%d_%H%M%S).dump
     ```
   - Retain 7 daily and 4 weekly snapshots.
2. **Neo4j Graph Backups**:
   - Snapshot the Neo4j `/data` volume or run `neo4j-admin database dump`.
3. **Recovery RTO / RPO**:
   - Recovery Time Objective (RTO): < 30 minutes.
   - Recovery Point Objective (RPO): < 24 hours.

---

## 15. Estimated Deployment Complexity

| Dimension | Rating | Rationale |
| :--- | :---: | :--- |
| **Architectural Complexity** | **Moderate** | Requires relational, graph, and cache backends, but all are dockerized. |
| **Configuration Burden** | **Low** | Centralized in Pydantic `Settings` and single `.env.production` file. |
| **Operational Overhead** | **Low–Medium** | Option A requires managing 1 VM; Option B requires coordinating 4 cloud dashboards. |
| **Overall Readiness** | **HIGH** | 58 tests pass, DDL verified, Dockerfile clean, fallback handling complete. |

---

## 16. Step-by-Step Deployment Sequence

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXECUTION SEQUENCE                               │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. Provision Host or Cloud Services (VPS or PaaS accounts)             │
│ 2. Create DNS Record (e.g. api.supplychainagent.com -> Host IP)         │
│ 3. Generate Strong Secrets (JWT_SECRET, DB passwords)                   │
│ 4. Clone Repository & Checkout Tagged Production Release                │
│ 5. Start Auxiliary Services (Postgres, Redis, Neo4j)                    │
│ 6. Execute Database Migrations (alembic upgrade head)                   │
│ 7. Ingest Initial Graph Topology (Neo4j Cypher scripts)                 │
│ 8. Build & Launch Backend Container (supplychain-backend)               │
│ 9. Launch Celery Worker Container                                       │
│ 10. Configure Reverse Proxy (Caddy / Let's Encrypt HTTPS)               │
│ 11. Verify Probes (curl https://api.../ready)                           │
│ 12. Connect Frontend (Update Vercel VITE_API_BASE_URL)                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 17. Rollback Strategy

1. **API Rollback**:
   - Re-tag previous container image (`docker tag supplychain-backend:previous supplychain-backend:latest`) and restart service.
2. **Database Rollback**:
   - Downgrade Alembic schema revision:
     ```bash
     alembic -c backend/alembic.ini downgrade -1
     ```
3. **Frontend Decoupling**:
   - If the backend suffers prolonged disruption, the Vercel frontend automatically returns to verified operational fallback mode with zero user-facing crashes.

---

## 18. Risks & Blockers

1. **Neo4j Memory Footprint**: Neo4j requires at least 2GB of RAM. A 4GB–8GB host is required to avoid OOM kills when running alongside PostgreSQL and Celery.
2. **LLM Cost & Quotas**: Running multi-agent simulations with live LLM calls requires an OpenAI or DeepSeek key with sufficient credits. (Simulated mock mode remains available as zero-cost fallback).
3. **Public Cloud Credentials**: Deployment requires user-provided cloud credentials (VPS access or cloud API tokens).

---

## 19. Pre-Flight Verification Before Connecting Frontend

Before setting `VITE_API_BASE_URL` in the Vercel project environment:

- [ ] `curl -I https://api.<domain>/health` returns `200 OK`.
- [ ] `curl https://api.<domain>/ready` returns `"status": "ready"`.
- [ ] CORS pre-flight test:
  ```bash
  curl -I -X OPTIONS https://api.<domain>/api/v1/suppliers     -H "Origin: https://frontend-pi-hazel-83.vercel.app"     -H "Access-Control-Request-Method: GET"
  ```
  Returns `Access-Control-Allow-Origin: https://frontend-pi-hazel-83.vercel.app`.
- [ ] Test admin registration or login via `/api/v1/auth/login`.
- [ ] Once verified, set `VITE_API_BASE_URL=https://api.<domain>` in Vercel environment variables and trigger redeployment.
