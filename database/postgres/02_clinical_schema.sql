-- ============================================================
-- InHealth Chronic Care - Extended Clinical Schema
-- PostgreSQL database initialization script
-- ============================================================

-- ============================================================
-- Patient Demographics (with PHI encryption)
-- ============================================================
CREATE TABLE IF NOT EXISTS patient_demographics (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id                  UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    tenant_id                   UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,

    -- Encrypted SSN using pgcrypto
    ssn_encrypted               BYTEA,  -- pgp_sym_encrypt(ssn, current_setting('app.encryption_key'))
    ssn_last4                   VARCHAR(4),

    -- Race & Ethnicity (USCDI)
    race_code                   VARCHAR(20),
    race_display                VARCHAR(100),
    ethnicity_code              VARCHAR(20),
    ethnicity_display           VARCHAR(100),
    preferred_language          VARCHAR(50),
    interpreter_needed          BOOLEAN DEFAULT FALSE,

    -- Social history
    smoking_status              VARCHAR(50),
    alcohol_use                 VARCHAR(50),
    substance_use               VARCHAR(50),
    exercise_frequency          VARCHAR(50),
    diet_type                   VARCHAR(100),
    occupation                  VARCHAR(200),
    employer                    VARCHAR(200),
    highest_education           VARCHAR(100),

    -- Insurance
    primary_insurance_name      VARCHAR(200),
    primary_insurance_id        VARCHAR(100),
    primary_insurance_group     VARCHAR(100),
    secondary_insurance_name    VARCHAR(200),
    secondary_insurance_id      VARCHAR(100),
    medicare_id                 VARCHAR(50),
    medicaid_id                 VARCHAR(50),

    -- Emergency Contact
    emergency_contact_name      VARCHAR(200),
    emergency_contact_phone     VARCHAR(30),
    emergency_contact_relation  VARCHAR(100),

    -- Primary Care
    pcp_name                    VARCHAR(200),
    pcp_npi                     VARCHAR(20),
    pcp_practice                VARCHAR(200),
    pcp_phone                   VARCHAR(30),
    pcp_fax                     VARCHAR(30),
    care_coordinator_id         UUID,

    -- Portal
    portal_enrolled             BOOLEAN DEFAULT FALSE,
    portal_enrolled_at          TIMESTAMPTZ,
    last_portal_login           TIMESTAMPTZ,
    mobile_app_enrolled         BOOLEAN DEFAULT FALSE,
    mobile_app_enrolled_at      TIMESTAMPTZ,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT patient_demographics_unique UNIQUE (patient_id)
);

CREATE INDEX idx_demographics_patient ON patient_demographics(patient_id);
CREATE INDEX idx_demographics_tenant ON patient_demographics(tenant_id);
CREATE INDEX idx_demographics_pcp_npi ON patient_demographics(pcp_npi);

