"""
Risk factor traversal queries using Neo4j graph algorithms.
"""

from typing import Any, Dict, List

from graph.connection import run_query


def get_patient_risk_traversal(patient_id: str) -> Dict:
    """
    Multi-hop risk factor traversal:
    Patient → Conditions → Risk Factors → Predicted Outcomes
    Returns a risk graph for visualization and ML feature extraction.
    """
    cypher = """
    MATCH (p:Patient {id: $patient_id})

    // Conditions
    OPTIONAL MATCH (p)-[:HAS_CONDITION]->(condition:Disease)

    // Medications
    OPTIONAL MATCH (p)-[:TAKES_MEDICATION]->(medication:Drug)

    // Risk factors from conditions
    OPTIONAL MATCH (condition)-[:RISK_FACTOR_FOR]->(risk_outcome:Disease)
    WHERE NOT (p)-[:HAS_CONDITION]->(risk_outcome)

    // Drug-condition interactions
    OPTIONAL MATCH (medication)-[:MAY_CAUSE]->(side_effect:Condition)

    RETURN p.id as patient_id,
           collect(DISTINCT condition.icd10) as current_conditions,
           collect(DISTINCT medication.name) as current_medications,
           collect(DISTINCT {
             outcome: risk_outcome.icd10,
             name: risk_outcome.name,
             risk_multiplier: 1.5
           }) as predicted_risk_outcomes,
           collect(DISTINCT {
             drug: medication.name,
             side_effect: side_effect.name,
             probability: side_effect.frequency
           }) as medication_risks
    """
    results = run_query(cypher, {"patient_id": patient_id})
    return results[0] if results else {}


def get_population_risk_distribution(tenant_id: str = None) -> List[Dict]:
    """
    Get risk score distribution across the patient population.
    Used for population health analytics.
    """
    cypher = """
    MATCH (p:Patient)
    WHERE $tenant_id IS NULL OR p.tenant_id = $tenant_id
    MATCH (p)-[:HAS_CONDITION]->(d:Disease)
    WITH p, count(d) as condition_count,
         count(CASE WHEN d.chronic = true THEN 1 END) as chronic_count
    RETURN
      CASE
        WHEN chronic_count >= 3 THEN 'high'
        WHEN chronic_count = 2 THEN 'medium'
        WHEN chronic_count = 1 THEN 'low'
        ELSE 'minimal'
      END as risk_tier,
      count(p) as patient_count,
      avg(condition_count) as avg_conditions
    ORDER BY patient_count DESC
    """
    return run_query(cypher, {"tenant_id": tenant_id})


def get_cascade_risk_factors(icd10_code: str, depth: int = 3) -> List[Dict]:
    """
    Get cascading risk factors for a condition up to N hops away.
    Implements backtracking DFS in Cypher.
    """
    cypher = """
    MATCH p = (start:Disease {icd10: $icd10})-[:RISK_FACTOR_FOR*1..$depth]->(outcome:Disease)
    WHERE start <> outcome
    WITH p, outcome,
         [rel in relationships(p) | rel.risk_multiplier] as multipliers
    RETURN outcome.icd10 as outcome_icd10,
           outcome.name as outcome_name,
           length(p) - 1 as hops,
           reduce(r = 1.0, m IN multipliers | r * coalesce(m, 1.5)) as combined_risk_multiplier,
           [node in nodes(p) | node.icd10] as risk_path
    ORDER BY combined_risk_multiplier DESC
    LIMIT 20
    """
    return run_query(cypher, {"icd10": icd10_code, "depth": depth})


def get_modifiable_risk_factors(patient_id: str) -> List[Dict]:
    """
    Identify modifiable risk factors for a patient.
    These are risk factors that can be addressed through intervention.
    """
    cypher = """
    MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(d:Disease)
    MATCH (d)-[:HAS_RISK_FACTOR]->(rf:RiskFactor)
    WHERE rf.modifiable = true
    OPTIONAL MATCH (rf)<-[:ADDRESSES]-(intervention:Intervention)
    RETURN rf.name as risk_factor,
           rf.category as category,
           rf.impact_score as impact_score,
           d.name as associated_condition,
           collect(intervention.name) as interventions
    ORDER BY rf.impact_score DESC
    """
    return run_query(cypher, {"patient_id": patient_id})
