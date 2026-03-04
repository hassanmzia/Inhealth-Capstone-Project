// ============================================================
// InHealth Chronic Care - Neo4j Performance Indexes
// Range and text indexes for knowledge graph queries
// ============================================================

// Patient indexes
CREATE INDEX patient_mrn_index IF NOT EXISTS
    FOR (p:Patient) ON (p.mrn);

CREATE INDEX patient_tenant_index IF NOT EXISTS
    FOR (p:Patient) ON (p.tenant_id);

CREATE INDEX patient_name_index IF NOT EXISTS
    FOR (p:Patient) ON (p.family_name, p.given_name);

CREATE INDEX patient_dob_index IF NOT EXISTS
    FOR (p:Patient) ON (p.birth_date);

CREATE INDEX patient_risk_index IF NOT EXISTS
    FOR (p:Patient) ON (p.risk_score);

// Disease indexes
CREATE INDEX disease_name_index IF NOT EXISTS
    FOR (d:Disease) ON (d.name);

CREATE INDEX disease_category_index IF NOT EXISTS
    FOR (d:Disease) ON (d.category);

CREATE INDEX disease_icd10_prefix_index IF NOT EXISTS
    FOR (d:Disease) ON (d.icd10_prefix);

// Medication indexes
CREATE INDEX medication_name_index IF NOT EXISTS
    FOR (m:Medication) ON (m.name);

CREATE INDEX medication_class_index IF NOT EXISTS
    FOR (m:Medication) ON (m.drug_class);

CREATE INDEX medication_generic_name_index IF NOT EXISTS
    FOR (m:Medication) ON (m.generic_name);

// Provider indexes
CREATE INDEX provider_name_index IF NOT EXISTS
    FOR (pr:Provider) ON (pr.last_name, pr.first_name);

CREATE INDEX provider_specialty_index IF NOT EXISTS
    FOR (pr:Provider) ON (pr.specialty);

// Organization/Hospital indexes
CREATE INDEX organization_name_index IF NOT EXISTS
    FOR (o:Organization) ON (o.name);

CREATE INDEX organization_state_index IF NOT EXISTS
    FOR (o:Organization) ON (o.state);

CREATE INDEX hospital_name_index IF NOT EXISTS
    FOR (h:Hospital) ON (h.name);

CREATE INDEX hospital_state_index IF NOT EXISTS
    FOR (h:Hospital) ON (h.state);

CREATE INDEX hospital_city_index IF NOT EXISTS
    FOR (h:Hospital) ON (h.city);

// Lab test indexes
CREATE INDEX lab_test_name_index IF NOT EXISTS
    FOR (l:LabTest) ON (l.name);

CREATE INDEX lab_test_category_index IF NOT EXISTS
    FOR (l:LabTest) ON (l.category);

// Guideline indexes
CREATE INDEX guideline_org_index IF NOT EXISTS
    FOR (g:ClinicalGuideline) ON (g.issuing_organization);

CREATE INDEX guideline_year_index IF NOT EXISTS
    FOR (g:ClinicalGuideline) ON (g.publication_year);

// Symptom indexes
CREATE INDEX symptom_name_index IF NOT EXISTS
    FOR (s:Symptom) ON (s.name);

// Gene indexes (pharmacogenomics)
CREATE INDEX gene_symbol_index IF NOT EXISTS
    FOR (g:Gene) ON (g.symbol);

// RiskFactor indexes
CREATE INDEX risk_factor_type_index IF NOT EXISTS
    FOR (r:RiskFactor) ON (r.type);

// ============================================================
// Full-Text Indexes (TEXT indexes for keyword search)
// ============================================================

CREATE TEXT INDEX disease_text_index IF NOT EXISTS
    FOR (d:Disease) ON (d.name);

CREATE TEXT INDEX medication_text_index IF NOT EXISTS
    FOR (m:Medication) ON (m.name, m.generic_name, m.brand_names);

CREATE TEXT INDEX guideline_text_index IF NOT EXISTS
    FOR (g:ClinicalGuideline) ON (g.title, g.summary);

CREATE TEXT INDEX symptom_text_index IF NOT EXISTS
    FOR (s:Symptom) ON (s.name, s.description);

CREATE TEXT INDEX lab_test_text_index IF NOT EXISTS
    FOR (l:LabTest) ON (l.name, l.description);

CREATE TEXT INDEX hospital_text_index IF NOT EXISTS
    FOR (h:Hospital) ON (h.name, h.city, h.state);

// ============================================================
// Relationship property indexes (Neo4j 5.x+)
// ============================================================

CREATE INDEX interacts_with_severity_index IF NOT EXISTS
    FOR ()-[r:INTERACTS_WITH]-() ON (r.severity);

CREATE INDEX increases_risk_weight_index IF NOT EXISTS
    FOR ()-[r:INCREASES_RISK_OF]-() ON (r.weight);

CREATE INDEX contraindicated_severity_index IF NOT EXISTS
    FOR ()-[r:CONTRAINDICATED_IN]-() ON (r.severity);
