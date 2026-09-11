# Security Audit & Required Credential Rotations

**Document Version:** 1.0.0  
**Phase:** Phase 3 — Security Hardening  
**Status:** Action Required (Manual Rotation)  

---

## 1. Executive Security Notice

During the Phase 1 and Phase 2 code audit of the **SupplyChainAgent** repository, several legacy configuration files and scripts were found to contain static, hardcoded credentials and API keys in source code.

> [!WARNING]
> Because these files have been committed to version control in the past, **all exposed secrets must be considered compromised** and must be rotated manually by the environment administrator.
> In accordance with zero-leakage security guidelines, the actual discovered keys and passwords are NOT reproduced in this document. Only their locations, purpose, and rotation procedures are documented below.

---

## 2. Credentials Requiring Manual Rotation

| Identifier / Service | File Location | Exposure Type | Severity | Action Required |
|:---|:---|:---|:---:|:---|
| **LLM Provider API Key** | `config.yaml`, `SupplyChainAgent/enterprise/config.yaml` | Plaintext API Key | **CRITICAL** | Revoke existing API key in the LLM provider dashboard (e.g., OpenAI / vLLM gateway) and generate a new key. Assign the new key to `OPENAI_API_KEY` in your `.env` file. |
| **PostgreSQL Password** | `docker/docker-compose.yml`, `docker/docker-compose-cn.yml`, `config.yaml`, `firmagentsql/config.py` | Hardcoded Database Password | **HIGH** | Change the PostgreSQL password for the `postgres` user in your production and local database instances. Update the `DATABASE_URL` environment variable accordingly. |
| **Redis Server Password** | `docker/docker-compose.yml`, `docker/docker-compose-cn.yml`, `config.yaml` | Hardcoded Cache Password | **HIGH** | Update the `requirepass` configuration on your Redis instance and set the new password in `REDIS_URL`. |
| **Neo4j Graph Database Password** | `neo4j/neo4j_industry_chain.py` | Hardcoded Database Password | **HIGH** | Execute `ALTER CURRENT USER SET PASSWORD FROM 'old' TO 'new'` in Neo4j Cypher shell. Set `NEO4J_PASSWORD` in `.env`. |
| **MLflow Auth Password** | `docker/mlflow/basic_auth.ini`, `config.yaml` | Plaintext Admin Credentials | **MEDIUM** | Regenerate MLflow HTTP basic authentication credentials in `basic_auth.ini` or migrate to OAuth2 proxy. |
| **Session Secret Key** | `agentsociety/webapi/app.py` | Static String Secret | **MEDIUM** | Generate a cryptographically secure 256-bit random string (`openssl rand -hex 32`) and set as `JWT_SECRET` in `.env`. |

---

## 3. Automated & Systematic Safeguards Implemented

To prevent accidental re-introduction of secrets:
1. **`.env` Ignored in Git**: Verified that `.gitignore` contains `.env`, `.env.local`, and cache files.
2. **Centralized Configuration (`backend/app/core/config.py`)**: All sensitive settings are loaded exclusively from environment variables via Pydantic `BaseSettings`. No fallback default values contain real credentials.
3. **Template Provided (`.env.example`)**: Developers are provided with placeholder templates containing dummy values (e.g. `your_openai_api_key_here`).
4. **Log Sanitization Middleware**: The backend logging pipeline filters out `Authorization`, `Cookie`, `X-API-Key`, and sensitive tokens before writing structured JSON logs.
5. **No Stack Traces in Production**: All API exceptions return structured error objects with a generic message and `request_id`, concealing internal connection strings or driver tracebacks.

---

## 4. Manual Verification Checklist for Deployment

- [ ] All external API keys revoked and re-issued.
- [ ] Production PostgreSQL credentials rotated with minimum 24-character random password.
- [ ] Production Redis authentication password updated.
- [ ] Production Neo4j instance secured with custom password.
- [ ] `JWT_SECRET` generated using `openssl rand -hex 32` and stored in production secret manager (AWS Secrets Manager / GCP Secret Manager / Vault).
- [ ] No `.env` files committed to Git repository (`git status` and `git log` clean).
