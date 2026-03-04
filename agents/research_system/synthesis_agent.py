"""
Research System — Synthesis Agent

Responsibilities:
  - Aggregate evidence from multiple literature sources
  - Generate systematic review-style summary
  - Identify research gaps
  - Grade overall evidence quality
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

logger = logging.getLogger("inhealth.research.synthesis")


class SynthesisAgent:
    """Research evidence synthesis and systematic review generation."""

    def __init__(self, langfuse_handler: Optional[LangfuseCallbackHandler] = None):
        self.langfuse_handler = langfuse_handler

    async def synthesize(
        self,
        literature_results: List[Dict[str, Any]],
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize evidence from multiple literature sources into a structured review.
        """
        if not literature_results:
            return {
                "status": "no_data",
                "message": "No literature results to synthesize",
                "synthesis": None,
            }

        # Grade distribution
        grade_distribution = self._calculate_grade_distribution(literature_results)
        overall_grade = self._determine_overall_grade(grade_distribution)

        # Cluster by topic
        topic_clusters = self._cluster_by_topic(literature_results)

        # Generate synthesis via LLM
        titles_and_abstracts = "\n\n".join([
            f"[{r.get('evidence_grade', '?')}] {r.get('title', '')}\n{r.get('summary', '')[:200]}"
            for r in literature_results[:10]
        ])

        synthesis_text = await self._generate_synthesis_narrative(
            titles_and_abstracts=titles_and_abstracts,
            grade_distribution=grade_distribution,
            overall_grade=overall_grade,
            query=query,
        )

        # Identify research gaps
        research_gaps = self._identify_research_gaps(literature_results)

        # Key findings extraction
        key_findings = self._extract_key_findings(literature_results)

        return {
            "status": "completed",
            "total_papers": len(literature_results),
            "overall_evidence_grade": overall_grade,
            "grade_distribution": grade_distribution,
            "topic_clusters": topic_clusters,
            "key_findings": key_findings,
            "research_gaps": research_gaps,
            "synthesis_narrative": synthesis_text,
            "citations": [
                f"{r.get('title', '')} ({r.get('journal', '')} {r.get('year', r.get('pub_date', '')[:4])})"
                for r in literature_results[:5]
            ],
        }

    def _calculate_grade_distribution(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        distribution: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "I": 0}
        for r in results:
            grade = r.get("evidence_grade", "C")
            distribution[grade] = distribution.get(grade, 0) + 1
        return distribution

    def _determine_overall_grade(self, distribution: Dict[str, int]) -> str:
        if distribution.get("A", 0) >= 2:
            return "A"
        if distribution.get("A", 0) >= 1 or distribution.get("B", 0) >= 2:
            return "B"
        if distribution.get("B", 0) >= 1:
            return "B-C"
        return "C"

    def _cluster_by_topic(
        self, results: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Simple keyword-based topic clustering."""
        clusters: Dict[str, List[str]] = {
            "treatment": [],
            "prevention": [],
            "diagnosis": [],
            "prognosis": [],
            "mechanism": [],
            "other": [],
        }
        keywords = {
            "treatment": ["treatment", "therapy", "intervention", "medication", "drug"],
            "prevention": ["prevention", "screening", "risk reduction", "prophylaxis"],
            "diagnosis": ["diagnosis", "diagnostic", "biomarker", "sensitivity", "specificity"],
            "prognosis": ["prognosis", "outcome", "survival", "mortality", "risk factor"],
            "mechanism": ["mechanism", "pathophysiology", "molecular", "pathway"],
        }
        for r in results:
            title_lower = r.get("title", "").lower()
            assigned = False
            for cluster, kws in keywords.items():
                if any(kw in title_lower for kw in kws):
                    clusters[cluster].append(r.get("title", "")[:80])
                    assigned = True
                    break
            if not assigned:
                clusters["other"].append(r.get("title", "")[:80])

        return {k: v for k, v in clusters.items() if v}

    def _identify_research_gaps(self, results: List[Dict[str, Any]]) -> List[str]:
        """Identify research gaps based on available evidence."""
        gaps = []
        titles = " ".join([r.get("title", "") for r in results]).lower()

        if "pediatric" not in titles and "children" not in titles:
            gaps.append("Limited evidence in pediatric populations")
        if "elderly" not in titles and "older adults" not in titles:
            gaps.append("Insufficient data in geriatric populations (>75 years)")
        if "real-world" not in titles and "real world" not in titles:
            gaps.append("Need for real-world effectiveness studies beyond controlled trials")
        if "long-term" not in titles and "longitudinal" not in titles:
            gaps.append("Lack of long-term follow-up data beyond 2 years")
        if "cost" not in titles and "economic" not in titles:
            gaps.append("Cost-effectiveness data needed for healthcare systems")

        return gaps[:4]

    def _extract_key_findings(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract top key findings from high-quality papers."""
        findings = []
        high_quality = [r for r in results if r.get("evidence_grade") in ("A", "B")]
        for paper in high_quality[:5]:
            summary = paper.get("summary", "")
            if summary:
                findings.append(f"[{paper.get('evidence_grade', '?')}] {summary[:150]}")
        return findings

    async def _generate_synthesis_narrative(
        self,
        titles_and_abstracts: str,
        grade_distribution: Dict[str, int],
        overall_grade: str,
        query: Optional[str],
    ) -> str:
        """Generate a systematic review-style narrative using LLM."""
        try:
            from langchain_community.chat_models import ChatOllama

            llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            )
            import os

            prompt = (
                f"Synthesize the following medical literature into a structured evidence summary:\n\n"
                f"Query: {query or 'General clinical evidence'}\n"
                f"Evidence grade distribution: {grade_distribution}\n"
                f"Overall evidence level: {overall_grade} (USPSTF scale)\n\n"
                f"Papers:\n{titles_and_abstracts}\n\n"
                f"Generate a structured synthesis with:\n"
                f"1. Summary of current evidence (2-3 paragraphs)\n"
                f"2. Areas of consensus\n"
                f"3. Areas of controversy\n"
                f"4. Clinical implications for practice\n"
                f"5. Recommended further research\n\n"
                f"Use systematic review writing style. Cite evidence grades."
            )
            response = llm.invoke(prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.warning("Synthesis LLM failed: %s", exc)
            return (
                f"Evidence synthesis based on {sum(grade_distribution.values())} papers. "
                f"Overall evidence grade: {overall_grade}. "
                f"Grade A studies: {grade_distribution.get('A', 0)}, "
                f"Grade B: {grade_distribution.get('B', 0)}, "
                f"Grade C: {grade_distribution.get('C', 0)}."
            )
