# SupplyChainAgent: Environment Configuration Specification

**Document Version:** 1.0.0  
**Phase:** Phase 5 — Production Integration & Hardening  
**Target Environments:** `development`, `test`, `staging`, `production`  

---

## 1. Overview & Operational Principles

All application configurations are loaded via **Pydantic v2 BaseSettings** in `backend/app/core/config.py`. 

### Key Invariants:
1. **Zero Secret Defaults in Production**: The application will fail-fast at boot if sensitive variables (e.g. `JWT_SECRET`, database passwords) remain set to development fallbacks in staging or production environments.
2. **Deterministic Precedence**: Environment variables in the host/container take highest precedence, followed by `.env` file values, followed by explicit model defaults.
3. **Redaction Guarantee**: Sensitive credentials (`JWT_SECRET`, `NEO4J_PASSWORD`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`) are masked in logs, health endpoints, and diagnostic output.

---

## 2. Master Configuration Matrix

| Variable | Type | Default (Dev) | Production Target | Sensitive? | Description |
|:---|:---:|:---|:---|:---:|:---|
| **`ENVIRONMENT`** | `str` | `development` | `production` | No | Target runtime environment (`development`, `test`, `staging`, `production`). |
| **`DEBUG`** | `bool` | `False` | `False` | No | Enables FastAPI auto-reload and verbose stack traces. **Must be False in production.** |
| **`PORT`** | `int` | `8000` | `8000` | No | HTTP listening port for ASGI server. |
| **`LOG_LEVEL`** | `str` | `INFO` | `INFO` | No | Standard logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| **`CORS_ORIGINS`** | `str` / `list` | `http://localhost:5173,http://localhost:3000` | `https://app.supplychain.company.com` | No | Allowed web origins. In production, must be restricted to verified HTTPS domains. |
| **`DATABASE_URL`** | `str` | `sqlite+aiosqlite:///./supplychain.db` | `postgresql+asyncpg://app_user:pwd@db.internal:5432/supplychain_prod` | **Yes** | SQLAlchemy async connection URI. Requires `asyncpg` driver in production. |
| **`REDIS_URL`** | `str` | `redis://localhost:6379/0` | `rediss://:auth_token@cache.internal:6379/0` | **Yes** | Redis connection URI for caching and Celery task broker. Use TLS (`rediss://`) in production. |
| **`NEO4J_URI`** | `str` | `bolt://localhost:7687` | `neo4j+s://graph.internal:7687` | No | Neo4j cluster bolt URI. Use `neo4j+s://` (TLS) for production clusters. |
| **`NEO4J_USERNAME`** | `str` | `neo4j` | `app_service_account` | No | Neo4j cluster authentication username. |
| **`NEO4J_PASSWORD`** | `str` | `""` | *[Strong Secret]* | **Yes** | Neo4j cluster password. |
| **`NEO4J_DATABASE`** | `str` | `neo4j` | `neo4j` | No | Target Neo4j database catalog name. |
| **`LLM_MODE`** | `str` | `mock` | `live` or `mock` | No | Operational mode for AI decisions (`live` or `mock`). If `live`, valid API keys are required. |
| **`OPENAI_API_KEY`** | `str` | `""` | `sk-proj-...` | **Yes** | OpenAI API secret key for live model generation. |
| **`OPENAI_BASE_URL`** | `str` | `https://api.openai.com/v1` | `https://api.openai.com/v1` | No | Base endpoint for OpenAI or enterprise API proxy. |
| **`DEEPSEEK_API_KEY`** | `str` | `""` | `sk-...` | **Yes** | DeepSeek API key for alternative reasoning provider. |
| **`DEEPSEEK_BASE_URL`** | `str` | `https://api.deepseek.com/v1` | `https://api.deepseek.com/v1` | No | Base endpoint for DeepSeek provider. |
| **`DEFAULT_LLM_MODEL`** | `str` | `gpt-4o-mini` | `gpt-4o-mini` | No | Default LLM model identifier. |
| **`JWT_SECRET`** | `str` | `development_fallback_secret...` | *[Min 64-char crypto secret]* | **Yes** | Cryptographic secret for signing HMAC-SHA256 JWT access and refresh tokens. |
| **`JWT_ALGORITHM`** | `str` | `HS256` | `HS256` | No | JWT cryptographic signing algorithm. |
| **`ACCESS_TOKEN_EXPIRE_MINUTES`** | `int` | `60` | `60` | No | JWT access token lifetime in minutes. |
| **`REFRESH_TOKEN_EXPIRE_DAYS`** | `int` | `7` | `7` | No | Refresh token rotation window in days. |
| **`RATE_LIMIT_ENABLED`** | `bool` | `True` | `True` | No | Toggles API rate limiting middleware. |
| **`RATE_LIMIT_UNAUTHENTICATED`** | `int` | `30` | `30` | No | Maximum requests per minute for unauthenticated clients. |
| **`RATE_LIMIT_AUTHENTICATED`** | `int` | `120` | `120` | No | Maximum requests per minute for authenticated tenants. |
| **`RATE_LIMIT_SIMULATION`** | `int` | `10` | `10` | No | Maximum requests per minute for simulation/AI dispatch. |
| **`CELERY_WORKER_CONCURRENCY`** | `int` | `2` | `8` | No | Number of parallel task worker threads/processes. |
| **`MLFLOW_TRACKING_URI`** | `str` | `http://localhost:59000` | `https://mlflow.internal.company.com` | No | Internal tracking URI for simulation telemetry. |
| **`VITE_API_URL`** (Frontend) | `str` | `http://localhost:8000` | `https://api.supplychain.company.com` | No | Frontend root endpoint for backend API Gateway. |
