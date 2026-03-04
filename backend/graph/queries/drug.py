"""
Drug interaction queries using Neo4j graph with backtracking search.
Implements multi-hop drug interaction detection.
"""

from typing import Any, Dict, List, Optional

from graph.connection import run_query, run_write_query


def check_drug_interactions(drug1_name: str, drug2_name: str) -> List[Dict]:
    """
    Check for direct and indirect drug-drug interactions.
    Uses graph traversal to find interaction paths.
    """
    cypher = """
    MATCH (d1:Drug)
    WHERE toLower(d1.name) CONTAINS toLower($drug1) OR d1.rxnorm = $drug1

    MATCH (d2:Drug)
    WHERE toLower(d2.name) CONTAINS toLower($drug2) OR d2.rxnorm = $drug2

    // Direct interaction
    OPTIONAL MATCH (d1)-[r:INTERACTS_WITH]->(d2)
    OPTIONAL MATCH (d2)-[r2:INTERACTS_WITH]->(d1)

    WITH d1, d2,
         CASE WHEN r IS NOT NULL THEN {
           type: 'direct',
           severity: r.severity,
           mechanism: r.mechanism,
           clinical_effect: r.clinical_effect,
           management: r.management,
           evidence_level: r.evidence_level
         }
         WHEN r2 IS NOT NULL THEN {
           type: 'direct',
           severity: r2.severity,
           mechanism: r2.mechanism,
           clinical_effect: r2.clinical_effect,
           management: r2.management,
           evidence_level: r2.evidence_level
         }
         ELSE null END as direct_interaction

    // Pharmacokinetic interactions via CYP enzymes
    OPTIONAL MATCH (d1)-[:INHIBITS|:INDUCES]->(enzyme:Enzyme)<-[:METABOLIZED_BY]-(d2)
    OPTIONAL MATCH (d1)-[:METABOLIZED_BY]->(enzyme2:Enzyme)<-[:INHIBITS|:INDUCES]-(d2)

    RETURN d1.name as drug1_name,
           d1.rxnorm as drug1_rxnorm,
           d2.name as drug2_name,
           d2.rxnorm as drug2_rxnorm,
           direct_interaction,
           collect(DISTINCT enzyme.name) as pk_enzymes_d1_affects_d2,
           collect(DISTINCT enzyme2.name) as pk_enzymes_d2_affects_d1
    """
    return run_query(cypher, {"drug1": drug1_name, "drug2": drug2_name})


def get_patient_drug_interactions(patient_id: str) -> List[Dict]:
    """
    Find all drug-drug interactions for a patient's current medication list.
    Uses backtracking to find all interaction pairs.
    """
    cypher = """
    MATCH (p:Patient {id: $patient_id})-[:TAKES_MEDICATION]->(d:Drug)
    WITH p, collect(d) as medications
    UNWIND range(0, size(medications)-2) as i
    UNWIND range(i+1, size(medications)-1) as j
    WITH medications[i] as drug1, medications[j] as drug2
    MATCH (drug1)-[r:INTERACTS_WITH]->(drug2)
    RETURN drug1.name as drug1,
           drug2.name as drug2,
           r.severity as severity,
           r.mechanism as mechanism,
           r.clinical_effect as clinical_effect,
           r.management as management
    ORDER BY
      CASE r.severity
        WHEN 'contraindicated' THEN 1
        WHEN 'major' THEN 2
        WHEN 'moderate' THEN 3
        WHEN 'minor' THEN 4
        ELSE 5
      END
    """
    return run_query(cypher, {"patient_id": patient_id})


def get_drug_alternatives(drug_rxnorm: str, condition_icd10: str = None) -> List[Dict]:
    """
    Find alternative medications for a given drug,
    optionally filtered by indication.
    """
    cypher = """
    MATCH (d:Drug {rxnorm: $rxnorm})
    MATCH (d)-[:IN_CLASS]->(class:DrugClass)<-[:IN_CLASS]-(alt:Drug)
    WHERE alt.rxnorm <> $rxnorm

    // Optionally filter by indication
    OPTIONAL MATCH (alt)-[:INDICATED_FOR]->(cond:Disease)
    WHERE $condition_icd10 IS NULL OR cond.icd10 = $condition_icd10

    RETURN alt.name as alternative_drug,
           alt.rxnorm as rxnorm,
           class.name as drug_class,
           alt.generic_name as generic_name,
           collect(DISTINCT cond.name) as indications
    ORDER BY alt.name
    LIMIT 10
    """
    return run_query(cypher, {"rxnorm": drug_rxnorm, "condition_icd10": condition_icd10})


def create_drug_node(rxnorm: str, name: str, generic_name: str = "", properties: Dict = None) -> None:
    """Create or update a Drug node in Neo4j."""
    cypher = """
    MERGE (d:Drug {rxnorm: $rxnorm})
    SET d.name = $name,
        d.generic_name = $generic_name,
        d.updated_at = datetime()
    """
    if properties:
        cypher = """
        MERGE (d:Drug {rxnorm: $rxnorm})
        SET d += $properties
        SET d.name = $name, d.generic_name = $generic_name
        SET d.updated_at = datetime()
        """
    run_write_query(cypher, {
        "rxnorm": rxnorm,
        "name": name,
        "generic_name": generic_name,
        "properties": properties or {},
    })


def create_drug_interaction(
    rxnorm1: str,
    rxnorm2: str,
    severity: str,
    mechanism: str = "",
    clinical_effect: str = "",
    management: str = "",
    evidence_level: str = "B",
) -> None:
    """Create a drug-drug interaction relationship in Neo4j."""
    cypher = """
    MATCH (d1:Drug {rxnorm: $rxnorm1})
    MATCH (d2:Drug {rxnorm: $rxnorm2})
    MERGE (d1)-[r:INTERACTS_WITH]->(d2)
    SET r.severity = $severity,
        r.mechanism = $mechanism,
        r.clinical_effect = $clinical_effect,
        r.management = $management,
        r.evidence_level = $evidence_level,
        r.updated_at = datetime()
    """
    run_write_query(cypher, {
        "rxnorm1": rxnorm1,
        "rxnorm2": rxnorm2,
        "severity": severity,
        "mechanism": mechanism,
        "clinical_effect": clinical_effect,
        "management": management,
        "evidence_level": evidence_level,
    })


def get_high_risk_combinations(patient_id: str) -> List[Dict]:
    """
    Find all contraindicated or major drug interactions for a patient.
    Used by the Medication Safety Agent.
    """
    cypher = """
    MATCH (p:Patient {id: $patient_id})-[:TAKES_MEDICATION]->(d:Drug)
    WITH collect(d) as meds
    UNWIND meds as d1
    UNWIND meds as d2
    WITH d1, d2 WHERE d1.rxnorm < d2.rxnorm  // Avoid duplicates
    MATCH (d1)-[r:INTERACTS_WITH]->(d2)
    WHERE r.severity IN ['contraindicated', 'major']
    RETURN d1.name as drug1,
           d2.name as drug2,
           r.severity as severity,
           r.clinical_effect as clinical_effect,
           r.management as recommended_action
    ORDER BY CASE r.severity WHEN 'contraindicated' THEN 1 ELSE 2 END
    """
    return run_query(cypher, {"patient_id": patient_id})
