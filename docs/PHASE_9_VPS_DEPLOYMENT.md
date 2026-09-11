# Phase 9 — VPS Deployment Runbook & Production Operations Manual

**Target Infrastructure**: Single Linux VPS with Docker Compose & Caddy Ingress  
**Connected Frontend**: [https://frontend-pi-hazel-83.vercel.app](https://frontend-pi-hazel-83.vercel.app)  
**Architecture**: Caddy (Ingress / TLS) ➔ FastAPI (8000) ➔ PostgreSQL 16 + Neo4j 5 + Redis 7 + Celery Worker  
**Status**: Provider-Agnostic Production Preparation (Zero Fake Domains / Domainless Bootstrap Supported)

---

## 1. Step-by-Step Future VPS Deployment Sequence

Follow this exact sequence once your cloud VPS is provisioned.

### STEP 1: Provision the VPS Host
Select a cloud provider (see [VPS Provider Comparison](file:///docs/VPS_PROVIDER_COMPARISON.md)) and create an instance with:
- **vCPU**: 4 vCPUs (x86_64 architecture)
- **RAM**: 8 GB RAM (required for Neo4j JVM heap, Postgres buffers, Redis, Uvicorn, and Celery)
- **Storage**: 80 GB to 160 GB NVMe SSD
- **Operating System**: Ubuntu 24.04 LTS
- **Networking**: 1 dedicated public IPv4 address
- **SSH Key**: Add your public SSH key during instance creation (recommended over root password)

### STEP 2: Connect via SSH
Open your local terminal and connect to the VPS public IP:
```bash
ssh -i ~/.ssh/id_ed25519 root@<VPS_PUBLIC_IP>
```
*(If you created a non-root sudo user, connect with `ssh user@<VPS_PUBLIC_IP>`)*

### STEP 3: Execute the Bootstrap Script
Run the automated host preparation script directly on the server:
```bash
# Option A: If cloning repository first
git clone https://github.com/HIT-ICES/SupplyChainAgent.git /opt/supplychain
cd /opt/supplychain
sudo bash scripts/bootstrap_vps.sh

# Option B: Or curl the raw script from your repository
curl -fsSL https://raw.githubusercontent.com/HIT-ICES/SupplyChainAgent/main/scripts/bootstrap_vps.sh | sudo bash
```
**What the Bootstrap Script Automates**:
1. System package update (`apt-get update && apt-get install`)
2. Installs base utilities: `curl`, `jq`, `git`, `ufw`, `gnupg`, `ca-certificates`
3. Applies Linux kernel optimizations: `vm.overcommit_memory = 1` for Redis persistence and file descriptor limits `nofile 65536`
4. Installs official Docker Engine and Docker Compose V2 plugin
5. Detects your active SSH port (default 22) and allows it in UFW before enabling
6. Allows HTTP port 80 and HTTPS port 443 (TCP and UDP/QUIC) for Caddy
7. Sets default policy: deny all other incoming traffic (blocking database ports `5432`, `6379`, `7474`, `7687` from internet)
8. Initializes directories: `/opt/supplychain`, `/var/backups/supplychain`, `/var/log/supplychain`

### STEP 4: Clone the Repository
Navigate to the application root directory:
```bash
cd /opt/supplychain
git status
```
Ensure you are on the `main` branch with the latest production commits.

### STEP 5: Create `.env.production` from Template
Create the private configuration file:
```bash
cp infra/env/.env.production.example infra/env/.env.production
chmod 600 infra/env/.env.production
```
> [!IMPORTANT]
> Never commit `infra/env/.env.production` to Git. File permissions must remain `600` so only the root/application user can read it.

### STEP 6: Generate Production Secrets on the VPS
Generate strong cryptographic strings directly on the VPS terminal. Do not use development defaults or human-memorable passwords:

```bash
# 1. JWT Authentication Secret (64 hex characters / 256-bit entropy)
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Or: openssl rand -hex 32

# 2. PostgreSQL Password
openssl rand -hex 16

# 3. Redis Password
openssl rand -hex 16

# 4. Neo4j Password
openssl rand -hex 16
```

Edit the file to insert the generated secrets:
```bash
nano infra/env/.env.production
```
Set:
- `JWT_SECRET=<GENERATED_JWT_SECRET>`
- `POSTGRES_PASSWORD=<GENERATED_POSTGRES_PASSWORD>`
- `REDIS_PASSWORD=<GENERATED_REDIS_PASSWORD>`
- `NEO4J_PASSWORD=<GENERATED_NEO4J_PASSWORD>`

### STEP 7: Configure Database, Security, CORS & LLM
Verify the remaining core settings in `infra/env/.env.production`:
```ini
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
CORS_ORIGINS=https://frontend-pi-hazel-83.vercel.app
CELERY_WORKER_CONCURRENCY=2
RATE_LIMIT_ENABLED=true
```

### STEP 8: LLM Provider Configuration
```ini
# KEEP MOCK MODE INITIALLY for zero API costs and zero external dependency failures:
LLM_MODE=mock
OPENAI_API_KEY=
DEEPSEEK_API_KEY=
DEFAULT_LLM_MODEL=gpt-4o-mini
```
> [!NOTE]
> Only switch `LLM_MODE=live` and supply `OPENAI_API_KEY=sk-...` or `DEEPSEEK_API_KEY=sk-...` after the entire stack is verified healthy.

### STEP 9: Domainless Initial Bootstrap vs. Custom Domain

#### Scenario A: Domainless Initial Bootstrap (Before Purchasing a Domain)
If you are bootstrapping the VPS to verify Docker, databases, and API health before buying a custom domain:
In `infra/env/.env.production`:
```ini
# Leave DOMAIN unset or commented
# Set SITE_ADDRESS to :80 for plain HTTP host verification:
SITE_ADDRESS=:80
```
Run deployment in bootstrap mode:
```bash
./scripts/deploy_production.sh --bootstrap
```
Caddy will bind to port 80 and route to the backend without attempting Let's Encrypt TLS certificates for dummy hostnames.

#### Scenario B: Full Production with Real Domain
Once you have purchased a domain (e.g., `yourdomain.com`):
In `infra/env/.env.production`:
```ini
DOMAIN=yourdomain.com
ACME_EMAIL=admin@yourdomain.com
# Leave SITE_ADDRESS commented out (defaults to api.${DOMAIN})
```

### STEP 10: Create DNS A-Record (When Domain is Ready)
Log into your DNS provider (Cloudflare, Namecheap, Route 53, etc.) and create:
- **Type**: `A`
- **Host / Name**: `api` (resolves to `api.yourdomain.com`)
- **Value / Target**: `<YOUR_VPS_PUBLIC_IP>`
- **TTL**: `300` seconds (or Auto)
- **Cloudflare Proxy**: Set to **DNS Only** (Grey Cloud) during initial certificate issuance so Let's Encrypt can complete ACME HTTP-01 challenges directly against Caddy.

Verify DNS propagation on the VPS:
```bash
dig +short api.yourdomain.com
# Must return your VPS Public IP
```

### STEP 11: Launch the Infrastructure Stack
Execute the automated deployment script:
```bash
chmod +x scripts/deploy_production.sh scripts/backup_production.sh
./scripts/deploy_production.sh
```
**What the Deployment Script Executes**:
1. Validates absence of placeholder tokens in `.env.production`
2. Pulls base images (`postgres:16-alpine`, `redis:7-alpine`, `neo4j:5-community`, `caddy:2-alpine`)
3. Builds application images (`backend`, `celery_worker`) using multi-stage `backend.Dockerfile`
4. Starts databases (`postgres`, `redis`, `neo4j`)
5. Waits for container healthchecks (`pg_isready`, `redis-cli ping`, `wget http://localhost:7474`)
6. Executes Alembic schema migrations (`alembic -c backend/alembic.ini upgrade head`)
7. Starts FastAPI backend, Celery worker, and Caddy reverse proxy
8. Awaits backend healthcheck probe (`/health/live`)
9. Prints container process status table

### STEP 12: Verify Database Schema Migrations
Inspect the migration status:
```bash
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production \
  run --rm backend alembic -c backend/alembic.ini current
```
Ensure the current migration matches the latest revision.

### STEP 13: Verify Ingress & Health Endpoints
From an external computer or from the VPS itself, run:

```bash
# 1. Process liveness probe
curl -i http://localhost:8000/health/live   # Container internal
curl -i https://api.yourdomain.com/health/live # Public Ingress (or http://<VPS_IP>/health/live if bootstrap mode)
# Expected: HTTP 200 OK, {"status": "alive"}

# 2. Comprehensive dependency readiness probe
curl -s https://api.yourdomain.com/ready | jq .
```
Expected Output:
```json
{
  "status": "ready",
  "dependencies": {
    "postgres": {"status": "healthy", "latency_ms": 1.4},
    "neo4j": {"status": "healthy"},
    "redis": {"status": "healthy", "latency_ms": 0.3},
    "celery": {"status": "healthy"},
    "llm": {"status": "healthy", "mode": "mock"}
  }
}
```

### STEP 14: Dependency-Level Verification
Verify each underlying container directly:

```bash
# PostgreSQL connectivity:
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production \
  exec postgres pg_isready -U supplychain -d supplychain

# Redis ping:
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production \
  exec redis redis-cli -a "$REDIS_PASSWORD" ping

# Neo4j Cypher query:
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production \
  exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1;"

# Celery ping:
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production \
  exec celery_worker celery -A backend.app.workers.celery_app.celery_app inspect ping
```

### STEP 15: Connect Vercel Production Frontend
Once the backend responds with HTTP 200 on `https://api.yourdomain.com/ready`:
1. Log into your [Vercel Dashboard](https://vercel.com).
2. Open the project `frontend-pi-hazel-83`.
3. Navigate to **Settings** ➔ **Environment Variables**.
4. Add or update:
   - `VITE_API_BASE_URL`: `https://api.yourdomain.com`
   - `VITE_APP_ENV`: `production`
5. Select **Production**, **Preview**, and **Development** environments.
6. Trigger a redeployment in Vercel to rebuild Vite with the new API URL:
   - Go to **Deployments** ➔ Click **Redeploy** on the latest deployment.
7. Open [https://frontend-pi-hazel-83.vercel.app](https://frontend-pi-hazel-83.vercel.app) in your browser:
   - Open Browser Developer Tools (F12) ➔ Network tab.
   - Verify that API calls target `https://api.yourdomain.com/api/v1/...` and return HTTP 200 with CORS header:
     `Access-Control-Allow-Origin: https://frontend-pi-hazel-83.vercel.app`.

---

## 2. Observability, Logging & Diagnostics

### Standard Inspection Commands
Run these commands from `/opt/supplychain`:

```bash
# 1. Check all container operational states
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production ps

# 2. View unified real-time logs across all 6 services
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f --tail=100

# 3. View FastAPI backend logs
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f --tail=100 backend

# 4. View Celery worker task execution logs
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f --tail=100 celery_worker

# 5. View Caddy reverse proxy and TLS handshake logs
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f --tail=100 caddy

# 6. View PostgreSQL database logs
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f --tail=100 postgres

# 7. View Neo4j graph engine logs
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f --tail=100 neo4j

# 8. View Redis cache logs
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f --tail=100 redis
```

---

## 3. Failure Diagnostic & Troubleshooting Guide

### Issue 1: Backend Unavailable (`502 Bad Gateway` from Caddy)
**Symptoms**: Browser or `curl https://api.yourdomain.com/ready` returns `502 Bad Gateway`.  
**Diagnostic Steps**:
1. Check if backend container is running:
   ```bash
   docker ps -a --filter "name=supplychain_backend"
   ```
2. Check backend crash logs:
   ```bash
   docker logs --tail 50 supplychain_backend
   ```
3. Common Causes:
   - Database connection timeout: Check if PostgreSQL or Redis are still starting up.
   - JWT secret error: If `ENVIRONMENT=production` and `JWT_SECRET` is shorter than 32 characters, FastAPI will exit during startup.
   - Unmigrated database table: Check if Alembic migrations were run (`./scripts/deploy_production.sh`).

### Issue 2: Database Unavailable (PostgreSQL Connection Refused)
**Symptoms**: Backend logs show `asyncpg.exceptions.CannotConnectNowError` or `ConnectionRefusedError`.  
**Diagnostic Steps**:
1. Inspect PostgreSQL container:
   ```bash
   docker logs --tail 50 supplychain_postgres
   ```
2. Verify container health status:
   ```bash
   docker inspect --format='{{.State.Health.Status}}' supplychain_postgres
   ```
3. Test local authentication:
   ```bash
   docker exec -it supplychain_postgres psql -U supplychain -d supplychain -c "SELECT 1;"
   ```
4. Common Causes:
   - Disk full: Run `df -h` on the VPS.
   - Password mismatch: Ensure `POSTGRES_PASSWORD` in `DATABASE_URL` matches the container's environment password.

### Issue 3: Redis Unavailable
**Symptoms**: Celery workers exit with `kombu.exceptions.OperationalError` or rate limiter fails.  
**Diagnostic Steps**:
1. Inspect Redis logs:
   ```bash
   docker logs --tail 50 supplychain_redis
   ```
2. Test ping with password:
   ```bash
   source infra/env/.env.production
   docker exec -it supplychain_redis redis-cli -a "${REDIS_PASSWORD}" ping
   ```
3. Common Causes:
   - Memory overcommit disabled: Check `cat /proc/sys/vm/overcommit_memory`. Must be `1`.

### Issue 4: Neo4j Graph Database Unavailable
**Symptoms**: Readiness probe reports `neo4j: unhealthy`.  
**Diagnostic Steps**:
1. Inspect Neo4j logs:
   ```bash
   docker logs --tail 50 supplychain_neo4j
   ```
2. Check Neo4j HTTP port responsiveness inside network:
   ```bash
   docker exec -it supplychain_backend curl -I http://neo4j:7474
   ```
3. Common Causes:
   - Out of Memory (OOM): Neo4j JVM heap killed by Linux OOM killer. Check `dmesg -T | grep -i oom`. Ensure VPS has at least 8 GB RAM.

### Issue 5: Celery Worker Failing
**Symptoms**: Simulations remain in `queued` state indefinitely.  
**Diagnostic Steps**:
1. Inspect Celery worker logs:
   ```bash
   docker logs --tail 50 supplychain_celery
   ```
2. Inspect active Celery queues:
   ```bash
   docker exec -it supplychain_celery celery -A backend.app.workers.celery_app.celery_app status
   ```

### Issue 6: TLS / SSL Certificate Failure
**Symptoms**: Browser shows `NET::ERR_CERT_COMMON_NAME_INVALID` or `SSL_ERROR_SYSCALL`.  
**Diagnostic Steps**:
1. Inspect Caddy's ACME logs:
   ```bash
   docker logs --tail 100 supplychain_caddy | grep -i -E "(tls|certificate|acme|error)"
   ```
2. Verify DNS resolution from outside:
   ```bash
   nslookup api.yourdomain.com 1.1.1.1
   ```
3. Verify port 80 is reachable from the internet (Let's Encrypt requires port 80 for HTTP-01 challenge):
   ```bash
   sudo ufw status | grep 80
   ```
4. Cloudflare Proxy Note: If using Cloudflare, change DNS record from Orange Cloud (Proxied) to Grey Cloud (DNS Only).

---

## 4. Backup & Disaster Recovery Architecture

### Classification of Backup Tiers
It is critical to maintain architectural honesty regarding backups:

| Backup Tier | Mechanism | Storage Location | Protection Scope | Current Status |
| :--- | :--- | :--- | :--- | :---: |
| **Local Container Backup** | `scripts/backup_production.sh` | `/var/backups/supplychain/<TIMESTAMP>` on VPS disk | Accidental data deletion, corrupted tables, bad migrations | **CONFIGURED & TESTED** |
| **VPS Cloud Snapshot** | Cloud Provider Control Panel (Hetzner / DO / AWS) | Cloud Provider Object Storage | Total OS disk corruption, bad system updates | **MANUAL IN PROVIDER CONSOLE** |
| **Off-Site Automated Backup** | S3 / R2 / Backblaze B2 sync script | Separate geographic cloud region | Total VPS destruction, cloud datacenter loss | **FUTURE ENHANCEMENT (NOT CONFIGURED)** |

> [!CAUTION]
> Local backups generated by `scripts/backup_production.sh` reside on the **local VPS disk**. If the VPS hardware fails, is deleted, or the hypervisor storage is wiped, local backups will be lost. You MUST enable Cloud Provider Snapshots or configure automated off-site sync (e.g. `rclone` to AWS S3 / Cloudflare R2).

### Automated Nightly Backup Setup (Local)
Add the backup job to the VPS crontab:
```bash
sudo crontab -e
```
Add the following line (runs every night at 02:00 UTC):
```crontab
0 2 * * * /opt/supplychain/scripts/backup_production.sh >> /var/log/supplychain/backup.log 2>&1
```

### Manual Backup Execution
```bash
sudo /opt/supplychain/scripts/backup_production.sh
```
Outputs:
- PostgreSQL logical dump: `/var/backups/supplychain/<TIMESTAMP>/postgres_supplychain_<TIMESTAMP>.dump` (custom compressed format `-Fc`)
- Neo4j graph data volume snapshot: `/var/backups/supplychain/<TIMESTAMP>/neo4j_data_<TIMESTAMP>.tar.gz`
- Automatically prunes local backups older than 7 days.

### Disaster Recovery Runbooks

#### Scenario 1: Container Failure (Restart & Health Recovery)
- Docker restart policy is set to `restart: unless-stopped`. If a container process crashes, Docker restarts it automatically.
- Persistent data resides in named Docker volumes (`supplychain_postgres_production_data`, `supplychain_neo4j_production_data`, `supplychain_redis_production_data`), surviving container restarts and recreations.

#### Scenario 2: Data Corruption (Restore from Local Backup)
```bash
# 1. Identify backup timestamp to restore
ls -la /var/backups/supplychain/

# 2. Restore PostgreSQL database
cat /var/backups/supplychain/<TIMESTAMP>/postgres_supplychain_*.dump | \
  docker exec -i supplychain_postgres pg_restore -U supplychain -d supplychain --clean --if-exists

# 3. Restore Neo4j graph data
# Stop Neo4j container before replacing data files
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production stop neo4j
docker run --rm \
  -v supplychain_neo4j_production_data:/data \
  -v /var/backups/supplychain/<TIMESTAMP>:/backup \
  alpine sh -c "rm -rf /data/* && tar -xzf /backup/neo4j_data_*.tar.gz -C /data"
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production start neo4j
```

#### Scenario 3: Complete VPS Hardware Destruction
1. Provision a new VPS instance following **STEP 1** & **STEP 2**.
2. Run `bootstrap_vps.sh` (**STEP 3**).
3. Clone repository and restore `.env.production`.
4. Restore latest off-site backup dump files into `/var/backups/supplychain/`.
5. Run `./scripts/deploy_production.sh`.
6. Execute the restoration commands from Scenario 2 above.
7. Update DNS A-record to the new VPS public IP (**STEP 10**).
