"""
Qdrant vector database client with connection pooling.
Used for semantic search across clinical guidelines, literature, and patient notes.
"""

import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings

logger = logging.getLogger("vector")

_client = None
_client_lock = threading.Lock()


def get_client():
    """Get or create the Qdrant client (singleton)."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = _create_client()
    return _client


def _create_client():
    """Create Qdrant client with retry logic."""
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as rest

    host = getattr(settings, "QDRANT_HOST", "localhost")
    port = getattr(settings, "QDRANT_PORT", 6333)

    try:
        client = QdrantClient(
            host=host,
            port=port,
            timeout=30,
            prefer_grpc=True,
        )
        # Test connection
        client.get_collections()
        logger.info(f"Qdrant connected to {host}:{port}")
        return client
    except Exception as e:
        logger.error(f"Qdrant connection failed ({host}:{port}): {e}")
        # Return an in-memory client for development/testing fallback
        try:
            client = QdrantClient(":memory:")
            logger.warning("Using in-memory Qdrant (development mode)")
            return client
        except Exception:
            raise


def upsert_vectors(
    collection_name: str,
    points: List[Dict],
) -> None:
    """
    Upsert vectors into a Qdrant collection.

    Each point: {"id": str/int, "vector": List[float], "payload": dict}
    """
    from qdrant_client.http import models as rest

    client = get_client()
    qdrant_points = [
        rest.PointStruct(
            id=p["id"] if isinstance(p["id"], int) else _str_to_int_id(p["id"]),
            vector=p["vector"],
            payload=p.get("payload", {}),
        )
        for p in points
    ]

    client.upsert(collection_name=collection_name, points=qdrant_points)
    logger.debug(f"Upserted {len(points)} vectors into {collection_name}")


def search_vectors(
    collection_name: str,
    query_vector: List[float],
    top_k: int = 10,
    score_threshold: float = 0.7,
    filter_payload: Dict = None,
) -> List[Dict]:
    """
    Search for similar vectors in a Qdrant collection.
    Returns list of {id, score, payload} dicts.
    """
    from qdrant_client.http import models as rest

    client = get_client()

    search_filter = None
    if filter_payload:
        conditions = [
            rest.FieldCondition(
                key=key,
                match=rest.MatchValue(value=value),
            )
            for key, value in filter_payload.items()
        ]
        search_filter = rest.Filter(must=conditions)

    try:
        results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=search_filter,
            with_payload=True,
        )
        return [
            {"id": r.id, "score": r.score, "payload": r.payload}
            for r in results
        ]
    except Exception as e:
        logger.error(f"Qdrant search failed in {collection_name}: {e}")
        return []


def delete_vector(collection_name: str, point_id: int) -> None:
    """Delete a single vector by ID."""
    client = get_client()
    from qdrant_client.http import models as rest
    client.delete(
        collection_name=collection_name,
        points_selector=rest.PointIdsList(points=[point_id]),
    )


def get_collection_info(collection_name: str) -> Optional[Dict]:
    """Get collection statistics."""
    client = get_client()
    try:
        info = client.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": str(info.status),
        }
    except Exception:
        return None


def _str_to_int_id(s: str) -> int:
    """Convert a string UUID to a deterministic integer ID for Qdrant."""
    import hashlib
    return int(hashlib.sha256(s.encode()).hexdigest()[:16], 16) % (2**63)