-- ============================================================
-- Patient Engagement
-- ============================================================
CREATE TABLE IF NOT EXISTS patient_engagement (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id                  UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    tenant_id                   UUID NOT NULL,

    -- Engagement scoring
    engagement_score            DECIMAL(5,2) DEFAULT 0,
    last_engagement_at          TIMESTAMPTZ,
    engagement_trend            VARCHAR(20) CHECK (engagement_trend IN ('improving','stable','declining','unknown')),

    -- Contact preferences
    preferred_contact_method    VARCHAR(50) CHECK (preferred_contact_method IN (
                                    'phone','sms','email','app_push','portal_message','mail'
                                )),
    best_contact_time           VARCHAR(100),
    do_not_contact_before       TIME,
    do_not_contact_after        TIME,
    do_not_contact_days         JSONB DEFAULT '[]',

    -- Communication counts
    total_outreach_attempts     INTEGER DEFAULT 0,
    successful_contacts         INTEGER DEFAULT 0,
    no_show_count               INTEGER DEFAULT 0,
    appointment_adherence_rate  DECIMAL(5,2),
    medication_refill_adherence DECIMAL(5,2),

    -- Patient activation
    patient_activation_score    DECIMAL(5,2),  -- PAM score 0-100
    health_literacy_level       VARCHAR(20) CHECK (health_literacy_level IN ('low','marginal','adequate','proficient')),
    self_management_readiness   VARCHAR(20),

    -- Goals
    patient_goals               JSONB DEFAULT '[]',
    care_team_notes             TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_engagement_patient ON patient_engagement(patient_id);
CREATE INDEX idx_engagement_tenant ON patient_engagement(tenant_id);
CREATE INDEX idx_engagement_score ON patient_engagement(engagement_score DESC);

-- ============================================================
-- Device Registration (RPM Devices)
-- ============================================================
CREATE TABLE IF NOT EXISTS device_registration (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id                  UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    tenant_id                   UUID NOT NULL,

    device_id                   VARCHAR(255) NOT NULL UNIQUE,
    device_type                 VARCHAR(100) NOT NULL,  -- 'glucometer','bp_cuff','pulse_oximeter','scale','cgm'
    device_manufacturer         VARCHAR(200),
    device_model                VARCHAR(200),
    device_serial               VARCHAR(200),
    firmware_version            VARCHAR(50),

    -- Status
    status                      VARCHAR(20) CHECK (status IN ('active','inactive','lost','replaced','returned')) DEFAULT 'active',
    assigned_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deactivated_at              TIMESTAMPTZ,

    -- Connectivity
    connection_type             VARCHAR(50),  -- 'bluetooth','wifi','cellular','manual'
    last_sync_at                TIMESTAMPTZ,
    last_reading_at             TIMESTAMPTZ,
    sync_frequency_minutes      INTEGER DEFAULT 60,
    battery_level               INTEGER,

    -- Thresholds
    alert_thresholds            JSONB DEFAULT '{}',
    calibration_due_date        DATE,

    -- Integration
    vendor_device_id            VARCHAR(255),
    vendor_patient_id           VARCHAR(255),
    integration_config          JSONB DEFAULT '{}',

    notes                       TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_device_patient ON device_registration(patient_id);
CREATE INDEX idx_device_tenant ON device_registration(tenant_id);
CREATE INDEX idx_device_type ON device_registration(device_type);
CREATE INDEX idx_device_status ON device_registration(status);
CREATE INDEX idx_device_last_sync ON device_registration(last_sync_at);

-- ============================================================
-- Care Gap
-- ============================================================
CREATE TABLE IF NOT EXISTS care_gap (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id                  UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    tenant_id                   UUID NOT NULL,

    -- Gap definition
    gap_type                    VARCHAR(100) NOT NULL,  -- 'HbA1c','BP_Control','Mammogram','Colonoscopy', etc.
    gap_category                VARCHAR(50),  -- 'preventive','chronic','medication','referral'
    gap_code                    VARCHAR(100),  -- HEDIS measure code
    gap_description             TEXT,

    -- Status
    status                      VARCHAR(20) NOT NULL CHECK (status IN (
                                    'open','in_progress','closed','excluded','not_applicable'
                                )) DEFAULT 'open',
    priority                    VARCHAR(10) CHECK (priority IN ('high','medium','low')) DEFAULT 'medium',

    -- Dates
    identified_date             DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date                    DATE,
    closed_date                 DATE,
    last_service_date           DATE,
    next_due_date               DATE,

    -- Closure details
    closure_reason              VARCHAR(200),
    closed_by_user_id           UUID,
    linked_encounter_id         UUID,
    linked_order_id             UUID,

    -- HEDIS/Quality measure context
    measure_id                  VARCHAR(50),
    measure_period_start        DATE,
    measure_period_end          DATE,
    numerator_met               BOOLEAN DEFAULT FALSE,
    exclusion_met               BOOLEAN DEFAULT FALSE,
    exclusion_reason            VARCHAR(200),

    notes                       TEXT,
    agent_identified            BOOLEAN DEFAULT FALSE,
    agent_action_log_id         UUID REFERENCES agent_action_log(id),

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_care_gap_patient ON care_gap(patient_id);
CREATE INDEX idx_care_gap_tenant ON care_gap(tenant_id);
CREATE INDEX idx_care_gap_status ON care_gap(status);
CREATE INDEX idx_care_gap_type ON care_gap(gap_type);
CREATE INDEX idx_care_gap_due_date ON care_gap(due_date);

-- ============================================================
-- Smart Order Set
-- ============================================================
CREATE TABLE IF NOT EXISTS smart_order_set (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL,

    name                        VARCHAR(500) NOT NULL,
    description                 TEXT,
    order_set_type              VARCHAR(100),  -- 'admission','discharge','procedure','disease_management'
    specialty                   VARCHAR(100),
    disease_context             JSONB DEFAULT '[]',  -- ICD-10 codes this applies to

    -- Orders contained
    orders                      JSONB NOT NULL DEFAULT '[]',  -- array of order objects

    -- Evidence / guidelines
    guideline_references        JSONB DEFAULT '[]',
    evidence_level              VARCHAR(10),  -- 'A','B','C','D'
    last_reviewed_date          DATE,
    reviewed_by                 VARCHAR(200),

    -- Status
    status                      VARCHAR(20) CHECK (status IN ('active','draft','retired')) DEFAULT 'active',
    version                     VARCHAR(20) DEFAULT '1.0',

    -- AI enhancement
    ai_recommended              BOOLEAN DEFAULT FALSE,
    ai_confidence_score         DECIMAL(5,2),

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_set_tenant ON smart_order_set(tenant_id);
CREATE INDEX idx_order_set_type ON smart_order_set(order_set_type);
CREATE INDEX idx_order_set_status ON smart_order_set(status);

-- ============================================================
-- Notification
-- ============================================================
CREATE TABLE IF NOT EXISTS notification (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL,
    patient_id                  UUID REFERENCES fhir_patient(id) ON DELETE SET NULL,

    -- Notification classification
    notification_type           VARCHAR(100) NOT NULL,  -- 'appointment_reminder','lab_result','medication_alert', etc.
    channel                     VARCHAR(50) NOT NULL CHECK (channel IN (
                                    'sms','email','app_push','phone','portal_message','fax','mail'
                                )),
    priority                    VARCHAR(10) CHECK (priority IN ('urgent','high','normal','low')) DEFAULT 'normal',

    -- Content
    subject                     VARCHAR(500),
    body_text                   TEXT,
    body_html                   TEXT,
    template_id                 UUID,
    template_variables          JSONB DEFAULT '{}',

    -- Recipient
    recipient_name              VARCHAR(200),
    recipient_address           VARCHAR(500),  -- phone/email/device token
    recipient_type              VARCHAR(50),  -- 'patient','caregiver','provider','care_coordinator'

    -- Delivery status
    status                      VARCHAR(20) NOT NULL CHECK (status IN (
                                    'pending','queued','sent','delivered','failed',
                                    'bounced','opted_out','cancelled'
                                )) DEFAULT 'pending',
    scheduled_at                TIMESTAMPTZ,
    sent_at                     TIMESTAMPTZ,
    delivered_at                TIMESTAMPTZ,
    opened_at                   TIMESTAMPTZ,
    failed_at                   TIMESTAMPTZ,
    failure_reason              TEXT,
    external_message_id         VARCHAR(500),
    retry_count                 INTEGER DEFAULT 0,
    max_retries                 INTEGER DEFAULT 3,
    next_retry_at               TIMESTAMPTZ,

    -- Context
    related_resource_type       VARCHAR(50),
    related_resource_id         UUID,
    triggered_by_agent          VARCHAR(100),
    agent_action_log_id         UUID REFERENCES agent_action_log(id),

    -- Patient response tracking
    patient_responded           BOOLEAN DEFAULT FALSE,
    patient_response            TEXT,
    patient_responded_at        TIMESTAMPTZ,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notification_patient ON notification(patient_id);
CREATE INDEX idx_notification_tenant ON notification(tenant_id);
CREATE INDEX idx_notification_status ON notification(status);
CREATE INDEX idx_notification_channel ON notification(channel);
CREATE INDEX idx_notification_scheduled ON notification(scheduled_at);
CREATE INDEX idx_notification_type ON notification(notification_type);

-- ============================================================
-- Notification Template
-- ============================================================
CREATE TABLE IF NOT EXISTS notification_template (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID,  -- NULL = system-wide template

    name                        VARCHAR(200) NOT NULL,
    notification_type           VARCHAR(100) NOT NULL,
    channel                     VARCHAR(50) NOT NULL,
    language                    VARCHAR(10) DEFAULT 'en',

    subject_template            VARCHAR(500),
    body_text_template          TEXT NOT NULL,
    body_html_template          TEXT,
    variables                   JSONB DEFAULT '[]',  -- list of expected template variables

    -- Metadata
    version                     INTEGER DEFAULT 1,
    status                      VARCHAR(20) CHECK (status IN ('active','draft','retired')) DEFAULT 'active',
    last_reviewed_at            TIMESTAMPTZ,
    reviewed_by                 VARCHAR(200),

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_template_name_channel_lang UNIQUE (tenant_id, name, channel, language)
);

CREATE INDEX idx_notif_template_tenant ON notification_template(tenant_id);
CREATE INDEX idx_notif_template_type ON notification_template(notification_type);

-- ============================================================
-- SDOH Assessment
-- ============================================================
CREATE TABLE IF NOT EXISTS sdoh_assessment (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id                  UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    tenant_id                   UUID NOT NULL,
    encounter_id                UUID REFERENCES fhir_encounter(id) ON DELETE SET NULL,

    -- Assessment metadata
    assessment_date             DATE NOT NULL DEFAULT CURRENT_DATE,
    assessment_tool             VARCHAR(100),  -- 'AHC_HRSN','PRAPARE','Hunger_Vital_Sign'
    administered_by             UUID,
    next_assessment_due         DATE,

    -- Food & Housing (SDOH domains)
    food_insecurity             BOOLEAN,
    housing_instability         BOOLEAN,
    homelessness                BOOLEAN,
    transportation_need         BOOLEAN,
    utility_insecurity          BOOLEAN,
    interpersonal_violence      BOOLEAN,
    social_isolation            BOOLEAN,
    financial_strain            BOOLEAN,
    education_barrier           BOOLEAN,
    employment_barrier          BOOLEAN,
    childcare_need              BOOLEAN,
    elder_care_need             BOOLEAN,
    health_literacy_barrier     BOOLEAN,

    -- Scores
    total_score                 INTEGER,
    risk_level                  VARCHAR(20) CHECK (risk_level IN ('low','moderate','high','critical')),

    -- Responses (full survey)
    responses                   JSONB DEFAULT '{}',

    -- Actions taken
    referrals_made              JSONB DEFAULT '[]',
    resources_provided          JSONB DEFAULT '[]',
    follow_up_plan              TEXT,
    agent_assessed              BOOLEAN DEFAULT FALSE,

    notes                       TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sdoh_patient ON sdoh_assessment(patient_id);
CREATE INDEX idx_sdoh_tenant ON sdoh_assessment(tenant_id);
CREATE INDEX idx_sdoh_date ON sdoh_assessment(assessment_date DESC);
CREATE INDEX idx_sdoh_risk ON sdoh_assessment(risk_level);

-- ============================================================
-- Risk Score
-- ============================================================
CREATE TABLE IF NOT EXISTS risk_score (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id                  UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    tenant_id                   UUID NOT NULL,

    -- Score details
    score_type                  VARCHAR(100) NOT NULL,  -- 'composite_risk','readmission_30d','mortality_1yr','ED_utilization'
    score_value                 DECIMAL(8,4) NOT NULL,
    score_percentile            DECIMAL(5,2),
    risk_level                  VARCHAR(20) CHECK (risk_level IN ('low','moderate','high','critical')),
    risk_level_numeric          INTEGER,  -- 1=low, 2=moderate, 3=high, 4=critical

    -- Model details
    model_name                  VARCHAR(200),
    model_version               VARCHAR(50),
    feature_importance          JSONB DEFAULT '{}',
    contributing_factors        JSONB DEFAULT '[]',

    -- Temporal
    score_date                  DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_through               DATE,
    previous_score              DECIMAL(8,4),
    score_delta                 DECIMAL(8,4),
    trend                       VARCHAR(20) CHECK (trend IN ('improving','stable','worsening','unknown')),

    -- Context
    calculated_by_agent         VARCHAR(100),
    agent_action_log_id         UUID REFERENCES agent_action_log(id),

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_risk_score_patient ON risk_score(patient_id);
CREATE INDEX idx_risk_score_tenant ON risk_score(tenant_id);
CREATE INDEX idx_risk_score_type ON risk_score(score_type);
CREATE INDEX idx_risk_score_date ON risk_score(score_date DESC);
CREATE INDEX idx_risk_score_level ON risk_score(risk_level);
CREATE INDEX idx_risk_score_patient_type_date ON risk_score(patient_id, score_type, score_date DESC);

-- ============================================================
-- Clinical KPI
-- ============================================================
CREATE TABLE IF NOT EXISTS clinical_kpi (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL,

    -- KPI identification
    kpi_name                    VARCHAR(200) NOT NULL,
    kpi_category                VARCHAR(100),  -- 'quality','utilization','financial','patient_experience'
    measure_id                  VARCHAR(50),  -- HEDIS measure
    reporting_period_start      DATE NOT NULL,
    reporting_period_end        DATE NOT NULL,

    -- Values
    numerator                   INTEGER DEFAULT 0,
    denominator                 INTEGER DEFAULT 0,
    rate                        DECIMAL(8,4),  -- numerator/denominator
    rate_percent                DECIMAL(5,2),  -- rate * 100
    target_value                DECIMAL(8,4),
    benchmark_value             DECIMAL(8,4),  -- national or regional benchmark
    benchmark_source            VARCHAR(100),

    -- Performance
    performance_status          VARCHAR(20) CHECK (performance_status IN (
                                    'meeting_target','below_target','above_target','data_insufficient'
                                )),
    trend                       VARCHAR(20) CHECK (trend IN ('improving','stable','declining','unknown')),
    prior_period_rate           DECIMAL(8,4),
    rate_change                 DECIMAL(8,4),

    -- Stratification
    stratification              JSONB DEFAULT '{}',  -- by disease, age group, etc.
    excluded_patients           INTEGER DEFAULT 0,
    exclusion_reasons           JSONB DEFAULT '[]',

    calculated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_kpi_tenant ON clinical_kpi(tenant_id);
CREATE INDEX idx_kpi_name ON clinical_kpi(kpi_name);
CREATE INDEX idx_kpi_period ON clinical_kpi(reporting_period_start, reporting_period_end);
CREATE INDEX idx_kpi_measure ON clinical_kpi(measure_id);

-- ============================================================
-- Claim (Billing)
-- ============================================================
CREATE TABLE IF NOT EXISTS claim (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL,
    patient_id                  UUID REFERENCES fhir_patient(id) ON DELETE SET NULL,
    encounter_id                UUID REFERENCES fhir_encounter(id) ON DELETE SET NULL,

    -- Claim identification
    claim_number                VARCHAR(100),
    external_claim_id           VARCHAR(200),
    claim_type                  VARCHAR(50) CHECK (claim_type IN (
                                    'professional','institutional','pharmacy','oral','vision'
                                )),
    claim_status                VARCHAR(30) CHECK (claim_status IN (
                                    'draft','submitted','pending','accepted','rejected',
                                    'adjusted','reversed','paid','denied'
                                )) DEFAULT 'draft',

    -- Dates
    service_date_start          DATE,
    service_date_end            DATE,
    submitted_date              DATE,
    adjudicated_date            DATE,
    paid_date                   DATE,

    -- Amounts
    billed_amount               DECIMAL(12,2),
    allowed_amount              DECIMAL(12,2),
    paid_amount                 DECIMAL(12,2),
    patient_responsibility      DECIMAL(12,2),
    copay_amount                DECIMAL(12,2),
    deductible_amount           DECIMAL(12,2),
    coinsurance_amount          DECIMAL(12,2),

    -- Billing codes
    diagnosis_codes             JSONB DEFAULT '[]',  -- ICD-10 codes
    procedure_codes             JSONB DEFAULT '[]',  -- CPT/HCPCS codes
    revenue_codes               JSONB DEFAULT '[]',
    drg_code                    VARCHAR(20),

    -- Payer
    primary_payer               VARCHAR(200),
    primary_payer_id            VARCHAR(100),
    primary_claim_id            VARCHAR(200),
    secondary_payer             VARCHAR(200),

    -- Provider
    rendering_provider_npi      VARCHAR(20),
    rendering_provider_name     VARCHAR(200),
    billing_provider_npi        VARCHAR(20),
    facility_npi                VARCHAR(20),

    denial_reason               VARCHAR(500),
    adjustment_reason           VARCHAR(500),
    remarks                     TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claim_patient ON claim(patient_id);
CREATE INDEX idx_claim_tenant ON claim(tenant_id);
CREATE INDEX idx_claim_encounter ON claim(encounter_id);
CREATE INDEX idx_claim_status ON claim(claim_status);
CREATE INDEX idx_claim_service_date ON claim(service_date_start DESC);
CREATE INDEX idx_claim_number ON claim(claim_number);

-- ============================================================
-- RPM Episode
-- ============================================================
CREATE TABLE IF NOT EXISTS rpm_episode (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id                  UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    tenant_id                   UUID NOT NULL,

    -- Episode classification
    program_type                VARCHAR(100) NOT NULL,  -- 'RPM','CCM','PCM','BHI','GENERAL_BHI'
    disease_focus               JSONB DEFAULT '[]',  -- primary diseases being managed
    status                      VARCHAR(20) CHECK (status IN (
                                    'active','pending','suspended','completed','withdrawn'
                                )) DEFAULT 'active',

    -- Enrollment
    enrolled_date               DATE NOT NULL DEFAULT CURRENT_DATE,
    consent_date                DATE,
    consent_type                VARCHAR(50),
    disenrolled_date            DATE,
    disenrollment_reason        TEXT,

    -- Care team
    primary_provider_id         UUID,
    primary_provider_name       VARCHAR(200),
    care_coordinator_id         UUID,
    care_coordinator_name       VARCHAR(200),
    clinical_staff_ids          JSONB DEFAULT '[]',

    -- CMS billing requirements
    cms_enrollment_date         DATE,
    billing_month               DATE,
    minutes_this_month          INTEGER DEFAULT 0,
    calls_this_month            INTEGER DEFAULT 0,
    threshold_99457_met         BOOLEAN DEFAULT FALSE,  -- 20 min RPM
    threshold_99458_met         BOOLEAN DEFAULT FALSE,  -- additional 20 min RPM
    threshold_99490_met         BOOLEAN DEFAULT FALSE,  -- 20 min CCM
    threshold_99439_met         BOOLEAN DEFAULT FALSE,  -- additional 20 min CCM

    -- Devices assigned
    assigned_devices            JSONB DEFAULT '[]',

    -- Goals & plan
    care_plan_id                UUID REFERENCES fhir_care_plan(id),
    clinical_goals              JSONB DEFAULT '[]',
    monitoring_frequency        JSONB DEFAULT '{}',

    -- Summary stats
    total_readings              INTEGER DEFAULT 0,
    out_of_range_readings       INTEGER DEFAULT 0,
    critical_readings           INTEGER DEFAULT 0,
    alerts_generated            INTEGER DEFAULT 0,

    notes                       TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rpm_patient ON rpm_episode(patient_id);
CREATE INDEX idx_rpm_tenant ON rpm_episode(tenant_id);
CREATE INDEX idx_rpm_status ON rpm_episode(status);
CREATE INDEX idx_rpm_program ON rpm_episode(program_type);
CREATE INDEX idx_rpm_enrolled ON rpm_episode(enrolled_date DESC);

-- ============================================================
-- Update Triggers
-- ============================================================
CREATE TRIGGER update_patient_demographics_updated_at
    BEFORE UPDATE ON patient_demographics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_patient_engagement_updated_at
    BEFORE UPDATE ON patient_engagement
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_device_registration_updated_at
    BEFORE UPDATE ON device_registration
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_care_gap_updated_at
    BEFORE UPDATE ON care_gap
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_smart_order_set_updated_at
    BEFORE UPDATE ON smart_order_set
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_updated_at
    BEFORE UPDATE ON notification
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_template_updated_at
    BEFORE UPDATE ON notification_template
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sdoh_assessment_updated_at
    BEFORE UPDATE ON sdoh_assessment
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_claim_updated_at
    BEFORE UPDATE ON claim
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rpm_episode_updated_at
    BEFORE UPDATE ON rpm_episode
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
