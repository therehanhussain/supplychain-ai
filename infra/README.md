# Infrastructure Configurations

This directory contains containerization, orchestration, and cloud infrastructure definitions for SupplyChainAgent.

- `Dockerfile`: Production multi-stage backend container definition.
- `docker-compose.production.yml`: Local production-like multi-container stack (FastAPI, Celery, PostgreSQL, Neo4j, Redis).
