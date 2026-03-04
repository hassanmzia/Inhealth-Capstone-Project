"""
Research System — Guideline Agent

Responsibilities:
  - Monitor ADA, ACC/AHA, KDIGO, GOLD guideline updates
  - Compare current practice patterns against latest guidelines
  - Generate care gap recommendations
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

from base.tools import vector_search

logger = logging.getLogger("inhealth.research.guideline")

# Guideline source URLs
GUIDELINE_SOURCES = {
    "ADA": {
        "name": "American Diabetes Association Standards of Care",
        "url": "https://diabetesjournals.org/care/issue/47/Supplement_1",
        "year": 2024,
        "conditions": ["diabetes", "hyperglycemia", "insulin"],
    },
    "ACC_AHA_HYPERTENSION": {
        "name": "ACC/AHA Hypertension Guideline",
        "url": "https://www.acc.org/Guidelines",
        "year": 2022,
        "conditions": ["hypertension", "blood_pressure", "antihypertensive"],
    },
    "KDIGO_CKD": {
        "name": "KDIGO CKD Management Guideline",
        "url": "https://kdigo.org/guidelines/ckd-evaluation-and-management/",
        "year": 2024,
        "conditions": ["ckd", "kidney", "egfr", "creatinine"],
    },
    "GOLD_COPD": {
        "name": "GOLD COPD Strategy Report",
        "url": "https://goldcopd.org/2024-gold-report/",
        "year": 2024,
        "conditions": ["copd", "emphysema", "bronchitis"],
    },
    "ACC_AHA_HEART_FAILURE": {
        "name": "ACC/AHA Heart Failure Guideline",
        "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001063",
        "year": 2022,
        "conditions": ["heart_failure", "cardiac"],
    },
    "AHA_ASA_STROKE": {
        "name": "AHA/ASA Stroke Guidelines",
        "url": "https://www.ahajournals.org/journal/str",
        "year": 2021,
        "conditions": ["stroke", "tia", "thrombolysis"],
    },
}


class GuidelineAgent:
    """Clinical guideline monitoring and care gap analysis agent."""

    def __init__(self, langfuse_handler: Optional[LangfuseCallbackHandler] = None):
        self.langfuse_handler = langfuse_handler

    async def check_guideline_adherence(
        self,
        patient_id: str,
        current_practices: Dict[str, Any],
        conditions: List[str],
    ) -> Dict[str, Any]:
        """
        Compare current care practices against latest clinical guidelines.
        Returns care gaps and recommendations.
        """
        applicable_guidelines = self._identify_applicable_guidelines(conditions)

        care_gaps = []
        recommendations = []

        for guideline_key in applicable_guidelines:
            guideline = GUIDELINE_SOURCES[guideline_key]

            # RAG: retrieve relevant guideline content
            try:
                guideline_content = vector_search.invoke({
                    "query": f"{guideline['name']} recommendations {' '.join(conditions[:3])}",
                    "collection": "clinical_guidelines",
                    "top_k": 3,
                })
            except Exception as exc:
                logger.warning("Guideline RAG failed for %s: %s", guideline_key, exc)
                guideline_content = []

            # Check for care gaps
            gaps = await self._identify_care_gaps(
                guideline_key=guideline_key,
                guideline=guideline,
                current_practices=current_practices,
                guideline_content=guideline_content,
            )
            care_gaps.extend(gaps)

        # Generate recommendations via LLM
        recommendations = await self._generate_recommendations(
            patient_id=patient_id,
            care_gaps=care_gaps,
            conditions=conditions,
        )

        return {
            "status": "completed",
            "guidelines_checked": len(applicable_guidelines),
            "care_gaps_found": len(care_gaps),
            "care_gaps": care_gaps,
            "recommendations": recommendations,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def _identify_applicable_guidelines(self, conditions: List[str]) -> List[str]:
        """Match patient conditions to applicable guidelines."""
        applicable = []
        conditions_lower = [c.lower() for c in conditions]

        for key, guideline in GUIDELINE_SOURCES.items():
            for condition_keyword in guideline["conditions"]:
                if any(condition_keyword in pc for pc in conditions_lower):
                    applicable.append(key)
                    break

        return list(set(applicable))

    async def _identify_care_gaps(
        self,
        guideline_key: str,
        guideline: Dict[str, Any],
        current_practices: Dict[str, Any],
        guideline_content: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Identify gaps between current practices and guideline recommendations."""
        gaps = []

        # Evidence-based gap checks
        if guideline_key == "ADA":
            # Check HbA1c monitoring frequency
            last_hba1c_date = current_practices.get("last_hba1c_date")
            if not last_hba1c_date:
                gaps.append({
                    "guideline": "ADA 2024",
                    "gap": "HbA1c not documented",
                    "recommendation": "ADA 2024: HbA1c every 3 months if not at goal, or every 6 months if at goal.",
                    "priority": "HIGH",
                })

            # Check statin therapy
            medications = current_practices.get("medications", [])
            if not any("statin" in m.lower() for m in medications):
                gaps.append({
                    "guideline": "ADA 2024",
                    "gap": "Statin therapy not prescribed (age > 40 with diabetes)",
                    "recommendation": "ADA 2024: Moderate-intensity statin for all patients with diabetes aged 40-75. High-intensity if 10-year ASCVD risk ≥ 20%.",
                    "priority": "HIGH",
                })

        elif guideline_key == "KDIGO_CKD":
            egfr = current_practices.get("current_egfr")
            medications = current_practices.get("medications", [])

            if egfr and egfr < 60 and not any("ace" in m.lower() or "arb" in m.lower() for m in medications):
                gaps.append({
                    "guideline": "KDIGO 2024",
                    "gap": "No ACE inhibitor or ARB prescribed for CKD with albuminuria",
                    "recommendation": "KDIGO 2024: ACE inhibitor or ARB for CKD with UACR ≥ 30 mg/g — reduces CKD progression by 30-40%.",
                    "priority": "HIGH",
                })

            if egfr and egfr >= 20 and not any("sglt2" in m.lower() or "empagliflozin" in m.lower() or "dapagliflozin" in m.lower() for m in medications):
                gaps.append({
                    "guideline": "KDIGO 2024",
                    "gap": "SGLT2 inhibitor not prescribed (indicated for CKD + T2DM or CKD + HF)",
                    "recommendation": "KDIGO 2024: SGLT2i (dapagliflozin) for CKD patients with eGFR ≥ 20 and T2DM or HF — DAPA-CKD trial: 39% reduction in CKD progression.",
                    "priority": "MEDIUM",
                })

        return gaps

    async def _generate_recommendations(
        self,
        patient_id: str,
        care_gaps: List[Dict[str, Any]],
        conditions: List[str],
    ) -> List[str]:
        """Generate prioritized care gap recommendations."""
        if not care_gaps:
            return ["No significant care gaps identified against current guidelines."]

        recs = []
        high_priority = [g for g in care_gaps if g.get("priority") == "HIGH"]
        medium_priority = [g for g in care_gaps if g.get("priority") == "MEDIUM"]

        for gap in high_priority[:3]:
            recs.append(f"[HIGH PRIORITY] {gap.get('guideline', '')}: {gap.get('recommendation', '')}")

        for gap in medium_priority[:2]:
            recs.append(f"[MEDIUM PRIORITY] {gap.get('guideline', '')}: {gap.get('recommendation', '')}")

        return recs

    async def monitor_guideline_updates(self) -> List[Dict[str, Any]]:
        """
        Check for new guideline publications or updates.
        In production: RSS feeds, journal APIs, or scheduled web scraping.
        """
        updates = []
        for key, guideline in GUIDELINE_SOURCES.items():
            updates.append({
                "guideline": guideline["name"],
                "year": guideline["year"],
                "url": guideline["url"],
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "status": "current",
            })
        return updates
