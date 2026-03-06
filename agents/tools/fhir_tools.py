"""
FHIR database query tools.

Re-exports the core query_fhir_database tool from base.tools and provides
additional FHIR-specific helpers for resource validation and patient summary
retrieval.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from agents.base.tools import query_fhir_database  # noqa: F401 – re-export

logger = logging.getLogger("inhealth.tools.fhir")

# Valid FHIR R4 resource types supported by InHealth
_SUPPORTED_FHIR_RESOURCES = frozenset(
    {
        "Observation",
        "MedicationRequest",
        "MedicationStatement",
        "Condition",
        "Procedure",
        "Encounter",
        "DiagnosticReport",
        "AllergyIntolerance",
        "Immunization",
        "CarePlan",
        "Goal",
        "ClinicalImpression",
    }
)


@tool
def validate_fhir_resource_type(resource_type: str) -> dict:
    """
    Validate whether a FHIR resource type is supported by the InHealth system.

    Args:
        resource_type: FHIR R4 resource type name (e.g., 'Observation',
                       'MedicationRequest')

    Returns:
        Dict with 'valid' bool, 'resource_type' string, and 'supported_types'
        list when invalid.
    """
    try:
        is_valid = resource_type in _SUPPORTED_FHIR_RESOURCES
        result: Dict[str, Any] = {
            "valid": is_valid,
            "resource_type": resource_type,
        }
        if not is_valid:
            result["supported_types"] = sorted(_SUPPORTED_FHIR_RESOURCES)
            logger.warning(
                "Unsupported FHIR resource type requested: %s", resource_type
            )
        return result
    except Exception as exc:
        logger.error("validate_fhir_resource_type failed: %s", exc)
        return {"valid": False, "error": str(exc)}


@tool
def get_patient_summary(patient_id: str) -> dict:
    """
    Retrieve a high-level clinical summary for a patient by fetching recent
    records across multiple FHIR resource types (Observations, Conditions,
    MedicationRequests, and AllergyIntolerances).

    Args:
        patient_id: FHIR patient identifier

    Returns:
        Dict keyed by resource type, each containing the most recent records.
    """
    try:
        summary: Dict[str, Any] = {"patient_id": patient_id}
        resource_types = [
            "Observation",
            "Condition",
            "MedicationRequest",
            "AllergyIntolerance",
        ]

        for rtype in resource_types:
            result = query_fhir_database.invoke(
                {
                    "resource_type": rtype,
                    "patient_id": patient_id,
                    "filters": {"limit": 5},
                }
            )
            summary[rtype.lower()] = result.get("resources", [])

        summary["status"] = "ok"
        return summary

    except Exception as exc:
        logger.error("get_patient_summary failed: %s", exc)
        return {"patient_id": patient_id, "status": "error", "error": str(exc)}


# All tools provided by this module
FHIR_TOOLS = [query_fhir_database, validate_fhir_resource_type, get_patient_summary]
