-- ============================================================
-- InHealth Chronic Care - Multi-Tenant Schema
-- PostgreSQL database initialization script
-- NOTE: This must be run BEFORE 01_fhir_schema.sql since
-- organizations table is referenced by fhir_patient.
-- ============================================================

-- ============================================================
-- Organizations (Tenants)
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Identification
    name                        VARCHAR(500) NOT NULL,
    short_name                  VARCHAR(100),
    slug                        VARCHAR(100) UNIQUE NOT NULL,
    npi                         VARCHAR(20),
    tax_id_encrypted            BYTEA,
    cms_certification_number    VARCHAR(50),

    -- Organization type
    org_type                    VARCHAR(50) CHECK (org_type IN (
                                    'health_system','hospital','clinic','physician_group',
                                    'aco','mso','independent_practice','demo'
                                )),
    specialty                   VARCHAR(100),

    -- Contact
    address_line1               VARCHAR(500),
    address_line2               VARCHAR(200),
    city                        VARCHAR(100),
    state                       VARCHAR(2),
    zip                         VARCHAR(10),
    country                     VARCHAR(3) DEFAULT 'USA',
    phone                       VARCHAR(30),
    fax                         VARCHAR(30),
    website                     VARCHAR(500),

    -- Geographic
    location                    GEOMETRY(POINT, 4326),

    -- Status
    status                      VARCHAR(20) CHECK (status IN (
                                    'active','inactive','suspended','demo','onboarding'
                                )) DEFAULT 'active',
    onboarded_at                TIMESTAMPTZ,
    contract_start_date         DATE,
    contract_end_date           DATE,

    -- Billing
    billing_email               VARCHAR(255),
    billing_contact             VARCHAR(200),
    plan_tier                   VARCHAR(50) CHECK (plan_tier IN ('starter','professional','enterprise','custom')),
    patient_license_count       INTEGER,
    active_patient_count        INTEGER DEFAULT 0,

    -- HIPAA BAA
    baa_signed_date             DATE,
    baa_signed_by               VARCHAR(200),

    -- Parent org (for health systems with multiple facilities)
    parent_org_id               UUID REFERENCES organizations(id),

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_org_slug ON organizations(slug);
CREATE INDEX idx_org_status ON organizations(status);
CREATE INDEX idx_org_parent ON organizations(parent_org_id);
CREATE INDEX idx_org_location_gist ON organizations USING GIST(location);

-- ============================================================
-- Tenant Configuration
-- ============================================================
CREATE TABLE IF NOT EXISTS tenant_config (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Feature flags
    feature_flags               JSONB NOT NULL DEFAULT '{}',
    -- Expected keys: rpm_enabled, ccm_enabled, agents_enabled, ai_alerts_enabled,
    --                stemi_protocol, stroke_protocol, copd_protocol,
    --                neo4j_enabled, qdrant_enabled, hitl_required

    -- Agent configuration
    agent_config                JSONB NOT NULL DEFAULT '{}',
    -- Expected: enabled_agents, hitl_threshold, orchestration_mode, max_concurrent_pipelines

    -- Clinical thresholds (can be customized per tenant)
    clinical_thresholds         JSONB NOT NULL DEFAULT '{
        "glucose_critical_low": 50,
        "glucose_critical_high": 400,
        "glucose_high": 250,
        "systolic_critical": 180,
        "diastolic_critical": 120,
        "spo2_critical_low": 85,
        "spo2_low": 90,
        "heart_rate_high": 120,
        "heart_rate_low": 40
    }',

    -- Notification configuration
    notification_config         JSONB NOT NULL DEFAULT '{}',

    -- Integration configuration
    ehr_integration             JSONB DEFAULT '{}',
    lab_integration             JSONB DEFAULT '{}',
    pharmacy_integration        JSONB DEFAULT '{}',
    claims_integration          JSONB DEFAULT '{}',
    device_integration          JSONB DEFAULT '{}',

    -- Branding
    branding                    JSONB DEFAULT '{}',
    -- logo_url, primary_color, secondary_color, custom_css

    -- Compliance settings
    hipaa_config                JSONB DEFAULT '{}',
    audit_retention_days        INTEGER DEFAULT 2555,  -- 7 years
    data_retention_days         INTEGER DEFAULT 2555,

    -- Timezone
    timezone                    VARCHAR(100) DEFAULT 'America/Chicago',
    locale                      VARCHAR(20) DEFAULT 'en-US',

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT tenant_config_unique UNIQUE (tenant_id)
);

