"""
Patient-related Cypher queries for the Neo4j medical knowledge graph.
"""

from typing import Any, Dict, List, Optional

from graph.connection import run_query, run_write_query


def create_or_update_patient_node(patient_id: str, properties: Dict) -> Dict:
    """Create or update a Patient node in Neo4j."""
    cypher = """
    MERGE (p:Patient {id: $patient_id})
    SET p += $properties
    SET p.updated_at = datetime()
    RETURN p
    """
    result = run_write_query(cypher, {"patient_id": patient_id, "properties": properties})
    return result[0] if result else {}


def link_patient_to_condition(patient_id: str, icd10_code: str, onset_date: str = None) -> None:
    """Create HAS_CONDITION relationship between patient and disease node."""
    cypher = """
    MATCH (p:Patient {id: $patient_id})
    MERGE (d:Disease {icd10: $icd10_code})
    MERGE (p)-[r:HAS_CONDITION]->(d)
    SET r.onset_date = $onset_date
    SET r.updated_at = datetime()
    """
    run_write_query(cypher, {
        "patient_id": patient_id,
        "icd10_code": icd10_code,
        "onset_date": onset_date,
    })


def link_patient_to_medication(patient_id: str, rxnorm_code: str, start_date: str = None) -> None:
    """Create TAKES_MEDICATION relationship."""
    cypher = """
    MATCH (p:Patient {id: $patient_id})
    MERGE (m:Drug {rxnorm: $rxnorm_code})
    MERGE (p)-[r:TAKES_MEDICATION]->(m)
    SET r.start_date = $start_date
    SET r.updated_at = datetime()
    """
    run_write_query(cypher, {
        "patient_id": patient_id,
        "rxnorm_code": rxnorm_code,
        "start_date": start_date,
    })


def get_patient_comorbidity_network(patient_id: str) -> List[Dict]:
    """
    Get a patient's comorbidity network — conditions they share with similar patients.
    Useful for identifying undiagnosed conditions.
    """
    cypher = """
    MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(d:Disease)
    MATCH (other:Patient)-[:HAS_CONDITION]->(d)
    WHERE other.id <> $patient_id
    WITH other, count(d) as shared_conditions
    WHERE shared_conditions >= 2
    MATCH (other)-[:HAS_CONDITION]->(other_disease:Disease)
    WHERE NOT (p)-[:HAS_CONDITION]->(other_disease)
    RETURN other_disease.icd10 as icd10,
           other_disease.name as disease_name,
           count(other) as co_occurrence_count,
           avg(shared_conditions) as avg_shared_conditions
    ORDER BY co_occurrence_count DESC
    LIMIT 10
    """
    return run_query(cypher, {"patient_id": patient_id})


def get_patient_risk_factors_graph(patient_id: str) -> List[Dict]:
    """
    Traverse risk factor relationships for a patient.
    Returns conditions → risk_factors → potential_outcomes paths.
    """
    cypher = """
    MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(d:Disease)
    MATCH (d)-[:RISK_FACTOR_FOR]->(outcome:Disease)
    OPTIONAL MATCH (d)-[:HAS_BIOMARKER]->(b:Biomarker)
    RETURN d.icd10 as current_condition,
           d.name as condition_name,
           outcome.icd10 as risk_outcome_icd10,
           outcome.name as risk_outcome_name,
           collect(b.name) as biomarkers
    ORDER BY d.icd10
    LIMIT 20
    """
    return run_query(cypher, {"patient_id": patient_id})


def find_similar_patients(patient_id: str, min_similarity: float = 0.7) -> List[Dict]:
    """
    Find clinically similar patients using Jaccard similarity of conditions.
    """
    cypher = """
    MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(d:Disease)
    WITH p, collect(d.icd10) as p_conditions
    MATCH (other:Patient)-[:HAS_CONDITION]->(od:Disease)
    WHERE other.id <> p.id
    WITH p, p_conditions, other, collect(od.icd10) as other_conditions
    WITH p, other,
         p_conditions, other_conditions,
         size([x IN p_conditions WHERE x IN other_conditions]) as intersection,
         size(p_conditions + [x IN other_conditions WHERE NOT x IN p_conditions]) as union_size
    WITH p, other,
         toFloat(intersection) / union_size as jaccard_similarity
    WHERE jaccard_similarity >= $min_similarity
    RETURN other.id as similar_patient_id,
           jaccard_similarity,
           other.age as age,
           other.gender as gender
    ORDER BY jaccard_similarity DESC
    LIMIT 20
    """
    return run_query(cypher, {"patient_id": patient_id, "min_similarity": min_similarity})
