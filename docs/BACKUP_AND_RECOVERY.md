# SupplyChainAgent: Backup & Disaster Recovery Runbook

**Document Version:** 1.0.0  
**Phase:** Phase 5 — Production Integration & Hardening  
**Target RTO:** < 30 Minutes | **Target RPO:** < 1 Hour  

---

## 1. Resilience Objectives & Recovery Targets

| Tier | Component | RPO (Data Loss Tolerance) | RTO (Restoration Speed) | Strategy |
|:---|:---|:---:|:---:|:---|
| **Tier 1** | **PostgreSQL** (Core Persistence) | **< 15 minutes** | **< 30 minutes** | Continuous WAL archiving + Hourly logical dumps (`pg_dump`) + Daily cloud snapshots |
| **Tier 2** | **Neo4j** (Graph Topology) | **< 24 hours** | **< 45 minutes** | Daily `neo4j-admin database dump` + Configuration state replay |
| **Tier 3** | **Redis** (Broker & Cache) | **< 1 hour** | **< 10 minutes** | Combined RDB snapshots + AOF (`appendfsync everysec`) |
| **Tier 4** | **MLflow** (Experiment Telemetry) | **< 24 hours** | **< 2 hours** | Relational metadata dump + S3/GCS artifact replication |

---

## 2. PostgreSQL Backup & Restore Procedures

### A. Automated Scheduled Backup (`pg_dump`)
Run via cron or Kubernetes CronJob every 6 hours:
```bash
# Export compressed binary custom-format dump
pg_dump \
  -h "${PGHOST:-localhost}" \
  -p "${PGPORT:-5432}" \
  -U "${PGUSER:-postgres}" \
  -F c -b -v \
  -f "/var/backups/postgres/supplychain_$(date +%Y%m%d_%H%M%S).dump" \
  "${PGDATABASE:-supplychain_production}"
```

### B. Restoration Procedure
1. Terminate active backend pool connections:
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE datname = 'supplychain_production' AND pid <> pg_backend_pid();
   ```
2. Re-create clean target database:
   ```bash
   dropdb -h localhost -U postgres supplychain_production
   createdb -h localhost -U postgres supplychain_production
   ```
3. Restore custom-format dump:
   ```bash
   pg_restore \
     -h localhost -U postgres \
     -d supplychain_production \
     -v --clean --if-exists \
     "/var/backups/postgres/supplychain_YYYYMMDD_HHMMSS.dump"
   ```
4. Verify schema migration consistency:
   ```bash
   python -m alembic current
   python -m alembic check
   ```

---

## 3. Neo4j Graph Database Backup & Restore

### A. Creating Graph Backup Dump
Using `neo4j-admin` CLI:
```bash
# Dump the active production graph database
neo4j-admin database dump neo4j \
  --to-path=/var/backups/neo4j/ \
  --overwrite-destination=true
```

### B. Restoring Graph Backup
1. Stop the target Neo4j instance:
   ```bash
   systemctl stop neo4j
   # or docker compose stop neo4j
   ```
2. Load database dump:
   ```bash
   neo4j-admin database load neo4j \
     --from-path=/var/backups/neo4j/ \
     --overwrite-destination=true
   ```
3. Restart Neo4j and re-verify constraints:
   ```bash
   systemctl start neo4j
   python backend/scripts/neo4j_init.py
   ```

---

## 4. Redis Cache & Queue Recovery

In production, Redis operates as a volatile cache and message broker. Data in transit is ephemeral.
* **AOF Enabled**: Ensure `appendonly yes` and `appendfsync everysec` in `redis.conf`.
* **Crash Recovery**: If Redis volume is corrupted:
  1. Flush stale broker queues: `redis-cli flushall`
  2. Restart Redis container: `docker compose restart redis`
  3. Restart backend workers to re-initialize task listeners.

---

## 5. Verification Drill Protocols

To guarantee operational readiness, disaster recovery drills should be executed quarterly:
1. Restore the most recent backup dump onto an isolated staging cluster.
2. Run `backend/scripts/verify_postgres.py` to confirm table counts, constraints, and indexes.
3. Run `pytest tests/integration/ -v` against the restored staging database.
4. Verify that total time elapsed conforms to the RTO (< 30 minutes).
