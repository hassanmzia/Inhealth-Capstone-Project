"""
Embedding generation for the InHealth vector store.
Uses sentence-transformers locally with OpenAI API as fallback.
"""

import logging
from typing import List, Optional

logger = logging.getLogger("vector.embeddings")

# Model cache
_st_model = None
_st_lock = __import__("threading").Lock()

EMBEDDING_DIMENSION = 768
EMBEDDING_MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"


def get_sentence_transformer():
    """Lazy-load the sentence transformer model."""
    global _st_model
    if _st_model is None:
        with _st_lock:
            if _st_model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    _st_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
                    logger.info(f"Loaded sentence transformer: {EMBEDDING_MODEL_NAME}")
                except Exception as e:
                    logger.error(f"Failed to load sentence transformer: {e}")
                    _st_model = None
    return _st_model


def generate_embedding(text: str, use_openai_fallback: bool = True) -> Optional[List[float]]:
    """
    Generate an embedding for the given text.
    Primary: sentence-transformers (local)
    Fallback: OpenAI text-embedding API
    """
    if not text or not text.strip():
        return None

    # Truncate to model limits
    text = text[:8192]

    # Try sentence-transformers first
    model = get_sentence_transformer()
    if model is not None:
        try:
            embedding = model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"sentence-transformers encoding failed: {e}")

    # Fallback to OpenAI
    if use_openai_fallback:
        return _generate_openai_embedding(text)

    return None


def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[Optional[List[float]]]:
    """Generate embeddings for a batch of texts efficiently."""
    model = get_sentence_transformer()

    if model is not None:
        try:
            # Process in batches
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                embeddings = model.encode(batch, normalize_embeddings=True, show_progress_bar=False)
                all_embeddings.extend(embeddings.tolist())
            return all_embeddings
        except Exception as e:
            logger.warning(f"Batch encoding failed, falling back to individual: {e}")

    # Fallback: individual encoding
    return [generate_embedding(text) for text in texts]


def _generate_openai_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using OpenAI API."""
    try:
        from django.conf import settings
        import openai

        api_key = getattr(settings, "OPENAI_API_KEY", "")
        if not api_key:
            return None

        client = openai.OpenAI(api_key=api_key)
        response = client.embeddings.create(
            input=text[:8191],
            model=OPENAI_EMBEDDING_MODEL,
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"OpenAI embedding failed: {e}")
        return None


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    import math
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def rerank_results(query: str, results: List[dict], top_k: int = 5) -> List[dict]:
    """
    Rerank search results using cross-encoder for higher precision.
    Falls back to original order if cross-encoder unavailable.
    """
    try:
        from sentence_transformers import CrossEncoder
        cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

        # Create pairs for cross-encoder
        pairs = [(query, r.get("payload", {}).get("content", r.get("payload", {}).get("abstract", ""))) for r in results]
        scores = cross_encoder.predict(pairs)

        # Sort by cross-encoder score
        ranked = sorted(zip(results, scores), key=lambda x: x[1], reverse=True)
        return [r for r, _ in ranked[:top_k]]
    except Exception as e:
        logger.debug(f"Cross-encoder reranking failed (using original order): {e}")
        return results[:top_k]
