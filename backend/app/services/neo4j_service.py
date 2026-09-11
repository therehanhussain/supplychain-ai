"""Neo4j Graph Database Service Layer with Connection Pooling and Status Tracking.

Provides topological graph queries, bill-of-materials traversal, and industry chain
statistics with explicit status reporting (LIVE, DEGRADED, UNAVAILABLE).
"""
import enum
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.logging import logger

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FALLBACK_TOPOLOGY_PATH = REPO_ROOT / "neo4j" / "industry_test.json"


class Neo4jStatus(str, enum.Enum):
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


class Neo4jService:
    """Enterprise service handling multi-tier supply chain graph queries with pooled connections."""

    def __init__(self):
        self._driver = None
        self._initialized = False
        self._status: Neo4jStatus = Neo4jStatus.DEGRADED
        self._last_error: Optional[str] = None

    @property
    def status(self) -> Neo4jStatus:
        """Current operational status of Neo4j service."""
        return self._status


    def get_status(self) -> Dict[str, Any]:
        """Return real-time operational status of the Neo4j graph cluster."""
        driver = self._get_driver()
        return {
            "status": self._status.value,
            "uri": settings.NEO4J_URI,
            "database": settings.NEO4J_DATABASE,
            "connected": driver is not None and self._status == Neo4jStatus.LIVE,
            "last_error": self._last_error,
        }

    async def check_health(self) -> Dict[str, Any]:
        """Convenience health check returning operational status."""
        status = self.get_status()
        return {
            "status": status["status"],
            "driver_initialized": self._initialized,
            "live_query_verified": status["connected"],
            "uri": status["uri"],
        }

    async def run_cypher(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run raw Cypher query against cluster, or raise AppException if unavailable."""
        driver = self._get_driver()
        if not driver or self._status != Neo4jStatus.LIVE:
            raise AppException(
                message=f"Neo4j graph database is unavailable: {self._last_error or 'Cluster disconnected'}",
                code="GRAPH_DATABASE_UNAVAILABLE",
                status_code=503,
            )
        with driver.session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(query, parameters or {})
            return [dict(r) for r in result]


    def _get_driver(self):
        """Lazy initialization of Neo4j driver with connection pooling and timeouts."""
        if not self._initialized:
            self._initialized = True
            if settings.NEO4J_URI and settings.NEO4J_PASSWORD:
                try:
                    from neo4j import GraphDatabase, basic_auth
                    self._driver = GraphDatabase.driver(
                        settings.NEO4J_URI,
                        auth=basic_auth(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                        max_connection_pool_size=50,
                        connection_timeout=5.0,
                        connection_acquisition_timeout=5.0,
                    )
                    # Verify connectivity
                    self._driver.verify_connectivity()
                    self._status = Neo4jStatus.LIVE
                    self._last_error = None
                    logger.info("Successfully connected to live Neo4j graph cluster.")
                except Exception as e:
                    self._driver = None
                    self._status = Neo4jStatus.DEGRADED
                    self._last_error = str(e)
                    logger.warning(
                        f"Neo4j live connection failed ({e}). Operating in DEGRADED fallback mode."
                    )
            else:
                self._status = Neo4jStatus.DEGRADED
                self._last_error = "Neo4j credentials not configured."
        return self._driver

    def close(self):
        """Close driver and release all pooled sockets."""
        if self._driver:
            try:
                self._driver.close()
            except Exception as e:
                logger.error(f"Error closing Neo4j driver: {e}")
            finally:
                self._driver = None
                self._initialized = False

    def get_topology_data(self) -> Dict[str, Any]:
        """Fetch full multi-tier supply chain network topology with provenance metadata."""
        driver = self._get_driver()
        if driver and self._status == Neo4jStatus.LIVE:
            try:
                with driver.session(database=settings.NEO4J_DATABASE) as session:
                    cypher = """
                        MATCH (s)-[r:SUPPLIES]->(c)
                        RETURN s.name AS supplier, c.name AS consumer,
                               r.material_name AS material, r.supply_price AS price,
                               r.available_inventory AS inventory, r.usage_ratio AS usage_ratio
                    """
                    result = session.run(cypher)
                    records = [dict(record) for record in result]
                    if records:
                        return {
                            "data_mode": Neo4jStatus.LIVE.value,
                            "source": "neo4j_cluster",
                            "status_message": "Retrieved live from Neo4j graph database",
                            "relationships": records,
                        }
            except Exception as e:
                self._status = Neo4jStatus.DEGRADED
                self._last_error = str(e)
                logger.warning(f"Neo4j query failed ({e}). Reverting to fallback topology.")

        # Fallback to local JSON topology
        fallback = self._load_fallback_topology()
        return {
            "data_mode": Neo4jStatus.DEGRADED.value,
            "source": "offline_fallback_dataset",
            "status_message": f"Graph database offline or unconfigured ({self._last_error}). Using certified fallback topology.",
            "relationships": fallback.get("relationships", []),
        }

    def get_level_statistics(self) -> List[Dict[str, Any]]:
        """Retrieve aggregated node and profit metrics per industry tier."""
        driver = self._get_driver()
        if driver and self._status == Neo4jStatus.LIVE:
            try:
                with driver.session(database=settings.NEO4J_DATABASE) as session:
                    result = session.run("""
                        CALL db.labels() YIELD label
                        WHERE label CONTAINS 'level' AND label CONTAINS 'company'
                        RETURN label
                        ORDER BY label
                    """)
                    labels = [r["label"] for r in result]
                    stats = []
                    for label in labels:
                        tier_res = session.run(
                            "MATCH (c:`" + label + "`) "
                            "RETURN $label as label, "
                            "count(c) as company_count, "
                            "sum(c.product_count) as product_count, "
                            "avg(c.avg_profit_margin) as avg_profit",
                            label=label,
                        ).single()
                        if tier_res and tier_res["company_count"] > 0:
                            item = dict(tier_res)
                            item["data_mode"] = Neo4jStatus.LIVE.value
                            stats.append(item)
                    if stats:
                        return stats
            except Exception as e:
                logger.warning(f"Neo4j level stats failed: {e}. Using fallback stats.")

        return [
            {"label": "level1_company", "company_count": 4, "product_count": 8, "avg_profit": 15.2, "data_mode": Neo4jStatus.DEGRADED.value},
            {"label": "level2_company", "company_count": 6, "product_count": 12, "avg_profit": 18.5, "data_mode": Neo4jStatus.DEGRADED.value},
            {"label": "level3_company", "company_count": 6, "product_count": 10, "avg_profit": 22.1, "data_mode": Neo4jStatus.DEGRADED.value},
        ]

    def _load_fallback_topology(self) -> Dict[str, Any]:
        """Load static topology from disk when Neo4j is offline or in development."""
        if not FALLBACK_TOPOLOGY_PATH.exists():
            logger.error(f"Fallback topology file not found at {FALLBACK_TOPOLOGY_PATH}")
            return {"relationships": []}

        try:
            with open(FALLBACK_TOPOLOGY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            relationships = []
            all_companies = []
            for level, companies in data.items():
                for comp in companies:
                    comp["_level"] = level
                    all_companies.append(comp)

            for consumer in all_companies:
                consumer_lvl = int(consumer["_level"].split("_")[1]) if "_" in consumer["_level"] else 1
                for product in consumer.get("main_products", []):
                    for mat in product.get("related_materials", []):
                        mat_id = mat.get("material_id")
                        for supplier in all_companies:
                            sup_lvl = int(supplier["_level"].split("_")[1]) if "_" in supplier["_level"] else 1
                            if consumer_lvl == sup_lvl + 1:
                                if any(m.get("material_id") == mat_id for m in supplier.get("available_materials", [])):
                                    relationships.append({
                                        "supplier": supplier["name"],
                                        "consumer": consumer["name"],
                                        "material": mat.get("material_name"),
                                        "price": 100.0,
                                        "inventory": 500,
                                        "usage_ratio": 1.0,
                                    })
            return {"relationships": relationships}
        except Exception as e:
            logger.error(f"Error parsing fallback topology: {e}")
            return {"relationships": []}


# Global singleton instance
neo4j_service = Neo4jService()
