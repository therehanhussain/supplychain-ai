# Phase 10 — Render Cloud Deployment Specification & Operations Guide

**Platform Target**: Render Cloud Platform ([render.com](https://render.com))  
**Deployment Model**: Render Blueprint Infrastructure as Code (`render.yaml`)  
**Frontend Ingress**: Live on Vercel at [https://frontend-pi-hazel-83.vercel.app](https://frontend-pi-hazel-83.vercel.app)  
**Status**: Configured & Locally Verified (Ready for 1-Click Render Deployment)

---

## 1. Architectural Overview

The Render cloud profile transitions SupplyChainAgent from single-host VPS management to managed cloud primitives with automated TLS, managed PostgreSQL, managed Redis-compatible caching, and isolated private networking:

```
                            Public Internet
                                  │
                          HTTPS Port 443
                                  │
                                  ▼
                   ┌─────────────────────────────┐
                   │    Vercel Edge Network      │  (Frontend SPA)
                   │frontend-pi-hazel-83.vercel.app│
                   └──────────────┬──────────────┘
                                  │
                        HTTPS API Calls / CORS
                                  │
                                  ▼
                   ┌─────────────────────────────┐
                   │   Render Public Ingress     │  (Automated TLS Termination)
                   │ supplychain-backend.onrender.com
                   └──────────────┬──────────────┘
                                  │
                  Internal Private Network (0.0.0.0:$PORT)
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                   │
        ▼                                                   ▼
┌───────────────────────────────┐           ┌───────────────────────────────┐
│Render FastAPI Web Service     │           │Celery Background Worker       │
│(Python 3.11, Uvicorn,         │           │(Optional / Paid Starter Tier) │
│ Alembic migrations on startup)│           │(Asynchronous agent sims)      │
└───────┬───────────────┬───────┘           └───────────────┬───────────────┘
        │               │                                   │
        │               └───────────────────┐               │
        ▼                                   ▼               ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│Render PostgreSQL 16 (Free)    │   │Render Key Value / Redis (Free)│
│(Internal Private Connection)  │   │(Internal Private Connection)  │
│(30-day lifecycle, 1 GB cap)   │   │(Ephemeral cache & task broker)│
└───────────────────────────────┘   └───────────────────────────────┘
```

### Relationship to VPS Architecture
The VPS Docker Compose infrastructure created in Phase 8 and 9 remains completely preserved in:
- `infra/docker-compose.production.yml`
- `infra/docker/Caddyfile`
- `scripts/bootstrap_vps.sh`
- `scripts/deploy_production.sh`
- `scripts/backup_production.sh`
- `docs/PHASE_8_INFRASTRUCTURE.md`
- `docs/PHASE_9_VPS_DEPLOYMENT.md`

Render serves as the **zero-maintenance portfolio/demo deployment target**, while the VPS architecture remains the **long-term, cost-effective self-hosted production alternative**.

---

## 2. Component Status Classification

| Component | Status | Verification Detail |
| :--- | :---: | :--- |
| **Vercel Frontend** | `CLOUD VERIFIED` | Live at `https://frontend-pi-hazel-83.vercel.app`. All 11 routes return 200 OK. |
| **Render Blueprint (`render.yaml`)** | `LOCALLY VERIFIED` | Syntactically validated via PyYAML; declarative mapping of Web, DB, and Key Value services. |
| **FastAPI Web Service** | `LOCALLY VERIFIED` | Dynamic `$PORT` handling verified; 59 tests passing; `/health/live` probe registered. |
| **PostgreSQL Compatibility** | `LOCALLY VERIFIED` | Automatic `postgres://` &rarr; `postgresql+asyncpg://` normalization tested and verified. |
| **Alembic Schema Migrations** | `LOCALLY VERIFIED` | Clean SQL DDL generation verified via `alembic upgrade head --sql`. |
| **Redis / Key Value Store** | `CONFIGURED` | Mapped via Render private network `fromService` connection string. |
| **Celery Worker** | `CONFIGURED` | Evaluated for Render; command documented; in-process asyncio fallback verified for Free tier. |
| **Neo4j Graph Database** | `LOCALLY VERIFIED` | Evaluated; certified offline dataset fallback (`industry_test.json`) verified for Free tier. |

---

## 3. The Neo4j Decision Matrix

Neo4j is an integral part of SupplyChainAgent for multi-tier supply network topology analysis. We evaluated three hosting strategies for Render:

| Attribute | Option A: Render Docker Service | Option B: External Neo4j AuraDB Free | Option C: Built-in Certified Fallback (Recommended) |
| :--- | :--- | :--- | :--- |
| **Hosting** | Render Web Service running `neo4j:5-community` | Managed cloud at [neo4j.com/cloud/aura-free](https://neo4j.com/cloud/aura-free/) | In-application dataset (`neo4j/industry_test.json`) |
| **RAM Footprint** | **~2.2 GB RAM** (512MB heap + 1536MB max + 512MB cache) | 0 MB on Render (External cloud) | 0 MB on Render (Loaded into memory on demand) |
| **Free Tier Viability** | **UNVIABLE (OOM Crash)**. Free Render tier provides 512MB RAM. | **VIABLE**. Free tier includes 1 instance with 200k nodes. | **VIABLE**. Zero cost, zero signup required. |
| **Cost** | Requires Paid Plan ($15–$25/mo) + Disk ($0.25/GB/mo) | **$0.00 / month** | **$0.00 / month** |
| **Network Protocol** | Bolt (7687) requires paid TCP proxy on Render | Native `neo4j+s://` protocol supported | In-memory JSON deserialization |
| **Data Provenance** | Live Cypher queries against dynamic graph | Live Cypher queries against cloud AuraDB | Labeled as `DEGRADED / offline_fallback_dataset` |

### Official Recommendation: **Option C for Initial Launch &rarr; Option B for Live AuraDB**
1. **Initial Free Render Deployment (Option C)**:
   Launch the backend with `NEO4J_URI` unset. The `Neo4jService` detects this, reports `status: "degraded"` with message `"Using certified fallback topology"`, and loads all 1,012 lines of multi-tier firm relationships from `neo4j/industry_test.json`. All network topology and risk endpoints respond with valid, structured supply chain data without crashing.
2. **Upgrade to Live Graph (Option B)**:
   When live graph mutations are required, create a free Neo4j AuraDB instance and set `NEO4J_URI=neo4j+s://<id>.databases.neo4j.io`, `NEO4J_USERNAME=neo4j`, and `NEO4J_PASSWORD=<password>` in the Render dashboard. The backend lazy-connects with pooled Bolt connections automatically.

---

## 4. The Celery Worker Decision & Free-Tier Reality

### Background
The codebase includes asynchronous Celery tasks (`backend.app.workers.tasks`) for:
- Long-running multi-agent simulation sweeps
- Machine learning demand forecasting
- Graph disruption cascading failure simulations

### The Render Constraint
Render's architecture separates Web Services (which receive HTTP traffic) from **Background Workers** (`type: worker`).
- **Render Background Workers do NOT have a free tier**. The minimum plan for a Background Worker is **Starter ($7.00 / month)**.
- If deployed on the Free plan, Render will refuse to create a `type: worker` service without a credit card.

### Dual-Path Solution
1. **Zero-Cost Deployment (In-Process Asyncio Worker)**:
   In `render.yaml`, the Celery worker service is commented out by default. In `backend/app/api/v1/agents.py`, simulation dispatches already schedule execution via `asyncio.create_task(simulation_service.run_simulation_worker(...))`. For student/portfolio demonstrations, simulations run asynchronously within the FastAPI process without a paid Celery worker!
2. **Production Celery Worker (Paid Starter Plan)**:
   If a paid worker is desired, uncomment the `supplychain-celery-worker` block in `render.yaml`. The worker executes:
   ```bash
   celery -A backend.app.workers.celery_app.celery_app worker --loglevel=INFO --concurrency=2
   ```

---

## 5. Free-Tier Reality Check & Limitations

> [!WARNING]
> Render's Free tier is designed for **testing, learning, and portfolio demonstration**. It must never be represented as high-availability enterprise production.

Documented limitations of the free tier:

1. **Inactivity Sleep / Cold Starts**:
   Free Render Web Services spin down to zero instances after **15 minutes of inactivity**. The first incoming request will experience a **cold start delay of 30 to 60 seconds** while the container reboots.
2. **30-Day Database Expiration**:
   Free PostgreSQL databases on Render **expire and are permanently deleted after 30 days**. To continue using the free database, you must manually recreate it every 30 days or upgrade to a paid persistent plan ($7/mo).
3. **Storage Caps**:
   - Free PostgreSQL: 1 GB maximum database size, 97 max connections.
   - Free Key Value: Ephemeral in-memory caching (data can be evicted under memory pressure).
4. **Bandwidth & Compute Limits**:
   512 MB RAM and shared CPU. Multi-agent simulations with large numbers of firms should be kept under 32 firms to prevent CPU starvation.

---

## 6. Step-by-Step Render Deployment Sequence

When you are ready to execute the deployment to Render, follow these steps:

### STEP 1: Connect GitHub Repository to Render
1. Push your local Git repository to GitHub.
2. Navigate to [dashboard.render.com](https://dashboard.render.com) and log in.
3. Click **New +** in the top navigation and select **Blueprint**.
4. Connect your GitHub repository: `SupplyChainAgent`.
5. Select the branch: `main`.

### STEP 2: Render Blueprint Auto-Discovery
Render will detect `render.yaml` at the root of the repository and show the service graph:
- **`supplychain-postgres`** (PostgreSQL 16, Free)
- **`supplychain-redis`** (Key Value, Free)
- **`supplychain-backend`** (Web Service, Python, Free)

Click **Apply**.

### STEP 3: Automated Build & Migration Execution
Render orchestrates the deployment in sequence:
1. Provisions `supplychain-postgres` and generates internal database credentials.
2. Provisions `supplychain-redis` on the private network.
3. Clones the code into the Python build environment and runs `pip install -r requirements.txt`.
4. Executes the start command:
   ```bash
   alembic -c backend/alembic.ini upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
   ```
   - Alembic connects to PostgreSQL via the normalized `postgresql+psycopg://` URL and creates all tables, indexes, and constraints.
   - Uvicorn launches on `0.0.0.0:$PORT`.
5. Render polls `healthCheckPath: /health/live`. When it returns HTTP 200, Render routes public traffic to the new version.

### STEP 4: Verify Health Probes
Once Render shows the service as **Live**, note your public service URL (e.g. `https://supplychain-backend.onrender.com`):

```bash
# 1. Test basic liveness
curl -i https://supplychain-backend.onrender.com/health/live
# Expected: HTTP/2 200 OK, {"status": "alive"}

# 2. Test deep dependency readiness
curl -s https://supplychain-backend.onrender.com/ready | jq .
```
Expected Output:
```json
{
  "status": "ready",
  "dependencies": {
    "postgres": {"status": "healthy", "latency_ms": 2.1, "message": "PostgreSQL database query verified"},
    "database": {"status": "healthy", "latency_ms": 2.1},
    "redis": {"status": "healthy", "latency_ms": 0.5, "message": "Redis cache ping successful"},
    "neo4j": {"status": "degraded", "message": "Neo4j fallback mode active (cached topology)"},
    "celery": {"status": "healthy", "message": "Redis broker reachable"},
    "llm": {"status": "simulated", "message": "LLM running in deterministic mock mode (gpt-4o-mini)"}
  }
}
```

### STEP 5: Connect Live Vercel Frontend
1. Open the [Vercel Dashboard](https://vercel.com) and navigate to `frontend-pi-hazel-83`.
2. Go to **Settings** ➔ **Environment Variables**.
3. Update `VITE_API_BASE_URL`:
   ```text
   VITE_API_BASE_URL=https://supplychain-backend.onrender.com
   ```
4. Trigger a **Redeploy** on Vercel.
5. Open [https://frontend-pi-hazel-83.vercel.app](https://frontend-pi-hazel-83.vercel.app).
6. Verify in Browser DevTools (Network tab) that API calls return `200 OK` with CORS header:
   `Access-Control-Allow-Origin: https://frontend-pi-hazel-83.vercel.app`.

---

## 7. Troubleshooting & Operational Diagnostics

### 1. Web Service Fails to Start (`Port Binding Failed`)
- **Cause**: Application tried to bind to a hardcoded port like `8000`.
- **Resolution**: Verify that the start command uses `--port $PORT`. Render sets `$PORT` dynamically in the environment.

### 2. Alembic Migration Fails (`async DBAPI driver required`)
- **Cause**: Database URL was passed with `postgres://` or `postgresql://` without driver dialect.
- **Resolution**: Our field validator in `backend/app/core/config.py` and `backend/alembic/env.py` automatically normalizes `postgres://` to `postgresql+asyncpg://` for the app and `postgresql+psycopg://` for Alembic migrations.

### 3. Service Returns 404 on Root
- **Cause**: Root health checks must use `/health`, `/live`, or `/health/live`.
- **Resolution**: In `render.yaml`, `healthCheckPath` is explicitly set to `/health/live`.

### 4. CORS Errors on Vercel (`No Access-Control-Allow-Origin`)
- **Cause**: Mismatched frontend origin in backend environment.
- **Resolution**: Verify in Render dashboard that `CORS_ORIGINS` contains `https://frontend-pi-hazel-83.vercel.app`.

---

## 8. Rollback Strategy on Render

If an update breaks functionality:
1. In the Render Dashboard, navigate to **Deploys**.
2. Locate the previous successful deployment.
3. Click the three dots (`...`) and select **Rollback to this deploy**.
4. Render immediately switches traffic back to the previous immutable container image.
