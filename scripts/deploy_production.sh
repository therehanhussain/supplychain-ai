#!/usr/bin/env bash
# ==============================================================================
# Production Deployment Script for SupplyChainAgent
# Manages zero-downtime startup, health inspection, and database migration.
# DOES NOT CONTAIN SECRETS. Reads all values from infra/env/.env.production.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infra/docker-compose.production.yml"
ENV_FILE="${ROOT_DIR}/infra/env/.env.production"

echo "========================================================================"
echo " Starting SupplyChainAgent Production Deployment"
echo " Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "========================================================================"

# 1. Prerequisite Validation
if [ ! -f "${ENV_FILE}" ]; then
    echo "[-] ERROR: Production environment file not found at ${ENV_FILE}"
    echo "    Please create it from template: cp infra/env/.env.production.example infra/env/.env.production"
    exit 1
fi

# Source environment variables for validation checks
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# Guard against placeholder values
FAIL_VALIDATION=0
check_placeholder() {
    local var_name="$1"
    local var_val="${!var_name:-}"
    if [ -z "${var_val}" ] || [[ "${var_val}" == *"PLACEHOLDER"* ]]; then
        echo "[-] ERROR: Variable ${var_name} is empty or still contains PLACEHOLDER text."
        FAIL_VALIDATION=1
    fi
}

check_placeholder "JWT_SECRET"
check_placeholder "POSTGRES_PASSWORD"
check_placeholder "REDIS_PASSWORD"
check_placeholder "NEO4J_PASSWORD"

# Domain validation with support for Domainless Bootstrap Mode
BOOTSTRAP_MODE_ACTIVE=0
if [ "${1:-}" = "--bootstrap" ] || [ "${BOOTSTRAP_MODE:-false}" = "true" ]; then
    BOOTSTRAP_MODE_ACTIVE=1
fi

if [ -z "${DOMAIN:-}" ] || [[ "${DOMAIN:-}" == *"PLACEHOLDER"* ]] || [[ "${DOMAIN:-}" == "example.com" ]]; then
    if [ ${BOOTSTRAP_MODE_ACTIVE} -eq 1 ]; then
        echo "[!] NOTICE: Running in DOMAINLESS BOOTSTRAP MODE (--bootstrap)."
        echo "    Caddy will serve on HTTP (:80) for host verification without public TLS certificate acquisition."
        echo "    Full production HTTPS will be activated once DOMAIN is set and DNS is pointed."
        export SITE_ADDRESS="${SITE_ADDRESS:-:80}"
    else
        echo "[-] ERROR: Variable DOMAIN is empty, placeholder, or default (example.com)."
        echo "    To deploy with automated HTTPS/TLS, set DOMAIN to your real registered domain in ${ENV_FILE}."
        echo "    To test on a fresh VPS before domain purchase, run: ./scripts/deploy_production.sh --bootstrap"
        FAIL_VALIDATION=1
    fi
fi

if [ ${FAIL_VALIDATION} -ne 0 ]; then
    echo "[-] Aborting deployment due to missing or placeholder secrets."
    exit 1
fi

if [ ${#JWT_SECRET} -lt 32 ]; then
    echo "[-] ERROR: JWT_SECRET must be at least 32 characters long."
    exit 1
fi

echo "[+] Pre-flight environment validation passed."

# 2. Build and Pull Images
echo "[+] Pulling base images and building backend containers..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull postgres redis neo4j caddy || true
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" build backend celery_worker

# 3. Start Data Tier (PostgreSQL, Redis, Neo4j)
echo "[+] Starting auxiliary persistence services (PostgreSQL, Redis, Neo4j)..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d postgres redis neo4j

# 4. Wait for Database Healthchecks
echo "[+] Awaiting healthy state from PostgreSQL, Redis, and Neo4j..."
wait_for_health() {
    local service="$1"
    local max_wait=60
    local elapsed=0
    echo -n "    Waiting for ${service} to become healthy..."
    until [ "$(docker inspect --format='{{.State.Health.Status}}' "supplychain_${service}" 2>/dev/null || echo "starting")" = "healthy" ]; do
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
        if [ ${elapsed} -ge ${max_wait} ]; then
            echo " [TIMED OUT]"
            echo "[-] ERROR: Service supplychain_${service} failed to become healthy within ${max_wait}s."
            docker logs --tail 30 "supplychain_${service}"
            exit 1
        fi
    done
    echo " [HEALTHY]"
}

wait_for_health "postgres"
wait_for_health "redis"
wait_for_health "neo4j"

# 5. Execute Alembic Database Migrations
echo "[+] Executing database schema migrations (Alembic)..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" run --rm backend alembic -c backend/alembic.ini upgrade head

# 6. Start Application Tier (FastAPI, Celery, Caddy)
echo "[+] Starting application tier (FastAPI backend, Celery worker, Caddy ingress)..."
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d backend celery_worker caddy

# 7. Wait for Backend Healthcheck
wait_for_health "backend"

# 8. Deployment Status Report
echo "========================================================================"
echo " SupplyChainAgent Production Deployment Completed Successfully"
if [ ${BOOTSTRAP_MODE_ACTIVE} -eq 1 ]; then
    echo " Ingress Endpoint: http://<VPS_PUBLIC_IP> (Bootstrap Mode — Plain HTTP on Port 80)"
    echo " Notice: Configure DOMAIN and DNS A-record when ready for automated TLS."
else
    echo " Ingress Endpoint: https://${SITE_ADDRESS:-api.${DOMAIN}}"
fi
echo " CORS Origin Authorized: ${CORS_ORIGINS}"
echo "========================================================================"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps
