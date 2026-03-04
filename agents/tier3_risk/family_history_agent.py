"""
Agent 11 — Family History Risk Agent

Responsibilities:
  - Query Neo4j for patient's family members and their conditions
  - Calculate polygenic risk score approximation
  - Gene-disease associations (BRCA1, APOE, etc.)
  - Generate genetic counseling recommendations
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from base.agent import MCPAgent
from base.tools import query_fhir_database, query_graph_database, vector_search

logger = logging.getLogger("inhealth.agent.family_history")

# Gene-disease high-penetrance associations
GENE_DISEASE_ASSOCIATIONS = {
    "BRCA1": {"diseases": ["breast_cancer", "ovarian_cancer"], "lifetime_risk": "50-85%", "action": "Oncology referral, enhanced screening"},
    "BRCA2": {"diseases": ["breast_cancer", "pancreatic_cancer"], "lifetime_risk": "45-70%", "action": "Oncology referral"},
    "APOE_E4": {"diseases": ["alzheimers_disease"], "lifetime_risk": "3× increased", "action": "Neurology referral, cognitive monitoring"},
    "LDLR": {"diseases": ["familial_hypercholesterolemia"], "lifetime_risk": "High", "action": "Lipid specialist referral, high-intensity statin"},
    "MTHFR": {"diseases": ["cardiovascular_disease", "thrombophilia"], "lifetime_risk": "Moderate", "action": "Folate supplementation, homocysteine monitoring"},
    "HBB": {"diseases": ["sickle_cell_disease", "thalassemia"], "lifetime_risk": "Autosomal recessive", "action": "Hematology referral if symptomatic"},
    "MLH1": {"diseases": ["colorectal_cancer", "endometrial_cancer"], "lifetime_risk": "Lynch syndrome: 70-80%", "action": "Colonoscopy q1-2y starting age 20-25"},
}

# Heritability of common conditions (approximate %)
HERITABILITY = {
    "type2_diabetes": 0.50,
    "hypertension": 0.57,
    "coronary_artery_disease": 0.55,
    "colorectal_cancer": 0.35,
    "breast_cancer": 0.31,
    "alzheimers_disease": 0.60,
    "atrial_fibrillation": 0.42,
    "obesity": 0.71,
    "depression": 0.37,
    "asthma": 0.60,
}


class FamilyHistoryAgent(MCPAgent):
    """Agent 11: Family history risk assessment and genetic counseling."""

    agent_id = 11
    agent_name = "family_history_agent"
    agent_tier = "tier3_risk"
    system_prompt = (
        "You are the Family History Risk AI Agent for InHealth Chronic Care. "
        "You analyze patient family history from the genomic knowledge graph, "
        "approximate polygenic risk scores, and identify high-penetrance gene-disease associations. "
        "Provide evidence-based genetic counseling recommendations. "
        "Reference USPSTF genetic testing guidelines, NCCN hereditary cancer guidelines, and AHA/ACC familial risk guidelines."
    )

    def _default_tools(self):
        return [query_fhir_database, query_graph_database, vector_search]

    async def analyze(
        self,
        patient_id: str,
        state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:

        # Query Neo4j for family history
        try:
            family_query = """
            MATCH (p:Patient {id: $patient_id})-[:HAS_FAMILY_MEMBER]->(fm:Patient)
            MATCH (fm)-[:HAS_CONDITION]->(c:Condition)
            RETURN fm.relationship AS relationship, fm.deceased AS deceased,
                   fm.age_at_death AS age_at_death, c.name AS condition,
                   c.age_at_diagnosis AS age_at_diagnosis
            ORDER BY fm.relationship
            """
            family_conditions = query_graph_database.invoke({
                "cypher_query": family_query,
                "params": {"patient_id": patient_id},
            })
        except Exception as exc:
            logger.warning("Family history graph query failed: %s", exc)
            family_conditions = []

        # Also check FHIR FamilyMemberHistory resources
        try:
            fhir_fmh = query_fhir_database.invoke({
                "resource_type": "FamilyMemberHistory",
                "patient_id": patient_id,
                "filters": {"limit": 50},
            })
            fhir_family = self._parse_fhir_family(fhir_fmh.get("resources", []))
        except Exception as exc:
            logger.warning("FHIR FamilyMemberHistory fetch failed: %s", exc)
            fhir_family = []

        # Merge family data
        all_family = family_conditions + fhir_family

        # Calculate polygenic risk score approximation
        prs_approximation = self._approximate_prs(all_family)

        # Check for high-penetrance gene markers (from patient genomic data if available)
        try:
            genomic_query = """
            MATCH (p:Patient {id: $patient_id})-[:HAS_GENETIC_VARIANT]->(g:GeneticVariant)
            WHERE g.clinical_significance IN ['pathogenic', 'likely_pathogenic']
            RETURN g.gene AS gene, g.variant AS variant,
                   g.clinical_significance AS significance,
                   g.associated_conditions AS conditions
            """
            genomic_variants = query_graph_database.invoke({
                "cypher_query": genomic_query,
                "params": {"patient_id": patient_id},
            })
        except Exception as exc:
            logger.warning("Genomic variant query failed: %s", exc)
            genomic_variants = []

        # Map genomic variants to gene-disease associations
        high_penetrance_findings = []
        for variant in genomic_variants:
            gene = variant.get("gene", "")
            if gene in GENE_DISEASE_ASSOCIATIONS:
                assoc = GENE_DISEASE_ASSOCIATIONS[gene]
                high_penetrance_findings.append({
                    "gene": gene,
                    "variant": variant.get("variant", ""),
                    "diseases": assoc["diseases"],
                    "lifetime_risk": assoc["lifetime_risk"],
                    "recommended_action": assoc["action"],
                })

        # Early-onset disease flags
        early_onset_flags = self._check_early_onset(all_family)

        # RAG: retrieve genetic counseling guidelines
        try:
            guidelines = vector_search.invoke({
                "query": f"genetic counseling family history risk assessment hereditary cancer syndrome",
                "collection": "clinical_guidelines",
                "top_k": 3,
            })
        except Exception as exc:
            logger.warning("Family history RAG failed: %s", exc)
            guidelines = []

        alerts = []
        if high_penetrance_findings:
            for finding in high_penetrance_findings:
                alerts.append(self._build_alert(
                    severity="HIGH",
                    message=f"High-penetrance genetic finding: {finding['gene']} variant — lifetime risk {finding['lifetime_risk']} for {', '.join(finding['diseases'])}. {finding['recommended_action']}",
                    patient_id=patient_id,
                    details=finding,
                ))

        for flag in early_onset_flags:
            alerts.append(self._build_alert(
                severity="NORMAL",
                message=f"Early-onset family history: {flag['condition']} in first-degree relative age {flag['age']}. Enhanced screening recommended.",
                patient_id=patient_id,
                details=flag,
            ))

        # LLM comprehensive analysis
        family_summary = "\n".join([
            f"  {fc.get('relationship', 'relative')}: {fc.get('condition', 'unknown')} (age {fc.get('age_at_diagnosis', '?')})"
            for fc in all_family[:15]
        ])
        llm_input = (
            f"Patient {patient_id} family history and genetic risk:\n\n"
            f"Family conditions:\n{family_summary}\n\n"
            f"Polygenic risk approximation:\n"
            + "\n".join([f"  {k}: {v['risk_level']} (heritability-adjusted)" for k, v in prs_approximation.items()])
            + f"\n\nHigh-penetrance genetic findings: {high_penetrance_findings}\n"
            f"Early-onset disease flags: {early_onset_flags}\n\n"
            f"Provide:\n"
            f"1. Overall hereditary risk assessment with quantified estimates\n"
            f"2. Specific genetic testing recommendations (USPSTF/NCCN guidelines)\n"
            f"3. Enhanced screening protocols based on family history\n"
            f"4. Cascade testing recommendations for at-risk family members\n"
            f"5. Genetic counseling referral urgency"
        )

        try:
            llm_result = await self.run_agent_chain(input_text=llm_input)
            genetic_counseling_report = llm_result.get("output", "")
        except Exception as exc:
            logger.warning("Family history LLM analysis failed: %s", exc)
            genetic_counseling_report = ""

        return self._build_result(
            status="completed",
            findings={
                "family_conditions": all_family[:20],
                "polygenic_risk_approximation": prs_approximation,
                "high_penetrance_findings": high_penetrance_findings,
                "early_onset_flags": early_onset_flags,
                "genomic_variants": genomic_variants,
                "genetic_counseling_report": genetic_counseling_report,
                "guidelines_retrieved": len(guidelines),
            },
            alerts=alerts,
            recommendations=self._generate_recommendations(high_penetrance_findings, prs_approximation),
        )

    def _parse_fhir_family(self, resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        for r in resources:
            meta = r.get("meta", {})
            result.append({
                "relationship": r.get("code", "unknown"),
                "condition": r.get("value", "unknown"),
                "age_at_diagnosis": meta.get("onset_age", "unknown"),
                "source": "fhir",
            })
        return result

    def _approximate_prs(self, family_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Approximate polygenic risk based on first-degree relative disease count."""
        condition_counts: Dict[str, int] = {}
        first_degree_conditions: Dict[str, int] = {}

        for fc in family_data:
            condition = fc.get("condition", "").lower().replace(" ", "_")
            relationship = fc.get("relationship", "").lower()
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
            if relationship in ("parent", "sibling", "child"):
                first_degree_conditions[condition] = first_degree_conditions.get(condition, 0) + 1

        prs: Dict[str, Any] = {}
        for condition, heritability in HERITABILITY.items():
            first_degree_count = first_degree_conditions.get(condition, 0)
            if first_degree_count >= 2:
                risk_level = "HIGH"
                risk_multiplier = 3.0
            elif first_degree_count == 1:
                risk_level = "MODERATE"
                risk_multiplier = 1.5 + heritability
            else:
                continue

            prs[condition] = {
                "risk_level": risk_level,
                "risk_multiplier": round(risk_multiplier, 2),
                "first_degree_affected": first_degree_count,
                "condition_heritability": heritability,
            }

        return prs

    def _check_early_onset(self, family_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flag conditions with early-onset in first-degree relatives."""
        flags = []
        early_onset_thresholds = {
            "heart disease": 55,     # men < 55, women < 65 — using conservative 55
            "breast cancer": 50,
            "colon cancer": 50,
            "diabetes": 40,
            "stroke": 55,
        }
        for fc in family_data:
            relationship = fc.get("relationship", "").lower()
            if relationship not in ("parent", "sibling", "child", "father", "mother", "brother", "sister"):
                continue
            condition = fc.get("condition", "").lower()
            age_at_dx = fc.get("age_at_diagnosis", "")
            try:
                age = int(str(age_at_dx).split()[0])
            except (ValueError, TypeError):
                continue
            for cond_key, threshold in early_onset_thresholds.items():
                if cond_key in condition and age < threshold:
                    flags.append({
                        "condition": condition,
                        "relationship": relationship,
                        "age": age,
                        "threshold": threshold,
                    })
        return flags

    def _generate_recommendations(
        self,
        high_penetrance: List[Dict[str, Any]],
        prs: Dict[str, Any],
    ) -> List[str]:
        recs = []
        if high_penetrance:
            recs.append("Genetic counseling referral: High-penetrance variant(s) identified. Patient and first-degree relatives should receive genetic counseling.")
        for finding in high_penetrance:
            if "BRCA" in finding.get("gene", ""):
                recs.append("BRCA variant: Annual breast MRI + mammogram (NCCN Category 1). Consider risk-reducing surgery discussion with oncologist.")
        if any(v.get("risk_level") == "HIGH" for v in prs.values()):
            recs.append("High polygenic risk in first-degree relatives: Enhanced screening protocol with earlier initiation and shorter intervals.")
        return recs
