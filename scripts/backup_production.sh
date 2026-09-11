#!/usr/bin/env bash
# ==============================================================================
# Production Backup Script for SupplyChainAgent
# Creates compressed, timestamped backups of PostgreSQL and Neo4j data volumes.
# Implements a 7-day retention policy. DOES NOT CONTAIN SECRETS.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/infra/env/.env.production"

# Backup directory destination
BACKUP_ROOT="${BACKUP_DIR:-/var/backups/supplychain}"
TIMESTAMP="$(date -u +"%Y%m%d_%H%M%SZ")"
TARGET_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

echo "========================================================================"
echo " SupplyChainAgent Automated Backup"
echo " Timestamp: ${TIMESTAMP}"
echo " Destination: ${TARGET_DIR}"
echo "========================================================================"

mkdir -p "${TARGET_DIR}"

if [ -f "${ENV_FILE}" ]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
fi

DB_USER="${POSTGRES_USER:-supplychain}"
DB_NAME="${POSTGRES_DB:-supplychain}"

# 1. PostgreSQL Logical Dump
echo "[+] Creating PostgreSQL logical backup via pg_dump..."
PG_DUMP_FILE="${TARGET_DIR}/postgres_${DB_NAME}_${TIMESTAMP}.dump"
if docker ps --format '{{.Names}}' | grep -q "^supplychain_postgres$"; then
    docker exec -t supplychain_postgres pg_dump -U "${DB_USER}" -Fc "${DB_NAME}" > "${PG_DUMP_FILE}"
    echo "    -> PostgreSQL backup saved (${PG_DUMP_FILE}, $(du -h "${PG_DUMP_FILE}" | cut -f1))"
else
    echo "[-] WARNING: supplychain_postgres container is not running. Skipping live pg_dump."
fi

# 2. Neo4j Graph Backup Strategy
echo "[+] Snapshotting Neo4j graph state..."
NEO_SNAPSHOT_FILE="${TARGET_DIR}/neo4j_data_${TIMESTAMP}.tar.gz"
if docker volume inspect supplychain_neo4j_production_data >/dev/null 2>&1; then
    docker run --rm \
        -v supplychain_neo4j_production_data:/data:ro \
        -v "${TARGET_DIR}":/backup \
        alpine tar -czf "/backup/neo4j_data_${TIMESTAMP}.tar.gz" -C /data .
    echo "    -> Neo4j volume snapshot saved (${NEO_SNAPSHOT_FILE}, $(du -h "${NEO_SNAPSHOT_FILE}" | cut -f1))"
else
    echo "[-] WARNING: supplychain_neo4j_production_data volume not found. Skipping Neo4j snapshot."
fi

# 3. Retention Cleanup (Prune snapshots older than 7 days)
echo "[+] Enforcing 7-day retention policy..."
if [ -d "${BACKUP_ROOT}" ]; then
    find "${BACKUP_ROOT}" -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
    echo "    -> Retention pruning completed."
fi

echo "========================================================================"
echo " Backup Completed Successfully"
echo " Files Stored in: ${TARGET_DIR}"
echo "========================================================================"
ls -lh "${TARGET_DIR}"
