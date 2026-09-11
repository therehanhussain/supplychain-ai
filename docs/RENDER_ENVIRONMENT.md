# Render Environment Variables Reference & Secret Classification

**Project**: SupplyChainAgent Production Backend  
**Deployment Target**: Render Cloud Platform  
**Target Ingress**: Auto-provisioned HTTPS on Render domain (e.g., `https://supplychain-backend.onrender.com`)  
**Authorized Origin**: `https://frontend-pi-hazel-83.vercel.app`

---

## 1. Classification Overview

To prevent accidental credential leaks into source control and maintain strict production security, all environment variables are categorized into **Public / Safe Configuration** and **Secret / Sensitive Variables**.

| Category | Definition | Injection Method | Git Policy |
| :--- | :--- | :--- | :--- |
| **SAFE / NON-SECRET** | Operational parameters, feature toggles, log levels, public frontend origins. | Declared directly in `render.yaml` with plain-text `value:`. | Safe for version control. |
| **SECRET** | Cryptographic signing keys, database connection strings, auth tokens, external API keys. | Injected via `fromDatabase`, `fromService`, `generateValue: true`, or manual Render Dashboard Secrets. | **NEVER** committed to Git. |

---

## 2. Safe / Non-Secret Variables

These variables configure application behavior without exposing credentials:

| Variable | Recommended Render Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Enables production security mode (enforces strict JWT length >= 32 chars and blocks development fallback secrets). |
| `DEBUG` | `false` | Disables verbose debug traceback in HTTP error responses. |
| `LOG_LEVEL` | `INFO` | Configures structured JSON logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `PORT` | *(Provided by Render)* | Render automatically assigns this port (typically `10000`). Uvicorn listens on `0.0.0.0:$PORT`. |
| `CORS_ORIGINS` | `https://frontend-pi-hazel-83.vercel.app` | Whitelist of browser origins permitted to query the API. Comma-separated if multiple. |
| `LLM_MODE` | `mock` | Default mode for Render. Generates deterministic, zero-cost agent simulations with valid provenance metadata without external API keys. Set `live` only when real LLM API keys are provided. |
| `DEFAULT_LLM_MODEL` | `gpt-4o-mini` | Model identifier passed to the LLM Gateway when active. |
| `RATE_LIMIT_ENABLED` | `true` | Activates tiered sliding-window rate limiting. |
| `RATE_LIMIT_UNAUTHENTICATED` | `30` | Requests per minute allowed for unauthenticated visitors. |
| `RATE_LIMIT_AUTHENTICATED` | `120` | Requests per minute allowed for authenticated JWT holders. |
| `RATE_LIMIT_SIMULATION` | `10` | Requests per minute allowed for simulation / dispatch endpoints. |
| `CELERY_WORKER_CONCURRENCY`| `2` | Number of worker processes spawned per worker container. |
| `JWT_ALGORITHM` | `HS256` | Symmetric HMAC cryptographic algorithm for token signing. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| `60` | Short-lived access token lifespan (1 hour). |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Long-lived refresh token lifespan (7 days). |
| `NEO4J_DATABASE` | `neo4j` | Default Neo4j graph database name. |

---

## 3. Secret Variables (Render Managed & External)

These variables contain sensitive credentials. In `render.yaml`, they use Render's dynamic references or are left un-synced (`sync: false`) for dashboard entry:

| Variable | Source on Render | Required | Description & Generation Method |
| :--- | :--- | :---: | :--- |
| `JWT_SECRET` | `generateValue: true` | **YES** | 256-bit cryptographically secure key used to sign and verify HS256 authentication tokens. Render auto-generates this secret on service creation. |
| `DATABASE_URL` | `fromDatabase: supplychain-postgres` | **YES** | Async PostgreSQL connection string. Render provides `postgres://...` or `postgresql://...`, which the backend automatically normalizes to `postgresql+asyncpg://...`. |
| `REDIS_URL` | `fromService: supplychain-redis` | **YES** | Connection string to Render Key Value store (`redis://...`). Used for rate limiting, distributed caching, and Celery message broker. |
| `NEO4J_URI` | Dashboard / Secret | Optional | External Neo4j instance connection URI (e.g., `neo4j+s://<db-id>.databases.neo4j.io` for Neo4j AuraDB Free). When left blank, backend runs in certified offline fallback mode. |
| `NEO4J_USERNAME` | Dashboard / Secret | Optional | Neo4j graph database user (default `neo4j`). |
| `NEO4J_PASSWORD` | Dashboard / Secret | Optional | Neo4j graph database authentication password. |
| `OPENAI_API_KEY` | Dashboard / Secret | Conditional | Required only if `LLM_MODE=live` and OpenAI is selected (`sk-...`). Leave blank when `LLM_MODE=mock`. |
| `DEEPSEEK_API_KEY` | Dashboard / Secret | Conditional | Required only if `LLM_MODE=live` and DeepSeek is selected. Leave blank when `LLM_MODE=mock`. |

---

## 4. How to Configure Secrets in the Render Dashboard

When using a Render Blueprint (`render.yaml`):

1. **Auto-Generated Secrets**:
   `JWT_SECRET` is automatically created with high cryptographic entropy by Render because of the `generateValue: true` directive. No manual action is required.
2. **Auto-Linked Database Secrets**:
   `DATABASE_URL` and `REDIS_URL` are wired via internal service references (`fromDatabase` and `fromService`). Render provisions private network endpoints with zero internet exposure.
3. **Optional External Credentials** (`sync: false`):
   If you choose to connect an external Neo4j AuraDB instance or real OpenAI API keys:
   - Go to [dashboard.render.com](https://dashboard.render.com).
   - Click on your Web Service: `supplychain-backend`.
   - Navigate to **Environment**.
   - Click **Add Environment Variable**.
   - Input the key (e.g. `OPENAI_API_KEY`) and secret value.
   - Click **Save Changes**. Render will automatically perform a rolling restart with the new secret.
