"""
Research System — Trial Matching Agent

Responsibilities:
  - ClinicalTrials.gov API integration (search by condition, eligibility)
  - Patient-to-trial matching algorithm (age, conditions, medications, history)
  - Rank trials by eligibility probability
  - Generate patient-friendly trial summary
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

from base.tools import search_clinical_trials

logger = logging.getLogger("inhealth.research.trial_matching")


class TrialMatchingAgent:
    """Clinical trial matching agent using ClinicalTrials.gov."""

    def __init__(self, langfuse_handler: Optional[LangfuseCallbackHandler] = None):
        self.langfuse_handler = langfuse_handler

    async def find_trials(
        self,
        condition: str,
        patient_id: Optional[str] = None,
        patient_criteria: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find and rank clinical trials for a patient.
        Returns list of matched trials with eligibility probability.
        """
        if patient_criteria is None:
            patient_criteria = {}

        # Search ClinicalTrials.gov
        try:
            raw_trials = search_clinical_trials.invoke({
                "condition": condition,
                "patient_criteria": patient_criteria,
            })
        except Exception as exc:
            logger.warning("Clinical trials search failed: %s", exc)
            raw_trials = []

        if not raw_trials:
            return []

        # Score and rank trials by eligibility
        scored_trials = self._score_eligibility(raw_trials, patient_criteria)

        # Generate patient-friendly summaries
        patient_summaries = await self._generate_patient_summaries(scored_trials[:5])

        return patient_summaries

    def _score_eligibility(
        self,
        trials: List[Dict[str, Any]],
        patient: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Score each trial by estimated eligibility probability."""
        patient_age = int(patient.get("age", 50))
        patient_sex = patient.get("sex", "all").lower()
        patient_conditions = [c.lower() for c in patient.get("conditions", [])]
        patient_medications = [m.lower() for m in patient.get("medications", [])]

        scored = []
        for trial in trials:
            score = 0.5  # Base score
            issues = []

            # Age eligibility
            min_age_str = trial.get("minimum_age", "0 Years")
            max_age_str = trial.get("maximum_age", "999 Years")
            try:
                min_age = int(min_age_str.split()[0])
                max_age = int(max_age_str.split()[0])
                if min_age <= patient_age <= max_age:
                    score += 0.2
                else:
                    score -= 0.3
                    issues.append(f"Age {patient_age} outside trial range {min_age}-{max_age}")
            except (ValueError, IndexError):
                pass

            # Sex eligibility
            trial_sex = trial.get("sex", "ALL").upper()
            if trial_sex != "ALL":
                if trial_sex.lower() in patient_sex:
                    score += 0.1
                else:
                    score -= 0.4
                    issues.append(f"Sex mismatch: trial requires {trial_sex}")

            # Check exclusion criteria for known patient medications/conditions
            criteria = trial.get("eligibility_criteria", "").lower()
            for med in patient_medications[:5]:
                if med in criteria and "exclude" in criteria:
                    score -= 0.15
                    issues.append(f"Potential exclusion: medication {med}")

            score = max(0.0, min(1.0, score))
            trial["eligibility_score"] = round(score, 2)
            trial["eligibility_issues"] = issues
            trial["eligibility_level"] = (
                "HIGH" if score >= 0.7
                else "MEDIUM" if score >= 0.4
                else "LOW"
            )
            scored.append(trial)

        # Sort by eligibility score
        scored.sort(key=lambda x: x.get("eligibility_score", 0), reverse=True)
        return scored

    async def _generate_patient_summaries(
        self, trials: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate patient-friendly trial descriptions."""
        try:
            from langchain_community.chat_models import ChatOllama

            llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
            )
        except Exception:
            llm = None

        result = []
        for trial in trials:
            patient_summary = ""
            if llm:
                try:
                    prompt = (
                        f"Explain this clinical trial in simple terms (grade 8 reading level):\n\n"
                        f"Title: {trial.get('title', '')}\n"
                        f"Condition: {trial.get('condition', '')}\n"
                        f"Status: {trial.get('status', '')}\n"
                        f"Brief summary: {trial.get('brief_summary', '')[:300]}\n"
                        f"Eligibility level: {trial.get('eligibility_level', '')}\n\n"
                        f"In 3-4 sentences, explain: What is this study about? What will participants do? What are the potential benefits? "
                        f"Is this a good match for this patient?"
                    )
                    response = llm.invoke(prompt)
                    patient_summary = response.content if hasattr(response, "content") else str(response)
                except Exception as exc:
                    logger.debug("Trial summary LLM failed: %s", exc)
                    patient_summary = trial.get("brief_summary", "")[:200]
            else:
                patient_summary = trial.get("brief_summary", "")[:200]

            trial["patient_summary"] = patient_summary
            result.append(trial)

        return result
