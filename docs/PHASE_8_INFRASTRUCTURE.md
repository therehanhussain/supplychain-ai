# Phase 8 — Production Infrastructure Specification & Operations Handbook

**Target Architecture**: Single Linux VPS with Docker Compose & Caddy Ingress  
**Target Services**: Caddy, FastAPI Backend, PostgreSQL 16, Neo4j 5, Redis 7, Celery Worker  
**Connected Frontend**: [https://frontend-pi-hazel-83.vercel.app](https://frontend-pi-hazel-83.vercel.app)  
**Status**: Infrastructure Implemented & Locally Verified  

---

## 1. Production Architecture Overview

The SupplyChainAgent production backend infrastructure is architected for zero public database exposure, deterministic parity with developer environments, and automated TLS certificate management:

```
                            Public Internet
                                  │
                          HTTPS Port 443 / HTTP Port 80
                                  │
                                  ▼
                   ┌─────────────────────────────┐
                   │    Caddy Reverse Proxy      │  (Ingress / TLS Termination)
                   │  (Auto Let's Encrypt / QUIC)│
                   └──────────────┬──────────────┘
                                  │
                   Private Network: supplychain_production_net
                                  │
       ┌──────────────────────────┴──────────────────────────┐
       │                                                     │
       ▼                                                     ▼
┌──────────────┐                                      ┌──────────────┐
│FastAPI API   │                                      │Celery Worker │
│(Uvicorn x2,  │                                      │(Simulations /│
│ Port 8000)   │                                      │ Forecasting) │
└──┬───┬───┬───┘                                      └──────┬───────┘
   │   │   │                                                 │
   │   │   └─────────────────────────┐                       │
   │   └───────────────┐             │                       │
   ▼                   ▼             ▼                       ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐               │
│PostgreSQL 16 │ │ Neo4j 5  │ │   Redis 7    │<──────────────┘
│(Port 5432,   │ │ (Bolt    │ │ (Port 6379,  │
│ NO HOST PORT)│ │  NO HOST)│ │ NO HOST PORT)│
└──────────────┘ └──────────┘ └──────────────┘
```

### Key Security & Isolation Guarantees
1. **Zero Public Database Exposure**: `postgres`, `neo4j`, and `redis` use Docker Compose `expose` instead of `ports`. Their ports are physically unreachable from outside the host.
2. **Sole Ingress Point**: `caddy` is the only container binding to public host ports `80` and `443` (TCP and UDP/QUIC).
3. **Internal Private Bridge**: All services communicate via container DNS aliases (`postgres`, `redis`, `neo4j`, `backend`) over `supplychain_production_net`.

---

## 2. File-by-File Breakdown

| File Path | Component | Purpose |
| :--- | :--- | :--- |
| `infra/docker/Caddyfile` | Ingress Proxy | Reverse proxy routing `api.{$DOMAIN}` to `backend:8000`, HSTS, automatic SSL, access logs. |
| `infra/docker/backend.Dockerfile` | ASGI & Worker Container | Python 3.11-slim, non-root `appuser` (UID 10001), healthcheck probe, multi-worker Uvicorn. |
| `infra/docker-compose.production.yml` | Orchestration | Production composition defining Caddy, FastAPI, Postgres, Neo4j, Redis, Celery, and volumes. |
| `infra/env/.env.production.example` | Environment Template | Documented template with placeholders for secrets, CORS origins, and domain configuration. |
| `scripts/deploy_production.sh` | Deployment Runner | Automation script validating secrets, building images, running migrations, and checking health. |
| `scripts/backup_production.sh` | Backup Automation | Non-destructive automated backups for PostgreSQL (pg_dump) and Neo4j, with 7-day retention. |

---

## 3. Environment Variables Reference

| Variable | Required | Production Value / Pattern | Description |
| :--- | :---: | :--- | :--- |
| `DOMAIN` | **YES** | `yourdomain.com` | Public root domain for API subdomain `api.${DOMAIN}`. |
| `ACME_EMAIL` | **YES** | `admin@yourdomain.com` | Email for Let's Encrypt expiry and certificate renewal notices. |
| `ENVIRONMENT` | **YES** | `production` | Enables strict production security (enforces JWT length & blocks dev keys). |
| `PORT` | **YES** | `8000` | Port for Uvicorn ASGI server. |
| `DEBUG` | **YES** | `false` | Disables debug stack traces in API responses. |
| `LOG_LEVEL` | **YES** | `INFO` | Structured JSON log verbosity. |
| `CORS_ORIGINS` | **YES** | `https://frontend-pi-hazel-83.vercel.app` | Comma-separated list of authorized browser origins. |
| `JWT_SECRET` | **YES** | Cryptographic key (>= 32 chars) | Secret key for signing HS256 tokens. Fallback rejected in production. |
| `JWT_ALGORITHM` | Optional | `HS256` | JWT signing algorithm. |
| `POSTGRES_USER` | **YES** | `supplychain` | PostgreSQL database username. |
| `POSTGRES_PASSWORD` | **YES** | Secure password (>= 24 chars) | PostgreSQL password. |
| `POSTGRES_DB` | **YES** | `supplychain` | Primary database name. |
| `REDIS_PASSWORD` | **YES** | Secure password (>= 24 chars) | Redis authentication token (`requirepass`). |
| `NEO4J_USERNAME` | **YES** | `neo4j` | Graph database administrator account. |
| `NEO4J_PASSWORD` | **YES** | Secure password (>= 24 chars) | Neo4j password. |
| `CELERY_WORKER_CONCURRENCY` | Optional | `2` | Number of worker processes per worker container. |
| `LLM_MODE` | **YES** | `live` or `mock` | Set `live` for real LLM inference, or `mock` for deterministic testing. |
| `OPENAI_API_KEY` | Conditional | `sk-...` | Required if `LLM_MODE=live` and OpenAI is used. |
| `RATE_LIMIT_ENABLED` | Optional | `true` | Tiered request rate limiting enforcement. |

---

## 4. Secret Generation Commands

Run these commands on your local machine or terminal to generate strong cryptographic secrets:

```bash
# 1. JWT Signing Key (Cryptographically secure URL-safe 32-byte string)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. PostgreSQL Password (32-character hexadecimal token)
python -c "import secrets; print(secrets.token_hex(16))"

# 3. Redis Auth Password (32-character hexadecimal token)
python -c "import secrets; print(secrets.token_hex(16))"

# 4. Neo4j Password (32-character hexadecimal token)
python -c "import secrets; print(secrets.token_hex(16))"
```

---

## 5. VPS Prerequisites & Sizing

### Minimum Host Sizing
- **vCPU**: 4 cores
- **RAM**: 8 GB (Neo4j requires ~2GB heap/pagecache, PostgreSQL requires ~1GB, Backend + Celery ~1.5GB)
- **Disk**: 80 GB – 160 GB NVMe SSD
- **Operating System**: Ubuntu 24.04 LTS (x86_64 or ARM64)

### Recommended Cloud VPS Options
- **Hetzner Cloud**: `CPX31` (4 vCPU, 8 GB RAM, 160 GB NVMe) &rarr; **~€13.50/month**
- **DigitalOcean**: Basic Droplet (4 vCPU, 8 GB RAM, 160 GB SSD) &rarr; **~$48.00/month**
- **AWS EC2**: `t4g.xlarge` (4 vCPU ARM64, 16 GB RAM) &rarr; **~$45.00/month**

### Host Linux Kernel Adjustments
For high-concurrency Redis and Neo4j performance, execute on the VPS:
```bash
# Enable memory overcommit for Redis background saves
echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf

# Increase max open files limit
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Apply sysctl settings
sudo sysctl -p
```

---

## 6. Docker Installation Prerequisites

On a fresh Ubuntu 24.04 LTS VPS, install official Docker Engine and Docker Compose V2:

```bash
# 1. Remove conflicting packages
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove -y $pkg || true; done

# 2. Add Docker's official GPG key
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 3. Add the repository to Apt sources
echo   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu   $(. /etc/os-release && echo "$VERSION_CODENAME") stable" |   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. Install Docker CE and Docker Compose Plugin
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. Enable and start Docker service
sudo systemctl enable --now docker
```

---

## 7. DNS Requirements

Before launching Caddy, create the following DNS records in your domain registrar / Cloudflare dashboard:

| Record Type | Host / Name | Target / Value | TTL | Proxy Status |
| :---: | :--- | :--- | :---: | :---: |
| **A** | `api.yourdomain.com` | `<YOUR_VPS_PUBLIC_IP>` | Auto / 300s | DNS Only (Disable Cloudflare proxy initially for ACME) |

---

## 8. Deployment Commands (Step-by-Step)

### Step 1: Clone Repository
```bash
git clone https://github.com/HIT-ICES/SupplyChainAgent.git /opt/supplychain
cd /opt/supplychain
```

### Step 2: Configure Production Environment
```bash
cp infra/env/.env.production.example infra/env/.env.production
chmod 600 infra/env/.env.production
nano infra/env/.env.production
# (Paste generated secrets, DOMAIN, ACME_EMAIL)
```

### Step 3: Run Production Deployment Script
```bash
chmod +x scripts/deploy_production.sh scripts/backup_production.sh
./scripts/deploy_production.sh
```

---

## 9. Database Migration Commands

Alembic migrations run automatically during deployment via `scripts/deploy_production.sh`.  
To run migrations manually at any time:

```bash
# Upgrade to head schema
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production   run --rm backend alembic -c backend/alembic.ini upgrade head

# Check current migration revision
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production   run --rm backend alembic -c backend/alembic.ini current

# Inspect migration history
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production   run --rm backend alembic -c backend/alembic.ini history --verbose
```

---

## 10. Health Verification & Probe Validation

Verify the live API using `curl`:

```bash
# 1. Test basic process liveness
curl -I https://api.yourdomain.com/health
# Expected: HTTP/2 200 OK

# 2. Test granular dependency readiness
curl -s https://api.yourdomain.com/ready | jq .
# Expected output:
# {
#   "status": "ready",
#   "dependencies": {
#     "postgres": {"status": "healthy", "latency_ms": 1.8},
#     "neo4j": {"status": "healthy"},
#     "redis": {"status": "healthy", "latency_ms": 0.4},
#     "celery": {"status": "healthy"},
#     "llm": {"status": "healthy"}
#   }
# }

# 3. Test CORS preflight from Vercel frontend
curl -I -X OPTIONS https://api.yourdomain.com/api/v1/suppliers   -H "Origin: https://frontend-pi-hazel-83.vercel.app"   -H "Access-Control-Request-Method: GET"
# Expected: Access-Control-Allow-Origin: https://frontend-pi-hazel-83.vercel.app
```

---

## 11. Log Inspection

View structured JSON logs across services:

```bash
# Follow all container logs in real time
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f

# Follow FastAPI backend logs only
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f backend

# Follow Caddy access and TLS logs
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f caddy

# Follow Celery worker task execution
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production logs -f celery_worker
```

---

## 12. Backup Procedure & Cron Setup

### Manual Backup Execution
```bash
sudo ./scripts/backup_production.sh
```

### Automated Nightly Cron
Add to the host root crontab:
```bash
sudo crontab -e
# Add line: Run backup every day at 02:00 UTC
0 2 * * * /opt/supplychain/scripts/backup_production.sh >> /var/log/supplychain_backup.log 2>&1
```

### Restoration Runbook
```bash
# Restore PostgreSQL dump
cat /var/backups/supplychain/<TIMESTAMP>/postgres_supplychain_*.dump |   docker exec -i supplychain_postgres pg_restore -U supplychain -d supplychain --clean --if-exists
```

---

## 13. Rollback Procedure

If a deployment contains critical issues:

```bash
# 1. Revert code to previous Git commit or tag
git checkout <PREVIOUS_STABLE_COMMIT>

# 2. Downgrade database schema by 1 revision
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production   run --rm backend alembic -c backend/alembic.ini downgrade -1

# 3. Rebuild and restart services
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production up -d --build
```

---

## 14. Controlled Shutdown & Restart Procedure

```bash
# Graceful restart of all services
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production restart

# Stop all services safely (preserves persistent volumes)
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production down

# Start services back up
docker compose -f infra/docker-compose.production.yml --env-file infra/env/.env.production up -d
```

---

## 15. Production Security Checklist

- [ ] `infra/env/.env.production` has permissions `600` (`chmod 600`).
- [ ] `JWT_SECRET` is at least 32 cryptographically random characters.
- [ ] No database ports (`5432`, `6379`, `7474`, `7687`) are exposed to the public internet.
- [ ] Caddy serves HTTPS with valid Let's Encrypt certificates on port 443.
- [ ] UFW firewall is enabled on the VPS (`sudo ufw allow 22,80,443/tcp && sudo ufw enable`).
- [ ] SSH password authentication is disabled on the VPS (`PasswordAuthentication no` in `/etc/ssh/sshd_config`).
- [ ] CORS is restricted to `https://frontend-pi-hazel-83.vercel.app`.
- [ ] Production mode disables debug stack traces (`DEBUG=false`).
