-- ============================================================
-- InHealth Chronic Care - HIPAA Audit Schema
-- PostgreSQL database initialization script
-- Implements comprehensive audit logging for HIPAA compliance
-- ============================================================

-- ============================================================
-- Audit Log (HIPAA Access Audit Trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID,

    -- Who
    user_id                     UUID,
    user_name                   VARCHAR(200),
    user_role                   VARCHAR(100),
    agent_name                  VARCHAR(100),  -- if performed by an AI agent
    session_id                  VARCHAR(255),

    -- What
    action                      VARCHAR(50) NOT NULL CHECK (action IN (
                                    'CREATE','READ','UPDATE','DELETE','EXPORT',
                                    'LOGIN','LOGOUT','LOGIN_FAILED','PASSWORD_CHANGE',
                                    'PERMISSION_CHANGE','API_ACCESS','BULK_EXPORT',
                                    'PRINT','FAX','EMAIL','PHI_ACCESS','EMERGENCY_ACCESS'
                                )),
    action_detail               VARCHAR(200),
    resource_type               VARCHAR(100),
    resource_id                 UUID,
    resource_fhir_id            VARCHAR(255),

    -- Patient context
    patient_id                  UUID,
    patient_name_hash           VARCHAR(64),  -- SHA-256 of patient name (for breach correlation without storing PHI)

    -- PHI indicators
    phi_accessed                BOOLEAN DEFAULT FALSE,
    phi_fields_accessed         JSONB DEFAULT '[]',  -- list of PHI field names accessed
    phi_data_categories         JSONB DEFAULT '[]',  -- 'demographics','clinical','financial','behavioral'

    -- Change data
    old_value                   JSONB,
    new_value                   JSONB,
    changed_fields              JSONB DEFAULT '[]',

    -- HTTP context
    ip_address                  INET,
    ip_country                  VARCHAR(2),
    user_agent                  TEXT,
    http_method                 VARCHAR(10),
    request_path                VARCHAR(1000),
    request_id                  VARCHAR(255),
    response_status_code        INTEGER,

    -- Security context
    authentication_method       VARCHAR(50),  -- 'password','mfa','sso','api_key','service_account'
    mfa_used                    BOOLEAN DEFAULT FALSE,
    access_reason               TEXT,
    emergency_access            BOOLEAN DEFAULT FALSE,
    emergency_access_reason     TEXT,

    -- Integrity
    checksum                    VARCHAR(64),  -- SHA-256 of key fields for tamper detection

    -- Timestamp
    timestamp                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Immutability - audit records must not be updated or deleted
    CONSTRAINT audit_log_no_delete CHECK (TRUE)  -- enforced via trigger
);

-- Audit log must not be modified after creation
CREATE OR REPLACE RULE audit_log_no_update AS ON UPDATE TO audit_log DO INSTEAD NOTHING;
CREATE OR REPLACE RULE audit_log_no_delete AS ON DELETE TO audit_log DO INSTEAD NOTHING;

-- Indexes for HIPAA reporting and breach investigation
CREATE INDEX idx_audit_log_user ON audit_log(user_id, timestamp DESC);
CREATE INDEX idx_audit_log_patient ON audit_log(patient_id, timestamp DESC);
CREATE INDEX idx_audit_log_tenant ON audit_log(tenant_id, timestamp DESC);
CREATE INDEX idx_audit_log_action ON audit_log(action, timestamp DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id, timestamp DESC);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_log_ip ON audit_log(ip_address, timestamp DESC);
CREATE INDEX idx_audit_log_phi ON audit_log(phi_accessed, timestamp DESC) WHERE phi_accessed = TRUE;
CREATE INDEX idx_audit_log_emergency ON audit_log(emergency_access, timestamp DESC) WHERE emergency_access = TRUE;

-- Partition audit_log by month for performance (if using TimescaleDB or native partitioning)
-- ALTER TABLE audit_log PARTITION BY RANGE (timestamp);

