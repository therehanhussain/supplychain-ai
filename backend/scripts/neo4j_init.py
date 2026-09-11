"""Neo4j schema initialization script: creates constraints, indexes, and nodes.

Usage:
    python backend/scripts/neo4j_init.py
"""
import sys
from pathlib import Path

# Add project root to path
root_path = Path(__file__).resolve().parents[2]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from backend.app.core.config import settings
from backend.app.core.logging import logger

CONSTRAINTS_AND_INDEXES = [
    # Company uniqueness
    "CREATE CONSTRAINT uq_company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
    # Level-specific indexes
    "CREATE INDEX idx_company_level IF NOT EXISTS FOR (c:Company) ON (c.level_num)",
    # Material index
    "CREATE INDEX idx_material_id IF NOT EXISTS FOR ()-[r:SUPPLIES]-() ON (r.material_id)",
]


def init_neo4j_schema():
    """Execute Cypher migration DDL to initialize constraints and indexes."""
    print("Checking Neo4j connection...")
    try:
        from neo4j import GraphDatabase, basic_auth
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=basic_auth(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
        )
        driver.verify_connectivity()
        print(f"Connected to Neo4j at {settings.NEO4J_URI}")

        with driver.session(database=settings.NEO4J_DATABASE) as session:
            for ddl in CONSTRAINTS_AND_INDEXES:
                try:
                    session.run(ddl)
                    print(f"Applied: {ddl}")
                except Exception as ex:
                    print(f"Error applying '{ddl}': {ex}")

        driver.close()
        print("Neo4j schema initialization complete.")
    except Exception as e:
        print(f"Neo4j connection could not be established: {e}")
        print("Note: If Neo4j is not currently running, verify Docker container 'neo4j' is active.")


if __name__ == "__main__":
    init_neo4j_schema()
