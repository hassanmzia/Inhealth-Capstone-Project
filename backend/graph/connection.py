"""
Neo4j driver connection with retry logic and connection pooling.
Used for medical knowledge graph queries (drug interactions, disease relationships).
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from django.conf import settings

logger = logging.getLogger("graph")

# Neo4j driver — lazy initialized
_driver = None
_driver_lock = __import__("threading").Lock()


def get_driver():
    """Get or create the Neo4j driver (singleton with retry)."""
    global _driver
    if _driver is None:
        with _driver_lock:
            if _driver is None:  # Double-checked locking
                _driver = _create_driver_with_retry()
    return _driver


def _create_driver_with_retry(max_retries: int = 5, delay: float = 2.0):
    """Create Neo4j driver with exponential backoff retry."""
    from neo4j import GraphDatabase, basic_auth, exceptions as neo4j_exc

    uri = settings.NEO4J_URI
    user = settings.NEO4J_USER
    password = settings.NEO4J_PASSWORD

    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                uri,
                auth=basic_auth(user, password),
                max_connection_lifetime=3600,  # 1 hour
                max_connection_pool_size=50,
                connection_acquisition_timeout=30,
            )
            # Verify connectivity
            driver.verify_connectivity()
            logger.info(f"Neo4j connected to {uri}")
            return driver
        except Exception as e:
            wait = delay * (2 ** attempt)
            logger.warning(f"Neo4j connection attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait:.1f}s")
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                logger.error(f"Could not connect to Neo4j after {max_retries} attempts")
                raise


@contextmanager
def get_session(database: str = "neo4j") -> Generator:
    """Context manager for Neo4j sessions."""
    driver = get_driver()
    session = driver.session(database=database)
    try:
        yield session
    finally:
        session.close()


def run_query(cypher: str, parameters: Dict = None, database: str = "neo4j") -> List[Dict]:
    """Execute a Cypher query and return results as a list of dicts."""
    with get_session(database=database) as session:
        result = session.run(cypher, parameters or {})
        return [record.data() for record in result]


def run_write_query(cypher: str, parameters: Dict = None, database: str = "neo4j") -> List[Dict]:
    """Execute a write Cypher query within a transaction."""
    with get_session(database=database) as session:
        return session.execute_write(lambda tx: [r.data() for r in tx.run(cypher, parameters or {})])


def close_driver():
    """Close the Neo4j driver (call on application shutdown)."""
    global _driver
    if _driver:
        _driver.close()
        _driver = None
        logger.info("Neo4j driver closed")


def initialize_schema():
    """Create Neo4j indexes and constraints for the knowledge graph."""
    schema_queries = [
        # Drug nodes
        "CREATE CONSTRAINT drug_rxnorm IF NOT EXISTS FOR (d:Drug) REQUIRE d.rxnorm IS UNIQUE",
        "CREATE CONSTRAINT disease_icd10 IF NOT EXISTS FOR (d:Disease) REQUIRE d.icd10 IS UNIQUE",
        "CREATE CONSTRAINT symptom_id IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE",
        "CREATE CONSTRAINT gene_id IF NOT EXISTS FOR (g:Gene) REQUIRE g.id IS UNIQUE",
        # Indexes for performance
        "CREATE INDEX drug_name IF NOT EXISTS FOR (d:Drug) ON (d.name)",
        "CREATE INDEX disease_name IF NOT EXISTS FOR (d:Disease) ON (d.name)",
        "CREATE INDEX interaction_severity IF NOT EXISTS FOR ()-[r:INTERACTS_WITH]-() ON (r.severity)",
    ]

    try:
        with get_session() as session:
            for query in schema_queries:
                try:
                    session.run(query)
                except Exception as e:
                    logger.warning(f"Schema query warning (may already exist): {e}")
        logger.info("Neo4j schema initialized")
    except Exception as e:
        logger.error(f"Neo4j schema initialization failed: {e}")