CREATE INDEX idx_tenant_config_tenant ON tenant_config(tenant_id);

-- ============================================================
-- API Keys
-- ============================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Key identification
    name                        VARCHAR(200) NOT NULL,
    description                 TEXT,
    key_prefix                  VARCHAR(10) NOT NULL,
    key_hash                    VARCHAR(255) NOT NULL UNIQUE,  -- bcrypt hash of full key
    key_last4                   VARCHAR(4) NOT NULL,

    -- Permissions
    scopes                      JSONB NOT NULL DEFAULT '["read"]',
    allowed_ips                 JSONB DEFAULT '[]',
    allowed_origins             JSONB DEFAULT '[]',

    -- Rate limiting
    rate_limit_per_minute       INTEGER DEFAULT 60,
    rate_limit_per_day          INTEGER DEFAULT 10000,

    -- Status
    status                      VARCHAR(20) CHECK (status IN ('active','inactive','revoked','expired')) DEFAULT 'active',
    expires_at                  TIMESTAMPTZ,
    last_used_at                TIMESTAMPTZ,
    use_count                   BIGINT DEFAULT 0,

    -- Created by
    created_by_user_id          UUID,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_status ON api_keys(status);

-- ============================================================
-- Add tenant_id FK to all main tables
-- (These tables were created in 01 and 02 without the FK
--  since organizations didn't exist yet. We add them here.)
-- ============================================================

-- Add FK constraints for tenant isolation
DO $$
BEGIN
    -- fhir_patient - already has FK from 01_fhir_schema.sql when run after this file
    -- If running independently, add FKs here:
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_observation_tenant_fk'
    ) THEN
        ALTER TABLE fhir_observation
            ADD CONSTRAINT fhir_observation_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_condition_tenant_fk'
    ) THEN
        ALTER TABLE fhir_condition
            ADD CONSTRAINT fhir_condition_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_medication_request_tenant_fk'
    ) THEN
        ALTER TABLE fhir_medication_request
            ADD CONSTRAINT fhir_medication_request_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_diagnostic_report_tenant_fk'
    ) THEN
        ALTER TABLE fhir_diagnostic_report
            ADD CONSTRAINT fhir_diagnostic_report_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_appointment_tenant_fk'
    ) THEN
        ALTER TABLE fhir_appointment
            ADD CONSTRAINT fhir_appointment_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_care_plan_tenant_fk'
    ) THEN
        ALTER TABLE fhir_care_plan
            ADD CONSTRAINT fhir_care_plan_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_allergy_intolerance_tenant_fk'
    ) THEN
        ALTER TABLE fhir_allergy_intolerance
            ADD CONSTRAINT fhir_allergy_intolerance_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_encounter_tenant_fk'
    ) THEN
        ALTER TABLE fhir_encounter
            ADD CONSTRAINT fhir_encounter_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_procedure_tenant_fk'
    ) THEN
        ALTER TABLE fhir_procedure
            ADD CONSTRAINT fhir_procedure_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_immunization_tenant_fk'
    ) THEN
        ALTER TABLE fhir_immunization
            ADD CONSTRAINT fhir_immunization_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fhir_document_reference_tenant_fk'
    ) THEN
        ALTER TABLE fhir_document_reference
            ADD CONSTRAINT fhir_document_reference_tenant_fk
            FOREIGN KEY (tenant_id) REFERENCES organizations(id) ON DELETE RESTRICT;
    END IF;
END $$;

-- ============================================================
-- Enable Row Level Security
-- ============================================================