-- ============================================================
-- Session Log
-- ============================================================
CREATE TABLE IF NOT EXISTS session_log (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID,

    session_id                  VARCHAR(255) NOT NULL UNIQUE,
    user_id                     UUID,
    user_name                   VARCHAR(200),
    user_role                   VARCHAR(100),

    -- Session lifecycle
    login_at                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    logout_at                   TIMESTAMPTZ,
    session_duration_seconds    INTEGER,
    logout_reason               VARCHAR(50),  -- 'user_logout','timeout','forced','revoked'

    -- Authentication
    authentication_method       VARCHAR(50),
    mfa_verified                BOOLEAN DEFAULT FALSE,
    mfa_method                  VARCHAR(50),  -- 'totp','sms','email','hardware_key'
    sso_provider                VARCHAR(100),
    identity_provider_id        VARCHAR(255),

    -- Client
    ip_address                  INET,
    user_agent                  TEXT,
    device_fingerprint          VARCHAR(255),
    device_type                 VARCHAR(50),  -- 'desktop','mobile','tablet'
    os                          VARCHAR(100),
    browser                     VARCHAR(100),

    -- Security events
    login_failed_attempts       INTEGER DEFAULT 0,
    suspicious_activity_flag    BOOLEAN DEFAULT FALSE,
    suspicious_activity_reason  TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_session_log_user ON session_log(user_id, login_at DESC);
CREATE INDEX idx_session_log_tenant ON session_log(tenant_id, login_at DESC);
CREATE INDEX idx_session_log_session ON session_log(session_id);
CREATE INDEX idx_session_log_ip ON session_log(ip_address);
CREATE INDEX idx_session_log_suspicious ON session_log(suspicious_activity_flag) WHERE suspicious_activity_flag = TRUE;

-- ============================================================
-- Data Access Log (Granular PHI Access Tracking)
-- ============================================================
CREATE TABLE IF NOT EXISTS data_access_log (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_log_id                UUID REFERENCES audit_log(id),
    tenant_id                   UUID,

    -- Who accessed
    user_id                     UUID,
    user_name                   VARCHAR(200),
    user_role                   VARCHAR(100),
    agent_name                  VARCHAR(100),
    session_id                  VARCHAR(255),

    -- What was accessed
    patient_id                  UUID,
    data_category               VARCHAR(100) NOT NULL,  -- 'demographics','vitals','medications','labs','diagnoses','notes'
    table_name                  VARCHAR(100),
    record_ids                  JSONB DEFAULT '[]',
    fields_accessed             JSONB DEFAULT '[]',
    record_count                INTEGER DEFAULT 1,

    -- Access method
    access_method               VARCHAR(50),  -- 'ui_view','api_query','report','bulk_export','agent_read'
    access_reason               VARCHAR(200),
    purpose_of_use              VARCHAR(100),  -- HIPAA Treatment/Payment/Operations/Research

    -- Result
    rows_returned               INTEGER DEFAULT 0,

    -- Context
    ip_address                  INET,
    request_id                  VARCHAR(255),

    timestamp                   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_data_access_patient ON data_access_log(patient_id, timestamp DESC);
CREATE INDEX idx_data_access_user ON data_access_log(user_id, timestamp DESC);
CREATE INDEX idx_data_access_tenant ON data_access_log(tenant_id, timestamp DESC);
CREATE INDEX idx_data_access_timestamp ON data_access_log(timestamp DESC);
CREATE INDEX idx_data_access_category ON data_access_log(data_category);

-- ============================================================
-- Audit Trigger Function
-- ============================================================
CREATE OR REPLACE FUNCTION log_data_access()
RETURNS TRIGGER AS $$
DECLARE
    v_action            VARCHAR(50);
    v_old_value         JSONB;
    v_new_value         JSONB;
    v_user_id           UUID;
    v_user_name         VARCHAR(200);
    v_user_role         VARCHAR(100);
    v_agent_name        VARCHAR(100);
    v_session_id        VARCHAR(255);
    v_tenant_id         UUID;
    v_patient_id        UUID;
    v_phi_fields        JSONB;
    v_changed_fields    JSONB;
BEGIN
    -- Determine action
    IF TG_OP = 'INSERT' THEN
        v_action := 'CREATE';
        v_new_value := to_jsonb(NEW);
        v_old_value := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        v_action := 'UPDATE';
        v_new_value := to_jsonb(NEW);
        v_old_value := to_jsonb(OLD);
        -- Compute changed fields
        SELECT jsonb_agg(key)
        INTO v_changed_fields
        FROM (
            SELECT key
            FROM jsonb_each(v_new_value) AS n(key, value)
            WHERE v_new_value->key IS DISTINCT FROM v_old_value->key
        ) changed;
    ELSIF TG_OP = 'DELETE' THEN
        v_action := 'DELETE';
        v_old_value := to_jsonb(OLD);
        v_new_value := NULL;
    END IF;

    -- Get session context (set by application)
    v_user_id := NULLIF(current_setting('app.user_id', true), '')::UUID;
    v_user_name := current_setting('app.user_name', true);
    v_user_role := current_setting('app.user_role', true);
    v_agent_name := current_setting('app.agent_name', true);
    v_session_id := current_setting('app.session_id', true);

    -- Extract tenant_id and patient_id from the row
    IF TG_OP = 'DELETE' THEN
        v_tenant_id := (v_old_value->>'tenant_id')::UUID;
        v_patient_id := CASE
            WHEN TG_TABLE_NAME = 'fhir_patient' THEN (v_old_value->>'id')::UUID
            WHEN v_old_value ? 'patient_id' THEN (v_old_value->>'patient_id')::UUID
            WHEN v_old_value ? 'subject_patient_id' THEN (v_old_value->>'subject_patient_id')::UUID
            ELSE NULL
        END;
    ELSE
        v_tenant_id := (v_new_value->>'tenant_id')::UUID;
        v_patient_id := CASE
            WHEN TG_TABLE_NAME = 'fhir_patient' THEN (v_new_value->>'id')::UUID
            WHEN v_new_value ? 'patient_id' THEN (v_new_value->>'patient_id')::UUID
            WHEN v_new_value ? 'subject_patient_id' THEN (v_new_value->>'subject_patient_id')::UUID
            ELSE NULL
        END;
    END IF;

    -- Determine PHI fields accessed based on table
    v_phi_fields := CASE TG_TABLE_NAME
        WHEN 'fhir_patient' THEN '["name","birth_date","gender","telecom","address","identifier","mrn"]'::JSONB
        WHEN 'patient_demographics' THEN '["ssn_encrypted","ssn_last4","race_code","ethnicity_code"]'::JSONB
        WHEN 'fhir_observation' THEN '["value_quantity","value_numeric","value_string","code"]'::JSONB
        WHEN 'fhir_condition' THEN '["code","icd10_code","onset_datetime"]'::JSONB
        WHEN 'fhir_medication_request' THEN '["drug_name","rxnorm_code","dosage_instruction"]'::JSONB
        ELSE '[]'::JSONB
    END;

    -- Remove sensitive data from logged values (SSN etc.)
    IF TG_TABLE_NAME = 'patient_demographics' THEN
        v_new_value := v_new_value - 'ssn_encrypted';
        v_old_value := v_old_value - 'ssn_encrypted';
    END IF;

    -- Insert audit record
    INSERT INTO audit_log (
        tenant_id,
        user_id,
        user_name,
        user_role,
        agent_name,
        session_id,
        action,
        resource_type,
        resource_id,
        patient_id,
        phi_accessed,
        phi_fields_accessed,
        old_value,
        new_value,
        changed_fields,
        ip_address,
        request_id,
        timestamp
    ) VALUES (
        v_tenant_id,
        v_user_id,
        v_user_name,
        v_user_role,
        v_agent_name,
        v_session_id,
        v_action,
        TG_TABLE_NAME,
        CASE WHEN TG_OP = 'DELETE' THEN (v_old_value->>'id')::UUID
             ELSE (v_new_value->>'id')::UUID END,
        v_patient_id,
        jsonb_array_length(v_phi_fields) > 0,
        v_phi_fields,
        v_old_value,
        v_new_value,
        COALESCE(v_changed_fields, '[]'::JSONB),
        NULLIF(current_setting('app.ip_address', true), '')::INET,
        current_setting('app.request_id', true),
        NOW()
    );

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- Attach Audit Triggers to All PHI Tables
-- ============================================================

-- fhir_patient
CREATE TRIGGER audit_fhir_patient
    AFTER INSERT OR UPDATE OR DELETE ON fhir_patient
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- fhir_observation
CREATE TRIGGER audit_fhir_observation
    AFTER INSERT OR UPDATE OR DELETE ON fhir_observation
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- fhir_condition
CREATE TRIGGER audit_fhir_condition
    AFTER INSERT OR UPDATE OR DELETE ON fhir_condition
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- fhir_medication_request
CREATE TRIGGER audit_fhir_medication_request
    AFTER INSERT OR UPDATE OR DELETE ON fhir_medication_request
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- fhir_diagnostic_report
CREATE TRIGGER audit_fhir_diagnostic_report
    AFTER INSERT OR UPDATE OR DELETE ON fhir_diagnostic_report
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- fhir_encounter
CREATE TRIGGER audit_fhir_encounter
    AFTER INSERT OR UPDATE OR DELETE ON fhir_encounter
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- fhir_procedure
CREATE TRIGGER audit_fhir_procedure
    AFTER INSERT OR UPDATE OR DELETE ON fhir_procedure
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- fhir_allergy_intolerance
CREATE TRIGGER audit_fhir_allergy_intolerance
    AFTER INSERT OR UPDATE OR DELETE ON fhir_allergy_intolerance
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- patient_demographics (highest sensitivity - contains SSN)
CREATE TRIGGER audit_patient_demographics
    AFTER INSERT OR UPDATE OR DELETE ON patient_demographics
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- fhir_document_reference
CREATE TRIGGER audit_fhir_document_reference
    AFTER INSERT OR UPDATE OR DELETE ON fhir_document_reference
    FOR EACH ROW EXECUTE FUNCTION log_data_access();

-- ============================================================
-- HIPAA Audit Report Helper Views
-- ============================================================

-- View: PHI access by user in past 30 days
CREATE OR REPLACE VIEW v_phi_access_by_user AS
SELECT
    user_id,
    user_name,
    user_role,
    tenant_id,
    COUNT(*) as total_accesses,
    COUNT(DISTINCT patient_id) as unique_patients_accessed,
    COUNT(*) FILTER (WHERE action = 'READ') as reads,
    COUNT(*) FILTER (WHERE action = 'UPDATE') as updates,
    COUNT(*) FILTER (WHERE action = 'DELETE') as deletes,
    COUNT(*) FILTER (WHERE action = 'EXPORT') as exports,
    COUNT(*) FILTER (WHERE emergency_access = TRUE) as emergency_accesses,
    MIN(timestamp) as first_access,
    MAX(timestamp) as last_access
FROM audit_log
WHERE phi_accessed = TRUE
  AND timestamp >= NOW() - INTERVAL '30 days'
GROUP BY user_id, user_name, user_role, tenant_id;

-- View: Suspicious access patterns (high volume access)
CREATE OR REPLACE VIEW v_suspicious_access AS
SELECT
    user_id,
    user_name,
    ip_address,
    tenant_id,
    COUNT(DISTINCT patient_id) as patients_accessed_count,
    COUNT(*) as total_accesses,
    MIN(timestamp) as window_start,
    MAX(timestamp) as window_end
FROM audit_log
WHERE timestamp >= NOW() - INTERVAL '1 hour'
  AND phi_accessed = TRUE
GROUP BY user_id, user_name, ip_address, tenant_id
HAVING COUNT(DISTINCT patient_id) > 50  -- accessing >50 patients in 1 hour is suspicious
ORDER BY patients_accessed_count DESC;

-- View: Emergency access log
CREATE OR REPLACE VIEW v_emergency_access_log AS
SELECT
    al.id,
    al.tenant_id,
    al.user_id,
    al.user_name,
    al.user_role,
    al.patient_id,
    al.action,
    al.emergency_access_reason,
    al.ip_address,
    al.timestamp
FROM audit_log al
WHERE al.emergency_access = TRUE
ORDER BY al.timestamp DESC;
