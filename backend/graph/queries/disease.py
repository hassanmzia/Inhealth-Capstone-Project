"""
Disease relationship queries for the Neo4j medical knowledge graph.
"""

from typing import Any, Dict, List

from graph.connection import run_query, run_write_query


def get_disease_comorbidities(icd10_code: str, limit: int = 20) -> List[Dict]:
    """Get common comorbidities for a given disease."""
    cypher = """
    MATCH (d:Disease {icd10: $icd10})
    MATCH (d)-[r:COMORBID_WITH]->(comorbid:Disease)
    RETURN comorbid.icd10 as icd10,
           comorbid.name as name,
           r.co_occurrence_rate as co_occurrence_rate,
           r.relative_risk as relative_risk
    ORDER BY r.co_occurrence_rate DESC
    LIMIT $limit
    """
    return run_query(cypher, {"icd10": icd10_code, "limit": limit})


def get_disease_progression_paths(icd10_code: str, max_depth: int = 3) -> List[Dict]:
    """
    Get disease progression pathways — what conditions commonly develop
    from a given condition over time.
    """
    cypher = """
    MATCH path = (d:Disease {icd10: $icd10})-[:PROGRESSES_TO*1..$max_depth]->(outcome:Disease)
    RETURN [node in nodes(path) | node.icd10] as progression_path,
           [node in nodes(path) | node.name] as disease_names,
           length(path) as progression_steps,
           [rel in relationships(path) | rel.median_years] as median_years_to_next
    ORDER BY length(path), outcome.name
    LIMIT 30
    """
    return run_query(cypher, {"icd10": icd10_code, "max_depth": max_depth})


def get_related_symptoms(icd10_code: str) -> List[Dict]:
    """Get symptoms commonly associated with a disease."""
    cypher = """
    MATCH (d:Disease {icd10: $icd10})-[r:HAS_SYMPTOM]->(s:Symptom)
    RETURN s.name as symptom,
           s.snomed as snomed_code,
           r.frequency as frequency,
           r.severity_association as severity
    ORDER BY r.frequency DESC
    """
    return run_query(cypher, {"icd10": icd10_code})


def get_differential_diagnoses(symptoms: List[str], limit: int = 10) -> List[Dict]:
    """
    Generate differential diagnoses based on a list of symptoms.
    Uses graph traversal to find diseases matching the symptom combination.
    """
    cypher = """
    UNWIND $symptoms as symptom_name
    MATCH (s:Symptom)
    WHERE toLower(s.name) CONTAINS toLower(symptom_name)
    MATCH (d:Disease)-[:HAS_SYMPTOM]->(s)
    WITH d, count(s) as matching_symptoms, collect(s.name) as matched_symptom_names
    RETURN d.icd10 as icd10,
           d.name as disease_name,
           matching_symptoms,
           matched_symptom_names,
           toFloat(matching_symptoms) / size($symptoms) as symptom_coverage
    ORDER BY matching_symptoms DESC, symptom_coverage DESC
    LIMIT $limit
    """
    return run_query(cypher, {"symptoms": symptoms, "limit": limit})


def get_disease_risk_genes(icd10_code: str) -> List[Dict]:
    """Get genetic risk factors associated with a disease."""
    cypher = """
    MATCH (d:Disease {icd10: $icd10})-[r:ASSOCIATED_WITH_GENE]->(g:Gene)
    RETURN g.symbol as gene_symbol,
           g.name as gene_name,
           r.odds_ratio as odds_ratio,
           r.p_value as p_value,
           r.study_count as study_count
    ORDER BY r.odds_ratio DESC
    LIMIT 20
    """
    return run_query(cypher, {"icd10": icd10_code})


def get_treatment_pathways(icd10_code: str) -> List[Dict]:
    """Get evidence-based treatment pathways for a condition."""
    cypher = """
    MATCH (d:Disease {icd10: $icd10})-[r:TREATED_BY]->(drug:Drug)
    OPTIONAL MATCH (d)-[:TREATED_BY]->(proc:Procedure)
    RETURN drug.name as treatment_name,
           'medication' as treatment_type,
           r.evidence_level as evidence_level,
           r.guideline_source as guideline_source,
           r.first_line as is_first_line
    ORDER BY r.first_line DESC, r.evidence_level ASC
    """
    return run_query(cypher, {"icd10": icd10_code})
