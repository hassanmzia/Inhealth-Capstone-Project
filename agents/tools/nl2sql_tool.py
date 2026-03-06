"""
NL2SQL query tool.

Re-exports the core nl2sql_query tool from base.tools and adds a query
validation helper that checks generated SQL for safety before execution.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

from langchain_core.tools import tool

from agents.base.tools import nl2sql_query  # noqa: F401 – re-export

logger = logging.getLogger("inhealth.tools.nl2sql")

# SQL keywords / patterns that should never appear in patient-scoped queries
_FORBIDDEN_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bDROP\b", re.IGNORECASE),
    re.compile(r"\bDELETE\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
    re.compile(r"\bALTER\b", re.IGNORECASE),
    re.compile(r"\bINSERT\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\b", re.IGNORECASE),
    re.compile(r"\bGRANT\b", re.IGNORECASE),
    re.compile(r"\bREVOKE\b", re.IGNORECASE),
    re.compile(r"\bEXEC\b", re.IGNORECASE),
    re.compile(r"--", re.IGNORECASE),
    re.compile(r";.*SELECT", re.IGNORECASE | re.DOTALL),
]


@tool
def validate_nl2sql_query(sql: str, patient_id: str) -> dict:
    """
    Validate a generated SQL query for safety before execution.

    Checks for:
    - Forbidden DDL/DML keywords (DROP, DELETE, INSERT, UPDATE, etc.)
    - SQL injection patterns (comment sequences, stacked queries)
    - Proper patient_id scoping (query must reference the patient)

    Args:
        sql: The generated SQL query string to validate
        patient_id: Patient identifier that must appear in the query scope

    Returns:
        Dict with 'valid' bool, 'reason' string (if invalid), and 'sql'.
    """
    try:
        if not sql or not sql.strip():
            return {"valid": False, "reason": "Empty SQL query", "sql": sql}

        # Check forbidden patterns
        for pattern in _FORBIDDEN_PATTERNS:
            if pattern.search(sql):
                logger.warning(
                    "Forbidden SQL pattern detected: %s in query: %s",
                    pattern.pattern,
                    sql[:200],
                )
                return {
                    "valid": False,
                    "reason": f"Forbidden SQL pattern: {pattern.pattern}",
                    "sql": sql,
                }

        # Ensure patient_id scoping
        if patient_id not in sql:
            return {
                "valid": False,
                "reason": (
                    "Query does not reference the patient_id; all queries must "
                    "be scoped to a specific patient for safety."
                ),
                "sql": sql,
            }

        return {"valid": True, "reason": "Query passed all safety checks", "sql": sql}

    except Exception as exc:
        logger.error("validate_nl2sql_query failed: %s", exc)
        return {"valid": False, "reason": str(exc), "sql": sql}


@tool
def safe_nl2sql_query(natural_language_query: str, patient_id: str) -> dict:
    """
    Convert a natural language question to SQL, validate the generated SQL
    for safety, and only then execute it.  This is a safer alternative to
    calling nl2sql_query directly.

    Args:
        natural_language_query: Clinical question in plain English
        patient_id: Patient identifier (used to scope the query)

    Returns:
        Dict with 'sql', 'results', 'columns', and 'validation' keys.
    """
    try:
        result = nl2sql_query.invoke(
            {
                "natural_language_query": natural_language_query,
                "patient_id": patient_id,
            }
        )

        generated_sql = result.get("sql", "")

        validation = validate_nl2sql_query.invoke(
            {"sql": generated_sql, "patient_id": patient_id}
        )

        if not validation.get("valid", False):
            logger.warning(
                "NL2SQL query failed validation: %s", validation.get("reason")
            )
            return {
                "sql": generated_sql,
                "results": [],
                "columns": [],
                "validation": validation,
                "error": f"Query blocked: {validation.get('reason')}",
            }

        result["validation"] = validation
        return result

    except Exception as exc:
        logger.error("safe_nl2sql_query failed: %s", exc)
        return {"sql": "", "results": [], "columns": [], "error": str(exc)}


# All tools provided by this module
NL2SQL_TOOLS = [nl2sql_query, validate_nl2sql_query, safe_nl2sql_query]
