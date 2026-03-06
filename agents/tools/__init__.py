"""
InHealth AI modular tool registry.

Re-exports every tool from the domain-specific modules as well as all tools
from agents.base.tools so that callers can do::

    from agents.tools import query_fhir_database, plan_route_to_hospital
    from agents.tools import ALL_TOOLS
"""

from __future__ import annotations

# ── Base tools (complete set) ──────────────────────────────────────────────
from agents.base.tools import (
    ALL_TOOLS as _BASE_TOOLS,
    TOOL_MAP as BASE_TOOL_MAP,
    calculate_risk_score,
    check_drug_interactions,
    detect_phi,
    find_nearest_hospital,
    nl2sql_query,
    query_fhir_database,
    query_graph_database,
    redact_phi,
    schedule_appointment,
    search_clinical_trials,
    search_pubmed,
    send_notification,
    transcribe_voice,
    vector_search,
)

# ── Domain-specific modules ───────────────────────────────────────────────
from agents.tools.fhir_tools import (
    FHIR_TOOLS,
    get_patient_summary,
    validate_fhir_resource_type,
)
from agents.tools.graph_tools import (
    GRAPH_TOOLS,
    find_alternative_drugs,
    get_condition_relationships,
)
from agents.tools.vector_tools import (
    VECTOR_TOOLS,
    search_clinical_guidelines,
    search_pubmed_vectors,
)
from agents.tools.notification_tools import (
    NOTIFICATION_TOOLS,
    schedule_followup_reminder,
    send_bulk_notifications,
)
from agents.tools.geospatial_tools import (
    GEOSPATIAL_TOOLS,
    find_hospitals_in_radius,
    plan_route_to_hospital,
)
from agents.tools.nl2sql_tool import (
    NL2SQL_TOOLS,
    safe_nl2sql_query,
    validate_nl2sql_query,
)
from agents.tools.voice_tool import (
    VOICE_TOOLS,
    extract_clinical_entities,
    transcribe_and_structure,
)

# ── Aggregate registries ──────────────────────────────────────────────────

# All tools: base tools + every helper added by the domain modules
ALL_TOOLS = list(
    {t.name: t for t in (
        _BASE_TOOLS
        + [
            # FHIR helpers
            validate_fhir_resource_type,
            get_patient_summary,
            # Graph helpers
            get_condition_relationships,
            find_alternative_drugs,
            # Vector helpers
            search_clinical_guidelines,
            search_pubmed_vectors,
            # Notification helpers
            send_bulk_notifications,
            schedule_followup_reminder,
            # Geospatial helpers
            plan_route_to_hospital,
            find_hospitals_in_radius,
            # NL2SQL helpers
            validate_nl2sql_query,
            safe_nl2sql_query,
            # Voice helpers
            transcribe_and_structure,
            extract_clinical_entities,
        ]
    )}.values()
)

TOOL_MAP = {t.name: t for t in ALL_TOOLS}

__all__ = [
    # Registries
    "ALL_TOOLS",
    "TOOL_MAP",
    "BASE_TOOL_MAP",
    # Per-domain tool lists
    "FHIR_TOOLS",
    "GRAPH_TOOLS",
    "VECTOR_TOOLS",
    "NOTIFICATION_TOOLS",
    "GEOSPATIAL_TOOLS",
    "NL2SQL_TOOLS",
    "VOICE_TOOLS",
    # Base tools
    "query_fhir_database",
    "query_graph_database",
    "vector_search",
    "check_drug_interactions",
    "calculate_risk_score",
    "send_notification",
    "schedule_appointment",
    "find_nearest_hospital",
    "nl2sql_query",
    "search_pubmed",
    "search_clinical_trials",
    "transcribe_voice",
    "detect_phi",
    "redact_phi",
    # FHIR helpers
    "validate_fhir_resource_type",
    "get_patient_summary",
    # Graph helpers
    "get_condition_relationships",
    "find_alternative_drugs",
    # Vector helpers
    "search_clinical_guidelines",
    "search_pubmed_vectors",
    # Notification helpers
    "send_bulk_notifications",
    "schedule_followup_reminder",
    # Geospatial helpers
    "plan_route_to_hospital",
    "find_hospitals_in_radius",
    # NL2SQL helpers
    "validate_nl2sql_query",
    "safe_nl2sql_query",
    # Voice helpers
    "transcribe_and_structure",
    "extract_clinical_entities",
]