-- Enable RLS on all PHI tables
ALTER TABLE fhir_patient ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_observation ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_condition ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_medication_request ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_diagnostic_report ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_appointment ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_care_plan ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_allergy_intolerance ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_encounter ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_procedure ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_immunization ENABLE ROW LEVEL SECURITY;
ALTER TABLE fhir_document_reference ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_demographics ENABLE ROW LEVEL SECURITY;
ALTER TABLE patient_engagement ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_registration ENABLE ROW LEVEL SECURITY;
ALTER TABLE care_gap ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification ENABLE ROW LEVEL SECURITY;
ALTER TABLE sdoh_assessment ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_score ENABLE ROW LEVEL SECURITY;
ALTER TABLE claim ENABLE ROW LEVEL SECURITY;
ALTER TABLE rpm_episode ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_action_log ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- Row Level Security Policies - Tenant Isolation
-- ============================================================

-- fhir_patient
CREATE POLICY tenant_isolation ON fhir_patient
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_observation
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_condition
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_medication_request
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_diagnostic_report
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_appointment
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_care_plan
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_allergy_intolerance
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_encounter
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_procedure
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_immunization
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON fhir_document_reference
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON patient_demographics
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON patient_engagement
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON device_registration
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON care_gap
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON notification
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON sdoh_assessment
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON risk_score
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON claim
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON rpm_episode
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

CREATE POLICY tenant_isolation ON agent_action_log
    USING (tenant_id IS NULL OR tenant_id = current_setting('app.tenant_id', true)::uuid);

-- ============================================================
-- Superuser bypass policy (for Django superusers / migrations)
-- ============================================================
CREATE POLICY superuser_bypass ON fhir_patient
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_observation
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_condition
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_medication_request
    USING (current_setting('app.bypass_rls', true) = 'true');

CREATE POLICY superuser_bypass ON fhir_diagnostic_report
    USING (current_setting('app.bypass_rls', true) = 'true');

-- ============================================================
-- Helper function to set tenant context
-- ============================================================
CREATE OR REPLACE FUNCTION set_tenant_context(p_tenant_id UUID)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.tenant_id', p_tenant_id::text, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION set_bypass_rls(p_bypass BOOLEAN DEFAULT TRUE)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.bypass_rls', p_bypass::text, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================
-- Update triggers
-- ============================================================
CREATE TRIGGER update_organizations_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenant_config_updated_at
    BEFORE UPDATE ON tenant_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at
    BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- Seed default demo organization
-- ============================================================
INSERT INTO organizations (
    id,
    name,
    short_name,
    slug,
    org_type,
    city,
    state,
    country,
    status,
    plan_tier,
    baa_signed_date
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'InHealth Demo Organization',
    'InHealth Demo',
    'inhealth-demo',
    'health_system',
    'Chicago',
    'IL',
    'USA',
    'demo',
    'enterprise',
    CURRENT_DATE
) ON CONFLICT (slug) DO NOTHING;

INSERT INTO tenant_config (
    tenant_id,
    feature_flags,
    agent_config,
    clinical_thresholds
) VALUES (
    '00000000-0000-0000-0000-000000000001',
    '{
        "rpm_enabled": true,
        "ccm_enabled": true,
        "agents_enabled": true,
        "ai_alerts_enabled": true,
        "stemi_protocol": true,
        "stroke_protocol": true,
        "copd_protocol": true,
        "neo4j_enabled": true,
        "qdrant_enabled": true,
        "hitl_required": false
    }',
    '{
        "enabled_agents": ["triage", "risk_stratification", "care_gap", "medication_review", "notification"],
        "hitl_threshold": 0.7,
        "orchestration_mode": "full_auto",
        "max_concurrent_pipelines": 10
    }',
    '{
        "glucose_critical_low": 50,
        "glucose_critical_high": 400,
        "glucose_high": 250,
        "systolic_critical": 180,
        "diastolic_critical": 120,
        "spo2_critical_low": 85,
        "spo2_low": 90,
        "heart_rate_high": 120,
        "heart_rate_low": 40
    }'
) ON CONFLICT (tenant_id) DO NOTHING;
