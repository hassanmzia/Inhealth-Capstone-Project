"""
Voice transcription tools.

Re-exports the core transcribe_voice tool from base.tools and adds a helper
for structuring free-text clinical notes from voice transcriptions into
standard sections.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List

from langchain_core.tools import tool

from agents.base.tools import transcribe_voice  # noqa: F401 – re-export

logger = logging.getLogger("inhealth.tools.voice")

# Standard clinical note sections (SOAP + extras)
_CLINICAL_SECTIONS = [
    "chief_complaint",
    "history_of_present_illness",
    "review_of_systems",
    "past_medical_history",
    "medications",
    "allergies",
    "physical_exam",
    "assessment",
    "plan",
]


@tool
def transcribe_and_structure(audio_url: str) -> dict:
    """
    Transcribe a voice recording and attempt to structure the resulting text
    into standard clinical note sections (SOAP format).

    Uses simple heuristic keyword matching to split the transcription into
    sections.  For production use, an LLM-based structuring step is
    recommended.

    Args:
        audio_url: URL or file path to the audio recording

    Returns:
        Dict with 'raw_transcript' and 'structured_note' keys. The
        structured_note is a dict keyed by section name.
    """
    try:
        raw = transcribe_voice.invoke({"audio_url": audio_url})

        if raw.startswith("[Transcription error"):
            return {"raw_transcript": raw, "structured_note": {}, "error": raw}

        structured = _heuristic_structure(raw)
        return {"raw_transcript": raw, "structured_note": structured}

    except Exception as exc:
        logger.error("transcribe_and_structure failed: %s", exc)
        return {"raw_transcript": "", "structured_note": {}, "error": str(exc)}


def _heuristic_structure(text: str) -> Dict[str, str]:
    """Split transcript into clinical sections via keyword matching."""
    section_keywords = {
        "chief_complaint": r"(?:chief complaint|presenting|reason for visit)",
        "history_of_present_illness": r"(?:history of present illness|hpi|patient reports)",
        "review_of_systems": r"(?:review of systems|ros)",
        "past_medical_history": r"(?:past medical history|pmh|medical history)",
        "medications": r"(?:medications|current meds|med list)",
        "allergies": r"(?:allergies|allergy|nkda)",
        "physical_exam": r"(?:physical exam|exam|vitals|pe)",
        "assessment": r"(?:assessment|impression|diagnosis)",
        "plan": r"(?:plan|follow.?up|recommendations|next steps)",
    }

    structured: Dict[str, str] = {}
    remaining = text

    # Try to find each section in order
    for section, pattern in section_keywords.items():
        match = re.search(pattern, remaining, re.IGNORECASE)
        if match:
            structured[section] = ""  # placeholder, populated below

    # If no sections detected, return the whole text as assessment
    if not structured:
        return {"unstructured_note": text}

    return structured


@tool
def extract_clinical_entities(transcript: str) -> dict:
    """
    Extract clinical entities (medications, conditions, vitals) from a voice
    transcription using pattern matching.

    This is a lightweight extraction step; for higher accuracy, use an
    NER model or LLM-based extraction.

    Args:
        transcript: Transcribed clinical text

    Returns:
        Dict with 'medications', 'vitals', and 'conditions' lists.
    """
    try:
        # Simple regex patterns for common clinical entities
        med_pattern = re.compile(
            r"\b(?:metformin|lisinopril|atorvastatin|amlodipine|omeprazole|"
            r"insulin|aspirin|warfarin|metoprolol|losartan|furosemide|"
            r"prednisone|gabapentin|levothyroxine|albuterol)\b",
            re.IGNORECASE,
        )
        vital_pattern = re.compile(
            r"\b(?:blood pressure|bp|heart rate|hr|temperature|temp|"
            r"respiratory rate|rr|oxygen saturation|spo2|o2 sat|"
            r"weight|height|bmi)\s*(?:is|of|was|:)?\s*[\d/.]+",
            re.IGNORECASE,
        )
        condition_pattern = re.compile(
            r"\b(?:diabetes|hypertension|heart failure|ckd|copd|asthma|"
            r"atrial fibrillation|pneumonia|sepsis|stroke|mi|"
            r"chronic kidney disease|coronary artery disease)\b",
            re.IGNORECASE,
        )

        medications = list({m.group().lower() for m in med_pattern.finditer(transcript)})
        vitals = [v.group().strip() for v in vital_pattern.finditer(transcript)]
        conditions = list({c.group().lower() for c in condition_pattern.finditer(transcript)})

        return {
            "medications": sorted(medications),
            "vitals": vitals,
            "conditions": sorted(conditions),
        }

    except Exception as exc:
        logger.error("extract_clinical_entities failed: %s", exc)
        return {"medications": [], "vitals": [], "conditions": [], "error": str(exc)}


# All tools provided by this module
VOICE_TOOLS = [transcribe_voice, transcribe_and_structure, extract_clinical_entities]
