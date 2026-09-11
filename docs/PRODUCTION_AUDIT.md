# Production Readiness Audit Report: SupplyChainAgent

**Date:** 2026-09-11  
**Author:** Lead Production Engineer  
**Status:** Complete  
**Repository:** [supplychain-ai](https://github.com/therehanhussain/supplychain-ai)

---

## Executive Summary

SupplyChainAgent is an AI-powered multi-agent supply chain simulation and analysis platform. Originally developed as an academic and research prototype combining Tsinghua FIB-Lab's AgentSociety v1.3 with specialized enterprise supply chain modeling, the system incorporates:
1. **Multi-Agent Simulation Engine**: Enterprise agents with autonomous production, inventory, pricing, and negotiation capabilities powered by LLMs (OpenAI, Qwen, DeepSeek, Claude) and Ray.
2. **Relational Data Management**: PostgreSQL for experiment tracking, agent states, transactions, and communication logs.
3. **Graph Intelligence**: Neo4j for hierarchical supply chain topologies (multi-tier supplier-consumer networks) and dependency propagation.
4. **Metrics & Experiment Tracking**: MLflow for parameter logging, financial telemetry, inventory ratios, and time-series metrics.
5. **Interactive Frontend**: React 18, TypeScript, Vite, Ant Design, and AntV G6 visualization.

While the simulation mechanics and domain models are conceptually strong, the codebase is in a **prototype/research state** that cannot be safely or reliably deployed to production as a SaaS platform without architectural transformation.

This audit details the current architecture, critical bugs, security vulnerabilities, deployment blockers, target SaaS architecture, and a structured 14-phase migration plan.

---

## 1. Current Architecture

### 1.1 High-Level Component Topology
```mermaid
flowchart TD
    subgraph Frontend [Frontend: React + Vite :5173]
        UI[Ant Design UI & AntV G6 Graph]
        Proxy[Vite Dev Proxy: /api -> :8080]
        DirectFetch[Direct Fetch -> localhost:8000]
    end

    subgraph BackendSplit [Dual Backend Architecture]
        WebApi[AgentSociety WebAPI :8080<br/>FastAPI + Session Middleware<br/>Experiment Runner + Surveys]
        EnterpriseApi[Enterprise API :8000<br/>FastAPI + Raw Psycopg<br/>Agent Profiles, Dialogs, Metrics]
    end

    subgraph StorageLayer [State & Persistence]
        PG[(PostgreSQL :5432<br/>Experiments, States, Records)]
        Neo[(Neo4j :7687<br/>Supply Network Graph)]
        Redis[(Redis :6379<br/>AgentSociety Syncer)]
        MLflow[MLflow Server :59000<br/>Run Metrics & Parameters]
        LocalFiles[Local JSON & Map Files<br/>./data/*.json, .pb]
    end

    UI --> Proxy --> WebApi
    UI --> DirectFetch --> EnterpriseApi
    WebApi --> PG
    EnterpriseApi --> PG
    EnterpriseApi --> MLflow
    WebApi --> MLflow
```

### 1.2 Frontend Architecture
* **Stack**: React 18.3, TypeScript 5.6, Vite 6.0, Ant Design 5.22, `@ant-design/pro-components`, `@antv/g6` (graph visualization), `@monaco-editor/react`, MobX 6.13, React Router v7.
* **API Communication Inconsistency**:
  * Some requests call `/api/...` expecting Vite proxy to forward to `http://localhost:8080` (`/api/mlflow/url`, `/api/run-experiments`, `/api/surveys`, `/api/experiments`).
  * Other requests in `src/services/api.ts` hardcode `BackendApiUrl = "http://localhost:8000/api"`.
  * Static JSON files are fetched directly via relative browser paths: `/neo4j/industry_test_small.json`, `/enterprise/data/state_*.json`.
* **State Management**: Mixed between MobX stores (`Replay/store.ts`), `localforage` indexedDB browser storage (`storageService.ts`), and ad-hoc React state.
* **Authentication**: Dependencies `casdoor-js-sdk` and `casdoor-react-sdk` exist in `package.json`, but there is no actual token management, login page, HTTP Authorization header injector, or route guards.

### 1.3 Backend Architecture
* **Split Servers**:
  1. `agentsociety/webapi/app.py`: Created via `agentsociety ui -c config.yaml`. Runs on port 8080. Uses SQLAlchemy async engine and Starlette SessionMiddleware. Serves `/api/experiments`, `/api/surveys`, `/api/mlflow/url`, `/api/run-experiments`.
  2. `SupplyChainAgent/enterprise/enterprise_Api.py`: Standalone FastAPI script run via `uvicorn enterprise_Api:app --port 8000`. Uses raw `psycopg` async connections directly into PostgreSQL tables (`company_states`, `company_records`, `as_experiment`).
  3. `SupplyChainAgent/enterprise/Api.py`: Minimal endpoint `/api/state/{fid}` reading local JSON files.
* **Database Access**: Direct SQL string interpolation with `%s` parameters; no ORM repositories, no migration framework (Alembic), no connection pooling safeguards.
* **Agent Engine**: Built on Ray (`ray.init()`) and AgentSociety simulation loops (`SupplyChainAgent/enterprise/main.py`), triggered either synchronously or via local scripts.

---

## 2. Critical Problems

1. **Dual Backend Confusion**: The application cannot function without running two separate FastAPI servers on different ports (8000 and 8080), in addition to MLflow, PostgreSQL, and Redis. The frontend tries to communicate with both concurrently.
2. **Hardcoded Machine Paths & Operating System Assumptions**:
   * `utils/path_utils.py`: `project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))` relies on arbitrary directory nesting.
   * `firmagentsql/config.py`: Hardcoded path to `agentsociety-enterprise/SupplyChainAgent/enterprise/config.yaml`.
   * `SupplyChainAgent/enterprise/readme.md`: Hardcoded path `PYTHONPATH=/home/cuda/agentsociety-enterprise`.
3. **Hardcoded Experiment & Run Identifiers**:
   * `firmagentsql/hanlde_data.py` hardcodes `experiment_id = "e7ec8d6e-dbdb-4f59-8749-959b898d7613"` and `run_uuid = "b07b54ee51bd416bba07bfd6b156c93f"`.
4. **Data Response Contract Inconsistencies**:
   * `enterprise_Api.py` returns raw lists for `/api/experiments` (`['id1', 'id2']`), whereas the frontend `Console/index.tsx` expects `{ data: [{ id, name, status, cur_day, ... }] }`.
5. **No Database Migrations**:
   * Database tables (`company_states`, `company_records`, `company_transaction_lists`, `as_experiment`) have no versioned Alembic migration scripts.
6. **No Automated Test Suite**:
   * There are zero unit, integration, or API tests across the entire repository.
7. **Unmanaged Background Processes**:
   * Ray-based simulations are launched as local processes without Celery/RQ job queuing, task state tracking, timeout handling, or worker autoscaling.

---

## 3. Security Risks

| Risk Level | Issue | Location | Impact |
|:---|:---|:---|:---|
| **CRITICAL** | Hardcoded API Keys in Git | `config.yaml`, `SupplyChainAgent/enterprise/config.yaml` | Plaintext LLM API keys (`sk-sbadfsaf`) committed to source control. Risk of quota exhaustion and unauthorized access. |
| **CRITICAL** | Hardcoded Database & Service Credentials | `docker/docker-compose.yml`, `neo4j/neo4j_industry_chain.py` | Passwords `SupplyChainDB2026`, `SupplyChainRedis2026`, `12345678` exposed in plaintext. |
| **CRITICAL** | Zero Authentication on APIs | `SupplyChainAgent/enterprise/enterprise_Api.py` | All `/api/experiments/*` endpoints are completely unauthenticated. Anyone on the network can view or delete data. |
| **HIGH** | Invalid & Permissive CORS Configuration | `enterprise_Api.py:51` | `allow_origins=["*"]` combined with `allow_credentials=True` violates the CORS specification and exposes APIs to CSRF and cross-origin data theft. |
| **HIGH** | Hardcoded Session Secret Key | `agentsociety/webapi/app.py:29` | Session secret `agentsociety-session` is static, allowing session forgery if signed cookies are used. |
| **HIGH** | Arbitrary File System Reads | `SupplyChainAgent/enterprise/Api.py` | Path formatting `f"./data/state_{fid}.json"` allows path traversal if `fid` contains `../`. |
| **MEDIUM** | Unbounded Request Payload & No Rate Limiting | Entire Backend | Lack of rate limiting (slowapi/Redis) leaves all LLM-calling endpoints open to denial-of-service and billing explosion. |

---

## 4. Deployment Blockers

1. **Monolithic Builder Dockerfile**: The root `Dockerfile` attempts to install the entire repository into a python wheel and executes `rm -rf /app`. It cannot be used to run a persistent web service.
2. **Missing Backend Containerization**: No production container runs Gunicorn/Uvicorn with non-root security.
3. **Serverless Incompatibility**: AgentSociety and Ray depend on persistent memory, background threads, and C-extensions (`torch`, `grpcio`, `fastavro`, `ray`), making the backend unsuitable for Vercel/Netlify serverless functions.
4. **Localhost Binding**: All API clients in frontend and backend hardcode `http://localhost:8000`, `http://localhost:8080`, `bolt://localhost:7687`.
5. **No Static Asset Hosting**: Graph topologies (`industry_test.json`) are read from local disk rather than served via CDN or database.

---

## 5. Recommended Architecture

```mermaid
flowchart TB
    subgraph ClientTier [Client Tier - Static Hosting]
        VercelNetlify[React 18 + TS + Vite SPA<br/>Hosted on Vercel / Netlify<br/>Configured via VITE_API_URL]
    end

    subgraph IngressTier [Ingress & Edge]
        LB[HTTPS Reverse Proxy / Cloud Load Balancer<br/>Strict CORS, SSL Termination, Secure Headers]
    end

    subgraph ServiceTier [Containerized Backend Service - ECS/Cloud Run/K8s]
        FastAPIApp[FastAPI Enterprise Backend<br/>Versioned API: /api/v1/*<br/>JWT Auth & RBAC Middleware<br/>Request ID & Latency Logging<br/>Centralized LLM Service Layer]
        CeleryWorker[Celery / Async Background Worker<br/>Agent Simulation Engine<br/>Forecasting & Risk Computations]
    end

    subgraph DataTier [Managed Cloud Data Tier]
        ManagedPG[(Managed PostgreSQL<br/>Users, Org, Inventory, Orders, Transactions)]
        ManagedNeo[(Managed Neo4j / AuraDB<br/>Multi-Tier Supply Chain Graph & Routes)]
        ManagedRedis[(Managed Redis<br/>Celery Broker, Cache, Rate Limiting)]
        LLMProvider[LLM Provider Gateway<br/>OpenAI / Azure / Anthropic API]
    end

    VercelNetlify -->|HTTPS / JWT| LB
    LB --> FastAPIApp
    FastAPIApp --> ManagedPG
    FastAPIApp --> ManagedNeo
    FastAPIApp --> ManagedRedis
    FastAPIApp --> LLMProvider
    FastAPIApp -->|Enqueue Simulation| CeleryWorker
    CeleryWorker --> ManagedPG
    CeleryWorker --> ManagedNeo
    CeleryWorker --> ManagedRedis
    CeleryWorker --> LLMProvider
```

### Key Architectural Principles:
1. **Unified FastAPI Backend**: Consolidate `webapi` and `enterprise_Api` into a single, clean layered architecture under `backend/app/` on port 8000.
2. **Separation of Concerns**:
   * `api/`: Route controllers with Pydantic request/response validation.
   * `core/`: Configuration (`BaseSettings`), security (JWT/password hashing), database sessions, structured JSON logging.
   * `models/`: SQLAlchemy ORM definitions for relational persistence.
   * `schemas/`: Strict Pydantic schemas for all entities.
   * `services/`: Business logic, Neo4j graph queries, centralized LLM client.
   * `agents/`: Enterprise multi-agent orchestration and simulation logic.
   * `workers/`: Background task execution.
3. **Decoupled Frontend Deployment**: Build the React SPA into static bundles deployable to Vercel or Netlify, talking strictly to the backend URL specified in `VITE_API_URL`.

---

## 6. Migration Plan

The migration is broken into 14 sequential phases:
- **Phase 1: Production Audit** *(Current)* — Comprehensive inspection and documentation.
- **Phase 2: Target Architecture** — Formalize directory structures, component interfaces, and deployment targets.
- **Phase 3: Clean Architecture Refactor** — Establish `backend/app/`, `frontend/`, `tests/`, `infra/`, `docs/` while preserving legacy code.
- **Phase 4: Configuration & Secrets** — Implement `pydantic-settings`, `.env.example`, and purge all hardcoded credentials.
- **Phase 5: Unified Versioned API** — Build `/api/v1/` routes for auth, users, suppliers, inventory, orders, shipments, routes, forecast, risk, agents, analytics, plus backward-compatible legacy routes.
- **Phase 6: Security Hardening** — JWT authentication, password hashing, RBAC, parameterized Cypher queries, secure CORS, rate limiting.
- **Phase 7: Observability & Health Probes** — Structured JSON logging, request IDs, latency tracking, `/health`, `/ready`, `/live`.
- **Phase 8: Comprehensive Automated Testing** — Unit, integration, and API test suites with Pytest.
- **Phase 9: Production Docker Stack** — Multi-stage non-root Dockerfile and `docker-compose.production.yml`.
- **Phase 10: Frontend Modernization** — Dynamic `VITE_API_URL`, Axios client with auth interceptors, error boundaries, empty states.
- **Phase 11: Vercel & Netlify Deployment** — `vercel.json` and `netlify.toml` with SPA rewrites.
- **Phase 12: CI/CD Pipelines** — GitHub Actions workflows for linting, testing, Docker build, and deployment.
- **Phase 13: Open-Source Documentation** — Industry-standard `README.md` with architecture diagrams and API reference.
- **Phase 14: Verification & Sign-off** — End-to-end execution of builds, test suites, container startup, and checklist validation.

---

## 7. Environment Variables Specification

| Variable | Description | Example / Default | Required in Prod |
|:---|:---|:---|:---:|
| `ENVIRONMENT` | Runtime environment (`development`, `staging`, `production`) | `production` | Yes |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` | Yes |
| `PORT` | Backend server port | `8000` | No (default 8000) |
| `DATABASE_URL` | PostgreSQL connection string (asyncpg or psycopg) | `postgresql+asyncpg://user:pass@host:5432/supplychain` | Yes |
| `REDIS_URL` | Redis cache and queue connection string | `redis://:pass@host:6379/0` | Yes |
| `NEO4J_URI` | Neo4j Bolt protocol URI | `bolt://host:7687` or `neo4j+s://...` | Yes |
| `NEO4J_USERNAME`| Neo4j database user | `neo4j` | Yes |
| `NEO4J_PASSWORD`| Neo4j database password | *(Secret)* | Yes |
| `OPENAI_API_KEY`| OpenAI or compatible LLM provider API key | `sk-...` *(Secret)* | Yes |
| `OPENAI_BASE_URL`| Custom LLM base URL (if using proxy/vLLM/Qwen) | `https://api.openai.com/v1` | No |
| `JWT_SECRET` | Secret key for signing JWT tokens (min 32 chars) | *(Secret)* | Yes |
| `JWT_ALGORITHM` | Cryptographic algorithm for JWT | `HS256` | No (default HS256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of access token | `60` | No |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins | `https://app.supplychain.io,http://localhost:5173` | Yes |
| `VITE_API_URL` | Frontend client target backend URL | `https://api.supplychain.io` | Yes (Frontend) |

---

## 8. Services Required

1. **Managed PostgreSQL 15+**: Relational store for users, roles, suppliers, inventory items, orders, shipments, simulation runs, and audit trails.
2. **Managed Neo4j 5+ (AuraDB or Self-hosted)**: Graph database modeling supplier-customer dependencies, material composition trees, and disruption path propagation.
3. **Managed Redis 7+**: In-memory caching, rate limit bucket tracking, and Celery task broker.
4. **Container Host (AWS ECS, Google Cloud Run, or Kubernetes)**: Compute layer running persistent FastAPI ASGI server and Celery background workers.
5. **Static Hosting (Vercel or Netlify)**: Edge CDN delivery for the React Vite frontend SPA.
6. **LLM Provider Gateway**: Centralized upstream API (OpenAI, Anthropic, or self-hosted vLLM).

---

## 9. Estimated Complexity of Each Change

| Phase | Description | Complexity | Key Dependencies & Risk Areas |
|:---|:---|:---:|:---|
| **Phase 1** | Audit & Documentation | Low | None |
| **Phase 2** | Architecture Design | Low | System topology alignment |
| **Phase 3** | Codebase Refactoring (`backend/app/`) | High | Preserving simulation & query logic without breakage |
| **Phase 4** | Configuration & Secret Management | Low | Pydantic Settings integration |
| **Phase 5** | Unified API (`/api/v1/*` + Legacy Aliases) | High | Schema modeling, routing, backward compatibility |
| **Phase 6** | Security (Auth, RBAC, Safe Queries, CORS) | Medium | Passlib/Bcrypt, JWT validation, Neo4j parameterization |
| **Phase 7** | Observability (JSON Logs, Probes, Request IDs) | Medium | Middleware integration, DB connection pinging |
| **Phase 8** | Testing Suite (Unit, Integration, API) | High | Mocking LLM, Postgres, Neo4j, Pytest fixtures |
| **Phase 9** | Production Docker & Compose | Medium | Multi-stage build, non-root user, networking |
| **Phase 10** | Frontend Modernization & API Client | High | Axios interceptor, VITE_API_URL, UI error states |
| **Phase 11** | Vercel & Netlify Deployment Config | Low | Rewrites configuration (`vercel.json`, `netlify.toml`) |
| **Phase 12** | CI/CD GitHub Workflows | Medium | Linting, test execution, container builds |
| **Phase 13** | Documentation & README Overhaul | Medium | Markdown documentation, diagrams, setup guides |
| **Phase 14** | Verification & Sign-off | Medium | Automated verification of builds and tests |
