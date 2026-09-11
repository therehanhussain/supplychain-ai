"""Supply Routes & Network Topology Endpoints (/api/v1/routes)."""

from fastapi import APIRouter
from backend.app.schemas.route import RouteTopologyResponse
from backend.app.services.neo4j_service import neo4j_service

router = APIRouter(prefix="/routes", tags=["Routes & Graph Topology"])


@router.get("", response_model=RouteTopologyResponse, summary="Get full supply chain graph topology")
@router.get("/topology", response_model=RouteTopologyResponse, summary="Get full supply chain graph topology")
async def get_network_topology():
    """Fetches multi-tier supply chain network graph for interactive visualization."""
    topo = neo4j_service.get_topology_data()
    stats = neo4j_service.get_level_statistics()
    return RouteTopologyResponse(
        source=topo.get("source", "fallback_file"),
        relationships=topo.get("relationships", []),
        tier_statistics=stats,
    )


@router.get("/statistics", summary="Get tier-level industry chain metrics")
async def get_tier_statistics():
    return neo4j_service.get_level_statistics()
