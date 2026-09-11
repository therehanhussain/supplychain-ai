"""Neo4j Graph Database Service Layer.

Provides topological graph queries, bill-of-materials traversal, and industry chain
statistics with graceful fallback to cached topology datasets for local dev/testing.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.config import settings
from backend.app.core.logging import logger

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FALLBACK_TOPOLOGY_PATH = REPO_ROOT / "neo4j" / "industry_test.json"


class Neo4jService:
    """Service handling multi-tier supply chain graph queries."""

    def __init__(self):
        self._driver = None
        self._initialized = False

    def _get_driver(self):
        """Lazy initialization of Neo4j driver."""
        if not self._initialized:
            self._initialized = True
            if settings.NEO4J_URI and settings.NEO4J_PASSWORD:
                try:
                    from neo4j import GraphDatabase
                    self._driver = GraphDatabase.driver(
                        settings.NEO4J_URI,
                        auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                    )
                    logger.info("Connected to Neo4j graph database.")
                except Exception as e:
                    logger.warning(f"Neo4j connection failed ({e}). Fallback to static topology active.")
                    self._driver = None
        return self._driver

    def close(self):
        if self._driver:
            self._driver.close()

    def get_topology_data(self) -> Dict[str, Any]:
        """Fetch full multi-tier supply chain network topology."""
        driver = self._get_driver()
        if driver:
            try:
                with driver.session() as session:
                    result = session.run("""
                        MATCH (s)-[r:SUPPLIES]->(c)
                        RETURN s.name AS supplier, c.name AS consumer,
                               r.material_name AS material, r.supply_price AS price,
                               r.available_inventory AS inventory, r.usage_ratio AS usage_ratio
                    """)
                    records = [dict(record) for record in result]
                    if records:
                        return {"source": "neo4j", "relationships": records}
            except Exception as e:
                logger.warning(f"Failed to query Neo4j: {e}. Using fallback dataset.")

        # Fallback to local JSON topology
        return self._load_fallback_topology()

    def get_level_statistics(self) -> List[Dict[str, Any]]:
        """Retrieve aggregated node and profit metrics per industry tier."""
        driver = self._get_driver()
        if driver:
            try:
                with driver.session() as session:
                    result = session.run("""
                        CALL db.labels() YIELD label
                        WHERE label CONTAINS 'level' AND label CONTAINS 'company'
                        RETURN label
                        ORDER BY label
                    """)
                    labels = [r["label"] for r in result]
                    stats = []
                    for label in labels:
                        tier_res = session.run(f"""
                            MATCH (c:{label})
                            RETURN '{label}' as label,
                                   count(c) as company_count,
                                   sum(c.product_count) as product_count,
                                   avg(c.avg_profit_margin) as avg_profit
                        """).single()
                        if tier_res and tier_res["company_count"] > 0:
                            stats.append(dict(tier_res))
                    if stats:
                        return stats
            except Exception as e:
                logger.warning(f"Neo4j level stats failed: {e}. Using fallback stats.")

        # Static fallback stats
        return [
            {"label": "level1_company", "company_count": 4, "product_count": 8, "avg_profit": 15.2},
            {"label": "level2_company", "company_count": 6, "product_count": 12, "avg_profit": 18.5},
            {"label": "level3_company", "company_count": 6, "product_count": 10, "avg_profit": 22.1},
        ]

    def _load_fallback_topology(self) -> Dict[str, Any]:
        """Load static topology fixture when Neo4j is offline."""
        if FALLBACK_TOPOLOGY_PATH.exists():
            try:
                with open(FALLBACK_TOPOLOGY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {"source": "fallback_file", "topology": data}
            except Exception as e:
                logger.error(f"Error reading fallback topology file: {e}")
        return {"source": "empty", "topology": {}}


neo4j_service = Neo4jService()
