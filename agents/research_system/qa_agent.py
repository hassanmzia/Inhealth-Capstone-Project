"""
Research System — Clinical Q&A Agent

Responsibilities:
  - Clinical Q&A with RAG retrieval from Qdrant
  - Answer questions with citations from medical literature
  - Hallucination check: verify answer against retrieved context
  - NL2SQL for database queries
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

from base.tools import nl2sql_query, vector_search

logger = logging.getLogger("inhealth.research.qa")


class QAAgent:
    """Clinical Q&A agent with RAG and hallucination checking."""

    def __init__(self, langfuse_handler: Optional[LangfuseCallbackHandler] = None):
        self.langfuse_handler = langfuse_handler

    async def answer(
        self,
        question: str,
        patient_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Answer a clinical question using RAG + LLM with hallucination verification.
        """
        # 1. Retrieve relevant context from Qdrant
        retrieved_context = await self._retrieve_context(question)

        # 2. Check if question requires database query
        db_result = None
        if patient_id and self._requires_database_query(question):
            db_result = await self._run_database_query(question, patient_id)

        # 3. Generate answer using LLM
        answer_text, citations = await self._generate_answer(
            question=question,
            retrieved_context=retrieved_context,
            db_result=db_result,
            context=context or {},
        )

        # 4. Hallucination check
        hallucination_score = await self._check_hallucination(
            answer=answer_text,
            context=retrieved_context,
        )

        # 5. Add confidence disclaimer if needed
        if hallucination_score > 0.3:
            answer_text += (
                "\n\n[CONFIDENCE NOTE: This answer may contain information not fully supported "
                "by retrieved clinical evidence. Please verify with primary sources or consult "
                "a clinical specialist.]"
            )

        return {
            "question": question,
            "answer": answer_text,
            "citations": citations,
            "retrieved_sources": len(retrieved_context),
            "hallucination_risk_score": round(hallucination_score, 3),
            "confidence": "HIGH" if hallucination_score < 0.15 else "MEDIUM" if hallucination_score < 0.30 else "LOW",
            "database_result": db_result,
            "disclaimer": "AI-generated clinical information. For clinical decisions, always consult appropriate medical literature and qualified healthcare professionals.",
        }

    async def _retrieve_context(self, question: str) -> List[Dict[str, Any]]:
        """Retrieve relevant context from Qdrant vector store."""
        results = []
        collections = ["clinical_guidelines", "pubmed_abstracts", "patient_cases"]

        for collection in collections:
            try:
                hits = vector_search.invoke({
                    "query": question,
                    "collection": collection,
                    "top_k": 3,
                })
                for hit in hits:
                    hit["collection"] = collection
                results.extend(hits)
            except Exception as exc:
                logger.debug("RAG retrieval from %s failed: %s", collection, exc)

        # Sort by relevance score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:8]

    def _requires_database_query(self, question: str) -> bool:
        """Determine if the question requires a database query."""
        db_keywords = [
            "last", "recent", "current", "today", "this week",
            "my", "patient", "value", "result", "reading",
            "hba1c", "glucose", "blood pressure", "creatinine",
        ]
        question_lower = question.lower()
        return any(kw in question_lower for kw in db_keywords)

    async def _run_database_query(
        self, question: str, patient_id: str
    ) -> Optional[Dict[str, Any]]:
        """Run NL2SQL query for patient-specific questions."""
        try:
            result = nl2sql_query.invoke({
                "natural_language_query": question,
                "patient_id": patient_id,
            })
            return result
        except Exception as exc:
            logger.warning("NL2SQL query failed: %s", exc)
            return None

    async def _generate_answer(
        self,
        question: str,
        retrieved_context: List[Dict[str, Any]],
        db_result: Optional[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> tuple[str, List[str]]:
        """Generate a grounded answer using LLM with retrieved context."""
        context_text = "\n\n".join([
            f"[Source {i+1}: {r.get('source', r.get('collection', 'unknown'))} | Relevance: {r.get('score', 0):.2f}]\n{r.get('content', '')[:400]}"
            for i, r in enumerate(retrieved_context[:5])
        ])

        db_text = ""
        if db_result and db_result.get("results"):
            db_text = f"\n\nPatient database results:\n{str(db_result.get('results', ''))[:300]}"

        synthesis_context = context.get("synthesis", {})
        synthesis_text = synthesis_context.get("synthesis_narrative", "") if synthesis_context else ""

        prompt = (
            f"You are a clinical AI assistant. Answer the following medical question "
            f"using ONLY the provided retrieved context. If the context doesn't support "
            f"the answer, say so explicitly. Always cite your sources.\n\n"
            f"Question: {question}\n\n"
            f"Retrieved clinical context:\n{context_text}\n{db_text}\n\n"
            + (f"Literature synthesis: {synthesis_text[:300]}\n\n" if synthesis_text else "")
            + f"Answer with citations (format: [Source N]):"
        )

        try:
            from langchain_community.chat_models import ChatOllama

            llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            )
            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.warning("QA LLM failed: %s", exc)
            if retrieved_context:
                answer = f"Based on retrieved clinical evidence: {retrieved_context[0].get('content', '')[:300]}"
            else:
                answer = "Insufficient clinical evidence retrieved to answer this question accurately."

        # Extract citations
        citations = [
            f"{r.get('source', r.get('collection', 'unknown'))}: {r.get('title', r.get('content', '')[:60])}"
            for r in retrieved_context[:5]
        ]

        return answer, citations

    async def _check_hallucination(
        self,
        answer: str,
        context: List[Dict[str, Any]],
    ) -> float:
        """
        Estimate hallucination risk by checking answer against retrieved context.
        Returns a score 0.0 (no hallucination risk) to 1.0 (high risk).
        """
        if not context:
            return 0.5  # No context = can't verify

        # Simple heuristic: check what fraction of answer sentences are grounded in context
        context_text = " ".join([r.get("content", "") for r in context]).lower()
        answer_sentences = [s.strip() for s in answer.split(".") if len(s.strip()) > 20]

        if not answer_sentences:
            return 0.0

        grounded_count = 0
        for sentence in answer_sentences:
            # Check if key words from sentence appear in context
            key_words = [w for w in sentence.lower().split() if len(w) > 4]
            if key_words:
                matches = sum(1 for w in key_words if w in context_text)
                if matches / len(key_words) >= 0.3:
                    grounded_count += 1

        grounded_ratio = grounded_count / len(answer_sentences)
        hallucination_risk = 1.0 - grounded_ratio

        return min(1.0, max(0.0, hallucination_risk))
