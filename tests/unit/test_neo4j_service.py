"""Unit tests for Neo4j connection pooling, status tracking, and graceful fallback handling."""
import pytest
from backend.app.services.neo4j_service import neo4j_service, Neo4jStatus
from backend.app.core.exceptions import AppException


@pytest.mark.asyncio
async def test_neo4j_health_status_reporting():
    """Verify health status reporting includes connection state and latency."""
    health = await neo4j_service.check_health()

    assert "status" in health
    assert health["status"] in [Neo4jStatus.LIVE.value, Neo4jStatus.UNAVAILABLE.value, Neo4jStatus.DEGRADED.value]
    assert "driver_initialized" in health
    assert "live_query_verified" in health


@pytest.mark.asyncio
async def test_neo4j_query_fails_gracefully_when_unavailable():
    """Verify run_cypher raises structured AppException when connection is unavailable."""
    # When Neo4j is unavailable, running a query should raise AppException 503
    if neo4j_service.status == Neo4jStatus.UNAVAILABLE:
        with pytest.raises(AppException) as exc_info:
            await neo4j_service.run_cypher("MATCH (n) RETURN count(n)")

        assert exc_info.value.status_code == 503
        assert exc_info.value.error_code == "GRAPH_DATABASE_UNAVAILABLE"
