"""
Neo4j knowledge-graph tools.

Re-exports the core query_graph_database and check_drug_interactions tools
from base.tools and provides graph-specific helpers for relationship
exploration and drug-alternative lookups.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_core.tools import tool

from agents.base.tools import (  # noqa: F401 – re-exports
    check_drug_interactions,
    query_graph_database,
)

logger = logging.getLogger("inhealth.tools.graph")


@tool
def get_condition_relationships(condition_name: str, depth: int = 2) -> list:
    """
    Explore relationships for a clinical condition in the knowledge graph,
    returning connected drugs, symptoms, risk factors, and related conditions
    up to a given traversal depth.

    Args:
        condition_name: Name of the condition node (e.g., 'Type 2 Diabetes')
        depth: Maximum relationship traversal depth (default 2, max 4)

    Returns:
        List of related nodes with relationship type, direction, and properties.
    """
    try:
        depth = min(max(depth, 1), 4)
        cypher = (
            "MATCH path = (c:Condition {name: $name})-[*1..$depth]-(related) "
            "RETURN "
            "  [rel IN relationships(path) | type(rel)] AS relationship_types, "
            "  labels(related) AS related_labels, "
            "  related.name AS related_name, "
            "  related {.description, .severity, .prevalence} AS properties "
            "LIMIT 50"
        ).replace("$depth", str(depth))

        records = query_graph_database.invoke(
            {"cypher_query": cypher, "params": {"name": condition_name}}
        )
        return records

    except Exception as exc:
        logger.error("get_condition_relationships failed: %s", exc)
        return [{"error": str(exc)}]


@tool
def find_alternative_drugs(drug_name: str) -> list:
    """
    Find therapeutic alternatives for a given drug using the Neo4j knowledge
    graph.  Alternatives share the same drug class or indication and do not
    have contraindicated interactions with each other.

    Args:
        drug_name: Name of the drug to find alternatives for

    Returns:
        List of alternative drugs with name, drug_class, and shared indications.
    """
    try:
        cypher = """
        MATCH (d:Drug {name: $drug_name})-[:BELONGS_TO_CLASS]->(cls:DrugClass)
              <-[:BELONGS_TO_CLASS]-(alt:Drug)
        WHERE alt.name <> $drug_name
        OPTIONAL MATCH (alt)-[:INDICATED_FOR]->(ind:Condition)
              <-[:INDICATED_FOR]-(d)
        RETURN alt.name AS alternative,
               cls.name AS drug_class,
               COLLECT(DISTINCT ind.name) AS shared_indications
        ORDER BY SIZE(COLLECT(DISTINCT ind.name)) DESC
        LIMIT 10
        """
        records = query_graph_database.invoke(
            {"cypher_query": cypher, "params": {"drug_name": drug_name}}
        )
        return records

    except Exception as exc:
        logger.error("find_alternative_drugs failed: %s", exc)
        return [{"error": str(exc)}]


# All tools provided by this module
GRAPH_TOOLS = [
    query_graph_database,
    check_drug_interactions,
    get_condition_relationships,
    find_alternative_drugs,
]
