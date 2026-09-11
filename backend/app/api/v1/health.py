"""Health, Liveness, and Readiness Endpoints.

Provides container orchestration, dependency status, and observability probes.
"""

import time
from fastapi import APIRouter
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import AsyncSessionLocal
from backend.app.services.neo4j_service import neo4j_service, Neo4jStatus
from backend.app.schemas.health import HealthStatus, ReadyStatus, LiveStatus, ComponentHealth

router = APIRouter(tags=["Health & Probes"])


@router.get("/health", response_model=HealthStatus, summary="Liveness Health Check")
async def get_health():
    """Returns basic process health without failing if auxiliary dependencies are offline."""
    return HealthStatus(
        status="healthy",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/live", response_model=LiveStatus, summary="Liveness Probe")
async def get_liveness():
    """Kubernetes liveness probe indicating process is responsive."""
    return LiveStatus(status="alive")


@router.get("/ready", response_model=ReadyStatus, summary="Readiness Probe")
async def get_readiness():
    """Enterprise readiness probe inspecting database, graph, cache, worker, and LLM connections."""
    dependencies = {}
    all_ready = True

    # 1. Check PostgreSQL Database Connectivity
    start_t = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        latency = round((time.perf_counter() - start_t) * 1000, 2)
        dependencies["postgres"] = ComponentHealth(
            status="healthy",
            latency_ms=latency,
            message="PostgreSQL database query verified",
        )
    except Exception as e:
        latency = round((time.perf_counter() - start_t) * 1000, 2)
        if settings.ENVIRONMENT.lower() == "production":
            all_ready = False
            status_val = "unreachable"
        else:
            status_val = "degraded"
        dependencies["postgres"] = ComponentHealth(
            status=status_val,
            latency_ms=latency,
            message=f"Database connectivity failed: {str(e)[:100]}",
        )
    dependencies["database"] = dependencies["postgres"]

    # 2. Check Neo4j Graph Database
    if settings.NEO4J_URI:
        neo_status = neo4j_service.get_status()
        if neo_status.get("status") == Neo4jStatus.LIVE.value:
            dependencies["neo4j"] = ComponentHealth(
                status="healthy",
                message="Neo4j graph cluster verified",
            )
        else:
            dependencies["neo4j"] = ComponentHealth(
                status="degraded",
                message="Neo4j fallback mode active (cached topology)",
            )
    else:
        dependencies["neo4j"] = ComponentHealth(status="disabled", message="Neo4j URI not configured")

    # 3. Check Redis Cache & Broker
    if settings.REDIS_URL:
        redis_start = time.perf_counter()
        try:
            import redis.asyncio as aioredis
            client = aioredis.from_url(settings.REDIS_URL, socket_timeout=1.0)
            await client.ping()
            await client.aclose()
            dependencies["redis"] = ComponentHealth(
                status="healthy",
                latency_ms=round((time.perf_counter() - redis_start) * 1000, 2),
                message="Redis cache/broker ping verified",
            )
        except Exception as e:
            dependencies["redis"] = ComponentHealth(
                status="unreachable" if settings.ENVIRONMENT.lower() == "production" else "degraded",
                latency_ms=round((time.perf_counter() - redis_start) * 1000, 2),
                message=f"Redis unavailable: {str(e)[:80]}",
            )
    else:
        dependencies["redis"] = ComponentHealth(status="disabled", message="Redis URL not configured")

    # 4. Check Celery Worker Queue Broker
    if settings.REDIS_URL:
        dependencies["celery"] = ComponentHealth(
            status="healthy" if dependencies["redis"].status == "healthy" else "degraded",
            message=f"Celery worker broker linked (concurrency={settings.CELERY_WORKER_CONCURRENCY})",
        )
    else:
        dependencies["celery"] = ComponentHealth(status="disabled", message="Celery worker broker not configured")

    # 5. Check LLM Gateway
    llm_mode = settings.LLM_MODE.lower().strip()
    if llm_mode == "live":
        provider_name = "deepseek" if settings.DEEPSEEK_API_KEY else "openai"
        key = settings.DEEPSEEK_API_KEY if provider_name == "deepseek" else settings.OPENAI_API_KEY
        if key:
            dependencies["llm"] = ComponentHealth(
                status="healthy",
                message=f"Live LLM provider '{provider_name}' ({settings.DEFAULT_LLM_MODEL}) configured",
            )
        else:
            if settings.ENVIRONMENT.lower() == "production":
                all_ready = False
            dependencies["llm"] = ComponentHealth(
                status="unreachable",
                message=f"LLM mode is 'live' but API key for '{provider_name}' is missing",
            )
    else:
        dependencies["llm"] = ComponentHealth(
            status="simulated",
            message=f"LLM running in deterministic mock mode ({settings.DEFAULT_LLM_MODEL})",
        )

    # In production, require core dependencies; in dev, serve with degraded/fallback
    probe_status = "ready" if (all_ready or settings.ENVIRONMENT.lower() != "production") else "not_ready"
    return ReadyStatus(
        status=probe_status,
        dependencies=dependencies,
    )
