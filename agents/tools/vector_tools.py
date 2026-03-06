"""
Qdrant vector search tools.

Re-exports the core vector_search tool from base.tools and adds
collection-specific convenience helpers for clinical guidelines and
PubMed abstract retrieval.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_core.tools import tool

from agents.base.tools import vector_search  # noqa: F401 – re-export

logger = logging.getLogger("inhealth.tools.vector")


@tool
def search_clinical_guidelines(query: str, top_k: int = 5) -> list:
    """
    Search the 'clinical_guidelines' Qdrant collection for evidence-based
    clinical guidelines relevant to a query.

    This is a convenience wrapper around vector_search that targets the
    clinical_guidelines collection and enriches results with a
    relevance-confidence label.

    Args:
        query: Natural language clinical question
        top_k: Number of top results (default 5)

    Returns:
        List of guideline documents with content, source, score, and
        relevance label.
    """
    try:
        results = vector_search.invoke(
            {"query": query, "collection": "clinical_guidelines", "top_k": top_k}
        )

        # Enrich with a human-readable relevance label
        for doc in results:
            score = doc.get("score", 0)
            if score >= 0.85:
                doc["relevance"] = "high"
            elif score >= 0.65:
                doc["relevance"] = "moderate"
            else:
                doc["relevance"] = "low"

        return results

    except Exception as exc:
        logger.error("search_clinical_guidelines failed: %s", exc)
        return [{"error": str(exc)}]


@tool
def search_pubmed_vectors(query: str, top_k: int = 5) -> list:
    """
    Search the 'pubmed_abstracts' Qdrant collection for PubMed literature
    semantically similar to the query.

    This is a convenience wrapper around vector_search that targets the
    pubmed_abstracts collection.

    Args:
        query: Natural language research question
        top_k: Number of top results (default 5)

    Returns:
        List of PubMed abstract snippets with content, source, and score.
    """
    try:
        results = vector_search.invoke(
            {"query": query, "collection": "pubmed_abstracts", "top_k": top_k}
        )
        return results

    except Exception as exc:
        logger.error("search_pubmed_vectors failed: %s", exc)
        return [{"error": str(exc)}]


# All tools provided by this module
VECTOR_TOOLS = [vector_search, search_clinical_guidelines, search_pubmed_vectors]
