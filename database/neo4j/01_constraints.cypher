// ============================================================
// InHealth Chronic Care - Neo4j Constraints
// Uniqueness and existence constraints for knowledge graph
// ============================================================

// Patient node constraints
CREATE CONSTRAINT patient_id_unique IF NOT EXISTS
    FOR (p:Patient) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT patient_fhir_id_unique IF NOT EXISTS
    FOR (p:Patient) REQUIRE p.fhir_id IS UNIQUE;

// Disease node constraints
CREATE CONSTRAINT disease_icd10_unique IF NOT EXISTS
    FOR (d:Disease) REQUIRE d.icd10 IS UNIQUE;

// Medication node constraints
CREATE CONSTRAINT medication_rxnorm_unique IF NOT EXISTS
    FOR (m:Medication) REQUIRE m.rxnorm IS UNIQUE;

// Provider node constraints
CREATE CONSTRAINT provider_npi_unique IF NOT EXISTS
    FOR (pr:Provider) REQUIRE pr.npi IS UNIQUE;

// Organization node constraints
CREATE CONSTRAINT organization_id_unique IF NOT EXISTS
    FOR (o:Organization) REQUIRE o.id IS UNIQUE;

// ClinicalGuideline node constraints
CREATE CONSTRAINT guideline_id_unique IF NOT EXISTS
    FOR (g:ClinicalGuideline) REQUIRE g.id IS UNIQUE;

// Lab test node constraints
CREATE CONSTRAINT lab_test_loinc_unique IF NOT EXISTS
    FOR (l:LabTest) REQUIRE l.loinc IS UNIQUE;

// Procedure node constraints
CREATE CONSTRAINT procedure_cpt_unique IF NOT EXISTS
    FOR (proc:Procedure) REQUIRE proc.cpt IS UNIQUE;

// Gene node constraints (pharmacogenomics)
CREATE CONSTRAINT gene_hgnc_unique IF NOT EXISTS
    FOR (g:Gene) REQUIRE g.hgnc_id IS UNIQUE;

// Hospital node constraints
CREATE CONSTRAINT hospital_id_unique IF NOT EXISTS
    FOR (h:Hospital) REQUIRE h.id IS UNIQUE;

// Symptom node constraints
CREATE CONSTRAINT symptom_snomed_unique IF NOT EXISTS
    FOR (s:Symptom) REQUIRE s.snomed IS UNIQUE;

// RiskFactor node constraints
CREATE CONSTRAINT risk_factor_id_unique IF NOT EXISTS
    FOR (r:RiskFactor) REQUIRE r.id IS UNIQUE;

// MedicalSpecialty node constraints
CREATE CONSTRAINT specialty_id_unique IF NOT EXISTS
    FOR (sp:MedicalSpecialty) REQUIRE sp.id IS UNIQUE;

// Existence constraints for critical properties
CREATE CONSTRAINT disease_name_exists IF NOT EXISTS
    FOR (d:Disease) REQUIRE d.name IS NOT NULL;

CREATE CONSTRAINT medication_name_exists IF NOT EXISTS
    FOR (m:Medication) REQUIRE m.name IS NOT NULL;

CREATE CONSTRAINT patient_mrn_exists IF NOT EXISTS
    FOR (p:Patient) REQUIRE p.mrn IS NOT NULL;
