#!/usr/bin/env python3
"""
InHealth Chronic Care - Neo4j Knowledge Graph Seeder

Seeds the Neo4j knowledge graph from Cypher files.
Runs all *.cypher files in /database/neo4j/ in order.
"""

import os
import sys
import logging
import time
from pathlib import Path
from typing import Optional

# Third-party imports
try:
    from neo4j import GraphDatabase, exceptions as neo4j_exceptions
except ImportError:
    print("ERROR: neo4j package not installed. Run: pip install neo4j")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    # dotenv is optional - fall back to environment variables
    def load_dotenv(path=None):
        pass

# ============================================================
# Configuration
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load .env from project root
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")

CYPHER_DIR = PROJECT_DIR / "database" / "neo4j"


# ============================================================
# Neo4j Driver
# ============================================================
def create_driver(uri: str, username: str, password: str):
    """Create and verify Neo4j driver connection."""
    max_retries = 10
    retry_delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            driver = GraphDatabase.driver(
                uri,
                auth=(username, password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_timeout=30,
            )
            # Verify connectivity
            driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {uri}")
            return driver
        except neo4j_exceptions.ServiceUnavailable as e:
            if attempt < max_retries:
                logger.warning(
                    f"Neo4j not available (attempt {attempt}/{max_retries}): {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Neo4j after {max_retries} attempts")
                raise
        except neo4j_exceptions.AuthError as e:
            logger.error(f"Neo4j authentication failed: {e}")
            raise


def run_cypher_file(driver, filepath: Path, verbose: bool = False) -> dict:
    """
    Execute all Cypher statements in a file.

    Splits on semicolons, handles multi-line statements,
    and skips comment-only lines.

    Returns a dict with counts of successful and failed statements.
    """
    logger.info(f"Processing: {filepath.name}")

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on semicolons - each statement ends with ;
    raw_statements = content.split(";")

    statements = []
    for raw in raw_statements:
        # Remove leading/trailing whitespace
        stmt = raw.strip()
        # Skip empty statements and comment-only blocks
        if not stmt:
            continue
        # Remove comment lines for validation but keep for execution
        non_comment_lines = [
            line for line in stmt.splitlines()
            if line.strip() and not line.strip().startswith("//")
        ]
        if not non_comment_lines:
            continue
        statements.append(stmt)

    success_count = 0
    fail_count = 0
    skip_count = 0

    with driver.session(database="neo4j") as session:
        for i, statement in enumerate(statements, start=1):
            # Skip pure comment statements
            non_comment = "\n".join(
                line for line in statement.splitlines()
                if not line.strip().startswith("//")
            ).strip()

            if not non_comment:
                skip_count += 1
                continue

            try:
                result = session.run(non_comment)
                summary = result.consume()
                counters = summary.counters

                if verbose:
                    logger.debug(
                        f"  Statement {i}: "
                        f"nodes_created={counters.nodes_created}, "
                        f"relationships_created={counters.relationships_created}, "
                        f"properties_set={counters.properties_set}"
                    )
                success_count += 1
            except neo4j_exceptions.ClientError as e:
                # Constraint already exists / index already exists - OK to continue
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    logger.debug(f"  Statement {i}: Already exists (skipped)")
                    skip_count += 1
                else:
                    logger.warning(f"  Statement {i} failed: {e}")
                    if verbose:
                        logger.debug(f"  Failed statement:\n{non_comment[:200]}...")
                    fail_count += 1
            except Exception as e:
                logger.error(f"  Statement {i} unexpected error: {e}")
                fail_count += 1

    return {
        "success": success_count,
        "failed": fail_count,
        "skipped": skip_count,
        "total": len(statements)
    }


def get_cypher_files(cypher_dir: Path) -> list:
    """Get all .cypher files in order (by filename prefix)."""
    if not cypher_dir.exists():
        logger.error(f"Cypher directory not found: {cypher_dir}")
        return []

    files = sorted(cypher_dir.glob("*.cypher"))
    if not files:
        logger.warning(f"No .cypher files found in {cypher_dir}")

    return files


def get_graph_stats(driver) -> dict:
    """Get counts of nodes and relationships in the graph."""
    with driver.session(database="neo4j") as session:
        node_result = session.run("MATCH (n) RETURN count(n) AS count")
        node_count = node_result.single()["count"]

        rel_result = session.run("MATCH ()-[r]-() RETURN count(r) AS count")
        rel_count = rel_result.single()["count"]

        label_result = session.run(
            "CALL db.labels() YIELD label "
            "RETURN label ORDER BY label"
        )
        labels = [r["label"] for r in label_result]

        rel_type_result = session.run(
            "CALL db.relationshipTypes() YIELD relationshipType "
            "RETURN relationshipType ORDER BY relationshipType"
        )
        rel_types = [r["relationshipType"] for r in rel_type_result]

    return {
        "total_nodes": node_count,
        "total_relationships": rel_count,
        "node_labels": labels,
        "relationship_types": rel_types,
    }


def seed_graph(
    uri: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    cypher_dir: Optional[Path] = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> bool:
    """
    Main seeding function.

    Returns True if all files processed successfully.
    """
    uri = uri or NEO4J_URI
    username = username or NEO4J_USERNAME
    password = password or NEO4J_PASSWORD
    cypher_dir = cypher_dir or CYPHER_DIR

    logger.info("=" * 60)
    logger.info("InHealth Chronic Care - Neo4j Graph Seeder")
    logger.info("=" * 60)
    logger.info(f"Neo4j URI:    {uri}")
    logger.info(f"Cypher dir:   {cypher_dir}")
    logger.info(f"Dry run:      {dry_run}")
    logger.info("")

    # Get files to process
    files = get_cypher_files(cypher_dir)
    if not files:
        logger.error("No Cypher files to process")
        return False

    logger.info(f"Found {len(files)} Cypher files:")
    for f in files:
        logger.info(f"  - {f.name}")
    logger.info("")

    if dry_run:
        logger.info("DRY RUN mode - no changes will be made")
        return True

    # Connect to Neo4j
    driver = create_driver(uri, username, password)

    # Get initial stats
    initial_stats = get_graph_stats(driver)
    logger.info(f"Initial graph state:")
    logger.info(f"  Nodes: {initial_stats['total_nodes']}")
    logger.info(f"  Relationships: {initial_stats['total_relationships']}")
    logger.info("")

    # Process each file
    overall_success = True
    total_results = {"success": 0, "failed": 0, "skipped": 0, "total": 0}

    start_time = time.time()

    for cypher_file in files:
        file_start = time.time()
        results = run_cypher_file(driver, cypher_file, verbose=verbose)
        elapsed = time.time() - file_start

        total_results["success"] += results["success"]
        total_results["failed"] += results["failed"]
        total_results["skipped"] += results["skipped"]
        total_results["total"] += results["total"]

        status = "OK" if results["failed"] == 0 else "PARTIAL"
        logger.info(
            f"  {status}: {cypher_file.name} - "
            f"{results['success']} ok, {results['failed']} failed, "
            f"{results['skipped']} skipped ({elapsed:.1f}s)"
        )

        if results["failed"] > 0:
            overall_success = False

    elapsed_total = time.time() - start_time

    # Get final stats
    final_stats = get_graph_stats(driver)

    logger.info("")
    logger.info("=" * 60)
    logger.info("Seeding Complete")
    logger.info("=" * 60)
    logger.info(f"Total time: {elapsed_total:.1f}s")
    logger.info(
        f"Statements: {total_results['success']} ok, "
        f"{total_results['failed']} failed, "
        f"{total_results['skipped']} skipped"
    )
    logger.info("")
    logger.info("Graph stats after seeding:")
    logger.info(f"  Nodes:         {final_stats['total_nodes']} (was {initial_stats['total_nodes']})")
    logger.info(f"  Relationships: {final_stats['total_relationships']} (was {initial_stats['total_relationships']})")
    logger.info(f"  Node labels:   {', '.join(final_stats['node_labels'])}")
    logger.info(f"  Rel types:     {', '.join(final_stats['relationship_types'])}")

    driver.close()
    return overall_success


# ============================================================
# CLI
# ============================================================
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed InHealth Neo4j knowledge graph from Cypher files"
    )
    parser.add_argument(
        "--uri",
        default=NEO4J_URI,
        help=f"Neo4j connection URI (default: {NEO4J_URI})"
    )
    parser.add_argument(
        "--username",
        default=NEO4J_USERNAME,
        help=f"Neo4j username (default: {NEO4J_USERNAME})"
    )
    parser.add_argument(
        "--password",
        default=NEO4J_PASSWORD,
        help="Neo4j password"
    )
    parser.add_argument(
        "--cypher-dir",
        type=Path,
        default=CYPHER_DIR,
        help=f"Directory containing .cypher files (default: {CYPHER_DIR})"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed per-statement output"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files to process without executing"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Process a single specific .cypher file"
    )

    args = parser.parse_args()

    if args.file:
        # Process single file
        driver = create_driver(args.uri, args.username, args.password)
        results = run_cypher_file(driver, args.file, verbose=args.verbose)
        driver.close()
        logger.info(
            f"Done: {results['success']} ok, {results['failed']} failed, "
            f"{results['skipped']} skipped"
        )
        sys.exit(0 if results["failed"] == 0 else 1)
    else:
        success = seed_graph(
            uri=args.uri,
            username=args.username,
            password=args.password,
            cypher_dir=args.cypher_dir,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
        sys.exit(0 if success else 1)
