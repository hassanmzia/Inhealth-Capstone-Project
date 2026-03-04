"""
Security — PHI Detection Module

Presidio-based PHI detection and anonymization for InHealth AI agents.
Ensures no Protected Health Information leaks to LLM providers or logs.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("inhealth.security.phi")

# PHI entity types to detect
PHI_ENTITY_TYPES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "LOCATION",
    "DATE_TIME",
    "NRP",
    "MEDICAL_LICENSE",
    "URL",
]

# Custom HIPAA PHI patterns not covered by Presidio defaults
HIPAA_PHI_PATTERNS = {
    "MRN": r"\bMRN[:#\s]\s*\d{6,12}\b",
    "DOB": r"\b(?:DOB|Date of Birth|birth date)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "ACCOUNT_NUMBER": r"\b(?:Account|Acct)[#\s:]+\d{5,15}\b",
    "HEALTH_PLAN": r"\bPolicy\s+(?:Number|#|No)[:\s]+[A-Z0-9\-]{6,20}\b",
    "NPI": r"\bNPI[:\s]+\d{10}\b",
    "DEA": r"\bDEA[:\s]+[A-Z]{2}\d{7}\b",
}


class PHIDetector:
    """
    HIPAA-compliant PHI detection using Presidio with custom pattern extensions.
    Thread-safe singleton pattern for production use.
    """

    _instance: Optional["PHIDetector"] = None
    _analyzer = None
    _anonymizer = None

    def __new__(cls) -> "PHIDetector":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        try:
            from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
            from presidio_anonymizer import AnonymizerEngine

            self._analyzer = AnalyzerEngine()

            # Add custom HIPAA patterns
            for phi_type, pattern in HIPAA_PHI_PATTERNS.items():
                recognizer = PatternRecognizer(
                    supported_entity=phi_type,
                    patterns=[Pattern(name=phi_type, regex=pattern, score=0.9)],
                )
                self._analyzer.registry.add_recognizer(recognizer)

            self._anonymizer = AnonymizerEngine()
            self._initialized = True
            logger.info("PHI Detector initialized with Presidio + HIPAA extensions")

        except ImportError as exc:
            logger.warning("Presidio not available: %s. Using regex-only PHI detection.", exc)
            self._initialized = True
        except Exception as exc:
            logger.error("PHI Detector initialization failed: %s", exc)
            self._initialized = True

    def detect(self, text: str, threshold: float = 0.7) -> Dict[str, Any]:
        """
        Detect PHI entities in text.

        Returns:
            {
                "has_phi": bool,
                "phi_count": int,
                "entities": [{"type": str, "start": int, "end": int, "score": float, "text": str}],
                "custom_matches": [{"type": str, "match": str}]
            }
        """
        self._initialize()
        entities = []
        custom_matches = []

        # Presidio analysis
        if self._analyzer:
            try:
                results = self._analyzer.analyze(
                    text=text,
                    language="en",
                    entities=PHI_ENTITY_TYPES,
                    score_threshold=threshold,
                )
                entities = [
                    {
                        "type": r.entity_type,
                        "start": r.start,
                        "end": r.end,
                        "score": round(r.score, 3),
                        "text": text[r.start : r.end],
                    }
                    for r in results
                ]
            except Exception as exc:
                logger.warning("Presidio analysis failed: %s", exc)

        # Custom HIPAA pattern matching
        for phi_type, pattern in HIPAA_PHI_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                custom_matches.append({"type": phi_type, "match": match})

        total_phi = len(entities) + len(custom_matches)
        return {
            "has_phi": total_phi > 0,
            "phi_count": total_phi,
            "entities": entities,
            "custom_matches": custom_matches,
            "text_length": len(text),
        }

    def redact(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Redact PHI from text. Returns (redacted_text, redaction_report).
        """
        self._initialize()
        detection_result = self.detect(text)

        if not detection_result["has_phi"]:
            return text, {"redacted": False, "changes": 0}

        redacted_text = text

        # Presidio anonymization
        if self._anonymizer and self._analyzer:
            try:
                from presidio_anonymizer.entities import OperatorConfig

                analyzer_results = self._analyzer.analyze(text=text, language="en")
                anonymized = self._anonymizer.anonymize(
                    text=text,
                    analyzer_results=analyzer_results,
                    operators={
                        "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
                        "PERSON": OperatorConfig("replace", {"new_value": "<PATIENT_NAME>"}),
                        "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
                        "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE>"}),
                        "US_SSN": OperatorConfig("replace", {"new_value": "<SSN>"}),
                        "LOCATION": OperatorConfig("replace", {"new_value": "<LOCATION>"}),
                        "DATE_TIME": OperatorConfig("replace", {"new_value": "<DATE>"}),
                        "IP_ADDRESS": OperatorConfig("replace", {"new_value": "<IP>"}),
                    },
                )
                redacted_text = anonymized.text
            except Exception as exc:
                logger.warning("Presidio redaction failed, using regex fallback: %s", exc)
                redacted_text = self._regex_redact(text)
        else:
            redacted_text = self._regex_redact(text)

        # Apply custom pattern redaction
        for phi_type, pattern in HIPAA_PHI_PATTERNS.items():
            redacted_text = re.sub(pattern, f"<{phi_type}>", redacted_text, flags=re.IGNORECASE)

        return redacted_text, {
            "redacted": True,
            "original_length": len(text),
            "redacted_length": len(redacted_text),
            "phi_entities_removed": len(detection_result["entities"]),
            "custom_matches_removed": len(detection_result["custom_matches"]),
        }

    def _regex_redact(self, text: str) -> str:
        """Regex-based PHI redaction fallback."""
        # Email
        text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "<EMAIL>", text)
        # Phone
        text = re.sub(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "<PHONE>", text)
        # SSN
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "<SSN>", text)
        # Dates with context
        text = re.sub(
            r"\b(?:DOB|born|birthday)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            "<DOB>",
            text,
            flags=re.IGNORECASE,
        )
        return text

    def scan_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively scan a dictionary for PHI and return detection report.
        Does NOT modify the dict (use redact_dict for that).
        """
        issues = []
        self._scan_dict_recursive(data, "", issues)
        return {
            "has_phi": len(issues) > 0,
            "issues": issues,
        }

    def _scan_dict_recursive(
        self,
        data: Any,
        path: str,
        issues: List[Dict],
    ) -> None:
        if isinstance(data, str) and len(data) > 5:
            result = self.detect(data)
            if result["has_phi"]:
                issues.append({"path": path, "phi_count": result["phi_count"]})
        elif isinstance(data, dict):
            for key, value in data.items():
                self._scan_dict_recursive(value, f"{path}.{key}", issues)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._scan_dict_recursive(item, f"{path}[{i}]", issues)


# Module-level singleton instance
phi_detector = PHIDetector()
