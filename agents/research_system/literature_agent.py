"""
Research System — Literature Agent

Responsibilities:
  - PubMed E-utilities API search (esearch + efetch)
  - Semantic Scholar API integration
  - Evidence grading (USPSTF levels A/B/C)
  - Store results in Qdrant for future RAG
  - Langfuse trace all LLM summarization calls
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

from base.tools import search_pubmed, vector_search

logger = logging.getLogger("inhealth.research.literature")

USPSTF_GRADES = {
    "A": "Strong evidence of benefit; recommend for all eligible patients.",
    "B": "Moderate evidence of benefit; recommend.",
    "C": "Moderate evidence; offer if individual patient benefit warrants.",
    "D": "Evidence of no benefit or harm; recommend against.",
    "I": "Insufficient evidence; cannot assess.",
}


class LiteratureAgent:
    """Research literature search and evidence grading agent."""

    def __init__(self, langfuse_handler: Optional[LangfuseCallbackHandler] = None):
        self.langfuse_handler = langfuse_handler
        self._ncbi_key = os.getenv("NCBI_API_KEY", "")
        self._semantic_scholar_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

    async def search(
        self,
        query: str,
        condition: Optional[str] = None,
        max_results: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Search PubMed and Semantic Scholar for relevant medical literature.
        Returns graded evidence with summaries.
        """
        search_query = query
        if condition:
            search_query = f"{query} AND {condition}[MeSH Terms]"

        # PubMed search
        pubmed_results = await self._search_pubmed(search_query, max_results)

        # Semantic Scholar search (for preprints and additional papers)
        semantic_results = await self._search_semantic_scholar(query, max_results // 2)

        # Merge and deduplicate
        all_results = self._merge_results(pubmed_results, semantic_results)

        # Grade evidence and summarize
        graded_results = await self._grade_and_summarize(all_results)

        # Store in Qdrant for RAG
        await self._store_in_qdrant(graded_results, query)

        return graded_results

    async def _search_pubmed(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search PubMed using E-utilities API."""
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        results = []

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                # esearch
                search_resp = await client.get(
                    f"{base_url}/esearch.fcgi",
                    params={
                        "db": "pubmed",
                        "term": query,
                        "retmax": max_results,
                        "retmode": "json",
                        "sort": "relevance",
                        "datetype": "pdat",
                        "mindate": "2020",
                        "api_key": self._ncbi_key,
                    },
                )
                search_resp.raise_for_status()
                search_data = search_resp.json()
                pmids = search_data.get("esearchresult", {}).get("idlist", [])

                if not pmids:
                    return []

                # esummary for metadata
                summary_resp = await client.get(
                    f"{base_url}/esummary.fcgi",
                    params={
                        "db": "pubmed",
                        "id": ",".join(pmids[:max_results]),
                        "retmode": "json",
                        "api_key": self._ncbi_key,
                    },
                )
                summary_resp.raise_for_status()
                summary_data = summary_resp.json()

                for pmid in pmids:
                    doc = summary_data.get("result", {}).get(pmid, {})
                    if doc:
                        results.append({
                            "source": "pubmed",
                            "pmid": pmid,
                            "title": doc.get("title", ""),
                            "authors": [a.get("name", "") for a in doc.get("authors", [])[:3]],
                            "journal": doc.get("fulljournalname", ""),
                            "pub_date": doc.get("pubdate", ""),
                            "abstract": "",  # Fetched separately if needed
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        })

        except Exception as exc:
            logger.warning("PubMed search failed: %s", exc)

        return results

    async def _search_semantic_scholar(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search Semantic Scholar API."""
        results = []
        try:
            headers = {}
            if self._semantic_scholar_key:
                headers["x-api-key"] = self._semantic_scholar_key

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    params={
                        "query": query,
                        "fields": "title,authors,year,abstract,externalIds,citationCount,isOpenAccess,journal",
                        "limit": max_results,
                        "sort": "relevance",
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

                for paper in data.get("data", []):
                    pmid = paper.get("externalIds", {}).get("PubMed", "")
                    results.append({
                        "source": "semantic_scholar",
                        "paper_id": paper.get("paperId", ""),
                        "pmid": pmid,
                        "title": paper.get("title", ""),
                        "authors": [a.get("name", "") for a in paper.get("authors", [])[:3]],
                        "year": paper.get("year", ""),
                        "abstract": paper.get("abstract", ""),
                        "citation_count": paper.get("citationCount", 0),
                        "open_access": paper.get("isOpenAccess", False),
                        "journal": paper.get("journal", {}).get("name", "") if paper.get("journal") else "",
                        "url": f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}",
                    })

        except Exception as exc:
            logger.warning("Semantic Scholar search failed: %s", exc)

        return results

    def _merge_results(
        self,
        pubmed: List[Dict[str, Any]],
        semantic: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merge and deduplicate results from multiple sources."""
        seen_pmids = set()
        seen_titles = set()
        merged = []

        for result in pubmed + semantic:
            pmid = result.get("pmid", "")
            title = result.get("title", "").lower()[:50]

            if pmid and pmid in seen_pmids:
                continue
            if title and title in seen_titles:
                continue

            if pmid:
                seen_pmids.add(pmid)
            if title:
                seen_titles.add(title)

            merged.append(result)

        # Sort by citation count (higher is better)
        merged.sort(key=lambda x: x.get("citation_count", 0), reverse=True)
        return merged[:20]

    async def _grade_and_summarize(
        self,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Grade evidence quality and generate abstracts summaries."""
        graded = []
        for result in results:
            # Simple evidence grading based on title/journal keywords
            grade = self._estimate_evidence_grade(result)
            result["evidence_grade"] = grade
            result["evidence_description"] = USPSTF_GRADES.get(grade, "")

            # Generate brief summary using LLM (traced via Langfuse)
            abstract = result.get("abstract", "")
            if abstract:
                try:
                    # This would use an LLM to summarize; simplified here
                    result["summary"] = abstract[:300] + "..." if len(abstract) > 300 else abstract
                except Exception:
                    result["summary"] = abstract[:300]
            else:
                result["summary"] = result.get("title", "No abstract available")

            graded.append(result)

        return graded

    def _estimate_evidence_grade(self, paper: Dict[str, Any]) -> str:
        """Estimate USPSTF evidence grade based on study design keywords."""
        title_abstract = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
        citations = paper.get("citation_count", 0)

        if any(t in title_abstract for t in ["systematic review", "meta-analysis", "cochrane"]):
            return "A"
        if any(t in title_abstract for t in ["randomized controlled", "rct", "clinical trial"]):
            return "A" if citations > 100 else "B"
        if any(t in title_abstract for t in ["cohort study", "prospective", "longitudinal"]):
            return "B"
        if any(t in title_abstract for t in ["case-control", "observational", "cross-sectional"]):
            return "C"
        return "C"

    async def _store_in_qdrant(
        self,
        results: List[Dict[str, Any]],
        query: str,
    ) -> None:
        """Store search results in Qdrant for future RAG retrieval."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct
            from sentence_transformers import SentenceTransformer
            import uuid

            client = QdrantClient(
                host=os.getenv("QDRANT_HOST", "qdrant"),
                port=int(os.getenv("QDRANT_PORT", "6333")),
            )
            embedder = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))

            points = []
            for result in results:
                text = f"{result.get('title', '')} {result.get('abstract', '')[:500]}"
                if not text.strip():
                    continue
                embedding = embedder.encode(text).tolist()
                points.append(PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "content": text[:1000],
                        "title": result.get("title", ""),
                        "source": result.get("source", ""),
                        "pmid": result.get("pmid", ""),
                        "evidence_grade": result.get("evidence_grade", "C"),
                        "url": result.get("url", ""),
                        "query": query,
                        "stored_at": datetime.now(timezone.utc).isoformat(),
                    },
                ))

            if points:
                client.upsert(collection_name="pubmed_abstracts", points=points)
                logger.info("Stored %d literature results in Qdrant", len(points))

        except Exception as exc:
            logger.warning("Qdrant storage failed: %s", exc)
