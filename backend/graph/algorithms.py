"""
Graph algorithms for medical knowledge graph analytics.
Implements PageRank risk scoring and community detection.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from graph.connection import run_query, run_write_query

logger = logging.getLogger("graph.algorithms")


def run_pagerank_risk_scoring(
    tenant_id: str = None,
    damping_factor: float = 0.85,
    iterations: int = 20,
) -> List[Dict]:
    """
    Run PageRank on the patient-disease-drug graph to identify high-influence diseases.
    High-PageRank nodes are clinically significant conditions that many risk paths pass through.

    Uses Neo4j GDS (Graph Data Science) library if available, otherwise manual implementation.
    """
    try:
        # Attempt to use Neo4j GDS PageRank
        cypher = """
        CALL gds.pageRank.stream({
          nodeProjection: ['Disease', 'RiskFactor'],
          relationshipProjection: {
            RISK_FACTOR_FOR: {orientation: 'NATURAL'},
            COMORBID_WITH: {orientation: 'UNDIRECTED'}
          },
          dampingFactor: $damping_factor,
          maxIterations: $iterations
        })
        YIELD nodeId, score
        WITH gds.util.asNode(nodeId) as node, score
        WHERE node:Disease
        RETURN node.icd10 as icd10, node.name as name, score
        ORDER BY score DESC
        LIMIT 50
        """
        return run_query(cypher, {
            "damping_factor": damping_factor,
            "iterations": iterations,
        })
    except Exception as e:
        logger.warning(f"GDS PageRank unavailable ({e}), using manual implementation")
        return _manual_pagerank_diseases()


def _manual_pagerank_diseases() -> List[Dict]:
    """Manual PageRank approximation using in/out degree centrality."""
    cypher = """
    MATCH (d:Disease)
    OPTIONAL MATCH (d)<-[:RISK_FACTOR_FOR]-(incoming)
    OPTIONAL MATCH (d)-[:RISK_FACTOR_FOR]->(outgoing)
    WITH d,
         count(DISTINCT incoming) as in_degree,
         count(DISTINCT outgoing) as out_degree
    RETURN d.icd10 as icd10,
           d.name as name,
           in_degree + out_degree as degree_centrality,
           toFloat(in_degree) / (in_degree + out_degree + 0.001) as authority_score
    ORDER BY degree_centrality DESC
    LIMIT 50
    """
    return run_query(cypher, {})


def detect_disease_communities() -> List[Dict]:
    """
    Detect communities of related diseases using Louvain community detection.
    Diseases in the same community tend to co-occur (e.g., metabolic syndrome cluster).
    """
    try:
        # Attempt GDS Louvain
        cypher = """
        CALL gds.louvain.stream({
          nodeProjection: 'Disease',
          relationshipProjection: {
            COMORBID_WITH: {orientation: 'UNDIRECTED', properties: 'co_occurrence_rate'}
          }
        })
        YIELD nodeId, communityId
        WITH gds.util.asNode(nodeId) as disease, communityId
        RETURN communityId,
               collect(disease.name) as diseases,
               collect(disease.icd10) as icd10_codes,
               count(*) as community_size
        ORDER BY community_size DESC
        LIMIT 20
        """
        return run_query(cypher, {})
    except Exception as e:
        logger.warning(f"GDS Louvain unavailable ({e}), using manual community approximation")
        return _manual_disease_communities()


def _manual_disease_communities() -> List[Dict]:
    """Manual community detection based on high co-occurrence rate."""
    cypher = """
    MATCH (d1:Disease)-[r:COMORBID_WITH]->(d2:Disease)
    WHERE r.co_occurrence_rate > 0.3
    WITH d1, collect(d2.name) as cluster_members, collect(d2.icd10) as cluster_codes
    WHERE size(cluster_members) >= 2
    RETURN d1.icd10 as anchor_icd10,
           d1.name as anchor_disease,
           cluster_members,
           cluster_codes,
           size(cluster_members) as cluster_size
    ORDER BY cluster_size DESC
    LIMIT 20
    """
    return run_query(cypher, {})


def find_shortest_disease_path(icd10_start: str, icd10_end: str) -> List[Dict]:
    """
    Find the shortest clinical pathway between two diseases.
    Useful for understanding disease progression and treatment planning.
    """
    cypher = """
    MATCH p = shortestPath(
      (start:Disease {icd10: $start})-[:RISK_FACTOR_FOR|PROGRESSES_TO|COMORBID_WITH*..6]-(end:Disease {icd10: $end})
    )
    RETURN [node in nodes(p) | node.icd10] as path_icd10,
           [node in nodes(p) | node.name] as path_names,
           [rel in relationships(p) | type(rel)] as relationship_types,
           length(p) as path_length
    ORDER BY path_length
    LIMIT 5
    """
    return run_query(cypher, {"start": icd10_start, "end": icd10_end})


def calculate_patient_graph_risk_score(patient_id: str) -> Tuple[float, Dict]:
    """
    Calculate a patient's graph-based risk score.
    Combines: PageRank of conditions + number of interactions + comorbidity density.

    Returns (risk_score 0-1, feature_dict).
    """
    cypher = """
    MATCH (p:Patient {id: $patient_id})
    OPTIONAL MATCH (p)-[:HAS_CONDITION]->(d:Disease)
    OPTIONAL MATCH (d)-[comorbid:COMORBID_WITH]->(:Disease)
    OPTIONAL MATCH (p)-[:TAKES_MEDICATION]->(m:Drug)-[interaction:INTERACTS_WITH]->(:Drug)
    WITH p,
         count(DISTINCT d) as condition_count,
         count(DISTINCT comorbid) as comorbidity_links,
         count(DISTINCT CASE WHEN interaction.severity IN ['major', 'contraindicated'] THEN interaction END) as high_risk_interactions,
         collect(DISTINCT d.chronic) as chronic_flags
    RETURN condition_count,
           comorbidity_links,
           high_risk_interactions,
           size([f IN chronic_flags WHERE f = true]) as chronic_condition_count
    """
    results = run_query(cypher, {"patient_id": patient_id})
    if not results:
        return 0.0, {}

    data = results[0]
    condition_count = data.get("condition_count", 0) or 0
    chronic_count = data.get("chronic_condition_count", 0) or 0
    interactions = data.get("high_risk_interactions", 0) or 0
    comorbidity_links = data.get("comorbidity_links", 0) or 0

    # Weighted risk score formula
    score = min(1.0, (
        (chronic_count * 0.20) +  # Chronic conditions are high weight
        (condition_count * 0.10) +  # Total conditions
        (interactions * 0.30) +  # Drug interactions are critical
        (comorbidity_links * 0.05)  # Comorbidity density
    ) / 3.0)

    features = {
        "condition_count": condition_count,
        "chronic_condition_count": chronic_count,
        "high_risk_drug_interactions": interactions,
        "comorbidity_links": comorbidity_links,
    }

    return score, features
