-- ============================================================
-- InHealth Chronic Care - Performance Indexes
-- PostgreSQL database optimization script
-- ============================================================

-- ============================================================
-- GiST Indexes for PostGIS Location Columns
-- ============================================================

-- Organizations geographic location index
CREATE INDEX IF NOT EXISTS idx_organizations_location_gist
    ON organizations USING GIST(location);

-- ============================================================
-- GIN Indexes for JSONB Columns
-- ============================================================

-- FHIR raw_fhir documents - for jsonb containment queries
CREATE INDEX IF NOT EXISTS idx_fhir_patient_raw_fhir_gin_ops
    ON fhir_patient USING GIN(raw_fhir jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_fhir_observation_raw_fhir_gin_ops
    ON fhir_observation USING GIN(raw_fhir jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_fhir_condition_raw_fhir_gin_ops
    ON fhir_condition USING GIN(raw_fhir jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_fhir_medication_request_raw_fhir_gin_ops
    ON fhir_medication_request USING GIN(raw_fhir jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_fhir_diagnostic_report_raw_fhir_gin_ops
    ON fhir_diagnostic_report USING GIN(raw_fhir jsonb_path_ops);

-- Patient identifier arrays (MRN, SSN last4 lookup)
CREATE INDEX IF NOT EXISTS idx_fhir_patient_identifier_gin_ops
    ON fhir_patient USING GIN(identifier jsonb_path_ops);

-- Observation component (for multi-value observations like BP)
CREATE INDEX IF NOT EXISTS idx_fhir_observation_component_gin
    ON fhir_observation USING GIN(component jsonb_path_ops);

-- Medication dosage instructions
CREATE INDEX IF NOT EXISTS idx_fhir_medrx_dosage_gin
    ON fhir_medication_request USING GIN(dosage_instruction jsonb_path_ops);

-- Care plan activity (finding open activities)
CREATE INDEX IF NOT EXISTS idx_fhir_care_plan_activity_gin
    ON fhir_care_plan USING GIN(activity jsonb_path_ops);

-- Agent action log - input/output data search
CREATE INDEX IF NOT EXISTS idx_agent_log_input_gin_ops
    ON agent_action_log USING GIN(input_data jsonb_path_ops);

CREATE INDEX IF NOT EXISTS idx_agent_log_output_gin_ops
    ON agent_action_log USING GIN(output_data jsonb_path_ops);

-- Risk score feature importance search
CREATE INDEX IF NOT EXISTS idx_risk_score_feature_gin
    ON risk_score USING GIN(feature_importance jsonb_path_ops);

-- Tenant config feature flags search
CREATE INDEX IF NOT EXISTS idx_tenant_config_flags_gin
    ON tenant_config USING GIN(feature_flags jsonb_path_ops);

-- Notification template variables
CREATE INDEX IF NOT EXISTS idx_notif_template_vars_gin
    ON notification_template USING GIN(variables jsonb_path_ops);

-- Care gap responses
CREATE INDEX IF NOT EXISTS idx_sdoh_responses_gin
    ON sdoh_assessment USING GIN(responses jsonb_path_ops);

-- ============================================================
-- Trigram Indexes for Text Search (pg_trgm)
-- ============================================================

-- Patient name search (fuzzy)
CREATE INDEX IF NOT EXISTS idx_fhir_patient_family_trgm
    ON fhir_patient USING GIN(family_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_fhir_patient_given_trgm
    ON fhir_patient USING GIN(given_name gin_trgm_ops);

-- Drug name search
CREATE INDEX IF NOT EXISTS idx_fhir_medrx_drug_name_trgm
    ON fhir_medication_request USING GIN(drug_name gin_trgm_ops);

-- Condition code display text search
CREATE INDEX IF NOT EXISTS idx_fhir_condition_display_trgm
    ON fhir_condition USING GIN(code_display gin_trgm_ops);

-- Observation code display text search
CREATE INDEX IF NOT EXISTS idx_fhir_observation_display_trgm
    ON fhir_observation USING GIN(code_display gin_trgm_ops);

-- ============================================================
-- Partial Indexes for Common Filtered Queries
-- ============================================================

-- Active patients only (soft delete pattern)
CREATE INDEX IF NOT EXISTS idx_fhir_patient_active
    ON fhir_patient(tenant_id, family_name, given_name)
    WHERE deleted_at IS NULL AND deceased_boolean = FALSE;

-- Current (final/active) observations
CREATE INDEX IF NOT EXISTS idx_fhir_obs_final
    ON fhir_observation(subject_patient_id, code_value, effective_datetime DESC)
    WHERE status = 'final';

-- Active conditions (not resolved)
CREATE INDEX IF NOT EXISTS idx_fhir_cond_active
    ON fhir_condition(subject_patient_id, icd10_code)
    WHERE abatement_datetime IS NULL;

-- Active medications
CREATE INDEX IF NOT EXISTS idx_fhir_medrx_active
    ON fhir_medication_request(subject_patient_id, rxnorm_code, authored_on DESC)
    WHERE status = 'active';

-- Upcoming appointments
CREATE INDEX IF NOT EXISTS idx_fhir_appt_upcoming
    ON fhir_appointment(subject_patient_id, start)
    WHERE status IN ('booked', 'arrived') AND start > NOW();

-- Open care gaps by priority
CREATE INDEX IF NOT EXISTS idx_care_gap_open_high
    ON care_gap(patient_id, due_date)
    WHERE status = 'open' AND priority = 'high';

CREATE INDEX IF NOT EXISTS idx_care_gap_open_by_type
    ON care_gap(tenant_id, gap_type, status)
    WHERE status IN ('open', 'in_progress');

-- Recent risk scores (last 90 days)
CREATE INDEX IF NOT EXISTS idx_risk_score_recent
    ON risk_score(patient_id, score_type, score_value DESC)
    WHERE score_date > CURRENT_DATE - INTERVAL '90 days';

-- High risk patients
CREATE INDEX IF NOT EXISTS idx_risk_score_high_risk
    ON risk_score(tenant_id, patient_id, score_date DESC)
    WHERE risk_level IN ('high', 'critical');

-- Pending notifications
CREATE INDEX IF NOT EXISTS idx_notification_pending
    ON notification(scheduled_at, channel)
    WHERE status IN ('pending', 'queued') AND scheduled_at <= NOW() + INTERVAL '5 minutes';

-- Failed notifications for retry
CREATE INDEX IF NOT EXISTS idx_notification_retry
    ON notification(next_retry_at)
    WHERE status = 'failed' AND retry_count < max_retries;

-- Active devices for RPM
CREATE INDEX IF NOT EXISTS idx_device_active_rpm
    ON device_registration(patient_id, device_type, last_sync_at DESC)
    WHERE status = 'active';

-- Active RPM episodes
CREATE INDEX IF NOT EXISTS idx_rpm_active
    ON rpm_episode(tenant_id, patient_id)
    WHERE status = 'active';

-- RPM billing - threshold not yet met
CREATE INDEX IF NOT EXISTS idx_rpm_billing_pending
    ON rpm_episode(tenant_id, billing_month)
    WHERE status = 'active' AND threshold_99457_met = FALSE;

-- Agent action log - failed executions
CREATE INDEX IF NOT EXISTS idx_agent_log_failed
    ON agent_action_log(agent_name, started_at DESC)
    WHERE status = 'failed';

-- Agent action log - HITL pending
CREATE INDEX IF NOT EXISTS idx_agent_log_hitl_pending
    ON agent_action_log(tenant_id, started_at)
    WHERE hitl_required = TRUE AND hitl_decision IS NULL;

-- Audit log - PHI access for compliance reporting
CREATE INDEX IF NOT EXISTS idx_audit_phi_recent
    ON audit_log(tenant_id, user_id, timestamp DESC)
    WHERE phi_accessed = TRUE AND timestamp > NOW() - INTERVAL '1 year';

-- Sessions currently active
CREATE INDEX IF NOT EXISTS idx_session_active
    ON session_log(user_id, last_activity_at DESC)
    WHERE logout_at IS NULL;

-- ============================================================
-- pgvector Cosine Similarity Indexes (IVFFlat)
-- For approximate nearest neighbor search on embeddings
-- ============================================================

-- Patient embedding index (for similar patient lookup)
CREATE INDEX IF NOT EXISTS idx_fhir_patient_embedding_ivfflat
    ON fhir_patient USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- Diagnostic report embedding index
CREATE INDEX IF NOT EXISTS idx_fhir_diagnostic_report_embedding_ivfflat
    ON fhir_diagnostic_report USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- Care plan embedding index
CREATE INDEX IF NOT EXISTS idx_fhir_care_plan_embedding_ivfflat
    ON fhir_care_plan USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- Document reference embedding index
CREATE INDEX IF NOT EXISTS idx_fhir_document_reference_embedding_ivfflat
    ON fhir_document_reference USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100)
    WHERE embedding IS NOT NULL;

-- ============================================================
-- pgvector HNSW Indexes (faster queries, more memory)
-- Use for collections that need sub-millisecond query times
-- ============================================================

-- Patient HNSW index for fast patient-to-patient similarity
CREATE INDEX IF NOT EXISTS idx_fhir_patient_embedding_hnsw
    ON fhir_patient USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embedding IS NOT NULL;

-- ============================================================
-- Composite Indexes for Common JOIN patterns
-- ============================================================

-- Patient timeline queries (patient_id + time range)
CREATE INDEX IF NOT EXISTS idx_fhir_obs_patient_timeline
    ON fhir_observation(subject_patient_id, effective_datetime DESC, code_value)
    INCLUDE (value_numeric, value_unit, status);

-- Condition burden (ICD-10 population queries)
CREATE INDEX IF NOT EXISTS idx_fhir_cond_tenant_icd10
    ON fhir_condition(tenant_id, icd10_code, onset_datetime DESC)
    WHERE abatement_datetime IS NULL;

-- Care gap reporting
CREATE INDEX IF NOT EXISTS idx_care_gap_reporting
    ON care_gap(tenant_id, measure_id, status, reporting_period_start, reporting_period_end);

-- Clinical KPI reporting
CREATE INDEX IF NOT EXISTS idx_kpi_reporting
    ON clinical_kpi(tenant_id, kpi_name, reporting_period_start DESC, reporting_period_end DESC);

-- Claim adjudication
CREATE INDEX IF NOT EXISTS idx_claim_adjudication
    ON claim(tenant_id, claim_status, service_date_start DESC)
    INCLUDE (billed_amount, paid_amount);

-- ============================================================
-- Statistics Update
-- Force fresh statistics for query planner optimization
-- ============================================================
ANALYZE fhir_patient;
ANALYZE fhir_observation;
ANALYZE fhir_condition;
ANALYZE fhir_medication_request;
ANALYZE fhir_encounter;
ANALYZE fhir_care_plan;
ANALYZE care_gap;
ANALYZE risk_score;
ANALYZE notification;
ANALYZE agent_action_log;
