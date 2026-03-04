"""
RAG (Retrieval-Augmented Generation) pipeline for InHealth.
Retrieve → Rank → Augment with clinical context.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("vector.rag")


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.
    Implements: Query → Embed → Retrieve → Rerank → Augment with LLM.
    """

    def __init__(self, llm_provider: str = None):
        self.llm_provider = llm_provider or self._get_default_provider()

    def _get_default_provider(self) -> str:
        try:
            from django.conf import settings
            return getattr(settings, "OPENAI_API_KEY", None) and "openai" or "anthropic"
        except Exception:
            return "openai"

    def retrieve(
        self,
        query: str,
        collection: str,
        top_k: int = 10,
        score_threshold: float = 0.65,
        filters: Dict = None,
    ) -> List[Dict]:
        """
        Retrieve semantically similar documents from Qdrant.
        Returns list of {id, score, payload} dicts.
        """
        from vector.embeddings import generate_embedding
        from vector.client import search_vectors

        query_embedding = generate_embedding(query)
        if query_embedding is None:
            logger.warning(f"Could not generate embedding for query: {query[:100]}")
            return []

        results = search_vectors(
            collection_name=collection,
            query_vector=query_embedding,
            top_k=top_k,
            score_threshold=score_threshold,
            filter_payload=filters,
        )

        logger.debug(f"RAG retrieved {len(results)} results from {collection}")
        return results

    def retrieve_and_augment(
        self,
        query: str,
        collection: str,
        top_k: int = 5,
        system_context: str = "",
        patient_context: Dict = None,
    ) -> Dict:
        """
        Full RAG pipeline:
        1. Retrieve relevant documents
        2. Rerank for quality
        3. Augment query with LLM

        Returns {answer, sources, confidence, evidence_level}
        """
        # Step 1: Retrieve
        results = self.retrieve(query, collection, top_k=top_k * 2)

        if not results:
            return {
                "answer": "No relevant information found in the knowledge base.",
                "sources": [],
                "confidence": 0.0,
                "evidence_level": "C",
            }

        # Step 2: Rerank
        from vector.embeddings import rerank_results
        reranked = rerank_results(query, results, top_k=top_k)

        # Step 3: Build context
        context_text = self._build_context(reranked)
        sources = self._extract_sources(reranked)

        # Step 4: LLM augmentation
        answer = self._call_llm(
            query=query,
            context=context_text,
            system_context=system_context,
            patient_context=patient_context,
        )

        # Determine evidence level from sources
        evidence_levels = [
            r.get("payload", {}).get("evidence_level", "C")
            for r in reranked
            if r.get("payload", {}).get("evidence_level")
        ]
        best_evidence = min(evidence_levels, key=lambda x: {"A": 1, "B": 2, "C": 3}.get(x, 3)) if evidence_levels else "C"

        return {
            "answer": answer,
            "sources": sources,
            "confidence": reranked[0]["score"] if reranked else 0.0,
            "evidence_level": best_evidence,
            "retrieved_count": len(reranked),
        }

    def _build_context(self, results: List[Dict]) -> str:
        """Build a context string from retrieved results."""
        context_parts = []
        for i, result in enumerate(results, 1):
            payload = result.get("payload", {})
            title = payload.get("title", f"Document {i}")
            content = (
                payload.get("content")
                or payload.get("abstract")
                or payload.get("description")
                or payload.get("dosing")
                or ""
            )
            source = payload.get("source") or payload.get("journal") or ""
            year = payload.get("year", "")

            context_parts.append(
                f"[{i}] {title} ({source}{', ' + str(year) if year else ''})\n{content[:500]}"
            )

        return "\n\n---\n\n".join(context_parts)

    def _extract_sources(self, results: List[Dict]) -> List[Dict]:
        """Extract source metadata from results."""
        sources = []
        for result in results:
            payload = result.get("payload", {})
            source = {
                "title": payload.get("title", ""),
                "score": result.get("score", 0),
            }
            # Add type-specific fields
            if "pubmed_id" in payload:
                source["pubmed_id"] = payload["pubmed_id"]
                source["doi"] = payload.get("doi", "")
                source["url"] = f"https://pubmed.ncbi.nlm.nih.gov/{payload['pubmed_id']}/"
            if "url" in payload:
                source["url"] = payload["url"]
            if "source" in payload:
                source["source_name"] = payload["source"]
            if "year" in payload:
                source["year"] = payload["year"]
            sources.append(source)
        return sources

    def _call_llm(
        self,
        query: str,
        context: str,
        system_context: str = "",
        patient_context: Dict = None,
    ) -> str:
        """Call LLM with retrieved context for answer generation."""
        system_prompt = """You are a clinical decision support AI for InHealth Chronic Care.
Answer clinical questions based on the provided evidence context.
Always cite specific evidence. Be concise and clinically accurate.
If the evidence is insufficient, explicitly state the limitations.
Never provide specific medical advice without appropriate clinical supervision."""

        if system_context:
            system_prompt += f"\n\nAdditional context: {system_context}"

        user_message = f"""Clinical question: {query}

Evidence context:
{context}

"""
        if patient_context:
            user_message += f"""
Patient context:
- Age: {patient_context.get('patient', {}).get('age', 'unknown')}
- Active conditions: {', '.join(c.get('display', '') for c in patient_context.get('clinical_summary', {}).get('active_conditions', [])[:5])}
- Current medications: {', '.join(m.get('medication_display', '') for m in patient_context.get('clinical_summary', {}).get('active_medications', [])[:5])}
"""
        user_message += "\nBased on the evidence above, provide a concise clinical answer:"

        try:
            return self._call_openai(system_prompt, user_message)
        except Exception:
            try:
                return self._call_anthropic(system_prompt, user_message)
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return f"Evidence retrieved but LLM unavailable. Key finding: {context[:300]}..."

    def _call_openai(self, system_prompt: str, user_message: str) -> str:
        from django.conf import settings
        import openai

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=800,
            temperature=0.1,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, system_prompt: str, user_message: str) -> str:
        from django.conf import settings
        import anthropic

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
