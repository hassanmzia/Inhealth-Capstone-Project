-- ============================================================
-- InHealth Chronic Care - FHIR R4 Schema
-- PostgreSQL database initialization script
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- FHIR Patient Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_patient (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'Patient',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    -- Identifiers (MRN, SSN, etc.)
    identifier              JSONB DEFAULT '[]',
    mrn                     VARCHAR(50),

    -- Name
    name                    JSONB DEFAULT '[]',
    given_name              VARCHAR(255),
    family_name             VARCHAR(255),

    -- Demographics
    gender                  VARCHAR(20) CHECK (gender IN ('male','female','other','unknown')),
    birth_date              DATE,
    deceased_boolean        BOOLEAN DEFAULT FALSE,
    deceased_datetime       TIMESTAMPTZ,

    -- Contact
    telecom                 JSONB DEFAULT '[]',
    address                 JSONB DEFAULT '[]',

    -- Clinical context
    marital_status          JSONB,
    multiple_birth_boolean  BOOLEAN,
    multiple_birth_integer  INTEGER,
    photo                   JSONB DEFAULT '[]',
    contact                 JSONB DEFAULT '[]',
    communication           JSONB DEFAULT '[]',
    general_practitioner    JSONB DEFAULT '[]',
    managing_organization   JSONB,
    link                    JSONB DEFAULT '[]',

    -- Extension / metadata
    extension               JSONB DEFAULT '[]',
    meta                    JSONB,
    text                    JSONB,
    raw_fhir                JSONB,

    -- Embedding for semantic search
    embedding               vector(1536),

    -- Timestamps
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT fhir_patient_tenant_fk FOREIGN KEY (tenant_id)
        REFERENCES organizations(id) ON DELETE RESTRICT
);

CREATE INDEX idx_fhir_patient_tenant ON fhir_patient(tenant_id);
CREATE INDEX idx_fhir_patient_mrn ON fhir_patient(mrn);
CREATE INDEX idx_fhir_patient_family_name ON fhir_patient(family_name);
CREATE INDEX idx_fhir_patient_birth_date ON fhir_patient(birth_date);
CREATE INDEX idx_fhir_patient_raw_fhir_gin ON fhir_patient USING GIN(raw_fhir);
CREATE INDEX idx_fhir_patient_identifier_gin ON fhir_patient USING GIN(identifier);

-- ============================================================
-- FHIR Observation Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_observation (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'Observation',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    -- Status
    status                  VARCHAR(20) NOT NULL CHECK (status IN (
                                'registered','preliminary','final','amended',
                                'corrected','cancelled','entered-in-error','unknown'
                            )),

    -- Category & Code
    category                JSONB DEFAULT '[]',
    code                    JSONB NOT NULL,
    code_system             VARCHAR(255),
    code_value              VARCHAR(100),
    code_display            VARCHAR(500),

    -- Subject
    subject_patient_id      UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    subject_reference       VARCHAR(500),

    -- Context
    encounter_id            UUID,
    effective_datetime      TIMESTAMPTZ,
    effective_period        JSONB,
    issued                  TIMESTAMPTZ,
    performer               JSONB DEFAULT '[]',

    -- Value
    value_quantity          JSONB,
    value_codeable_concept  JSONB,
    value_string            TEXT,
    value_boolean           BOOLEAN,
    value_integer           INTEGER,
    value_range             JSONB,
    value_ratio             JSONB,
    value_sampled_data      JSONB,
    value_time              TIME,
    value_datetime          TIMESTAMPTZ,
    value_period            JSONB,

    -- Numeric convenience columns for indexing
    value_numeric           DECIMAL(18,4),
    value_unit              VARCHAR(100),

    -- Interpretation
    interpretation          JSONB DEFAULT '[]',
    body_site               JSONB,
    method                  JSONB,
    specimen                JSONB,
    device                  JSONB,
    reference_range         JSONB DEFAULT '[]',
    has_member              JSONB DEFAULT '[]',
    derived_from            JSONB DEFAULT '[]',
    component               JSONB DEFAULT '[]',
    note                    JSONB DEFAULT '[]',

    -- Metadata
    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_obs_patient ON fhir_observation(subject_patient_id);
CREATE INDEX idx_fhir_obs_tenant ON fhir_observation(tenant_id);
CREATE INDEX idx_fhir_obs_code ON fhir_observation(code_value);
CREATE INDEX idx_fhir_obs_effective ON fhir_observation(effective_datetime DESC);
CREATE INDEX idx_fhir_obs_status ON fhir_observation(status);
CREATE INDEX idx_fhir_obs_patient_code ON fhir_observation(subject_patient_id, code_value, effective_datetime DESC);
CREATE INDEX idx_fhir_obs_raw_fhir_gin ON fhir_observation USING GIN(raw_fhir);
CREATE INDEX idx_fhir_obs_value_numeric ON fhir_observation(value_numeric) WHERE value_numeric IS NOT NULL;

-- ============================================================
-- FHIR Condition Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_condition (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'Condition',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    clinical_status         JSONB,
    verification_status     JSONB,
    category                JSONB DEFAULT '[]',
    severity                JSONB,
    code                    JSONB NOT NULL,
    code_system             VARCHAR(255),
    code_value              VARCHAR(100),
    code_display            VARCHAR(500),
    icd10_code              VARCHAR(20),

    body_site               JSONB DEFAULT '[]',
    subject_patient_id      UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    encounter_id            UUID,

    onset_datetime          TIMESTAMPTZ,
    onset_age               JSONB,
    onset_period            JSONB,
    onset_range             JSONB,
    onset_string            TEXT,

    abatement_datetime      TIMESTAMPTZ,
    abatement_age           JSONB,
    abatement_period        JSONB,
    abatement_range         JSONB,
    abatement_string        TEXT,

    recorded_date           DATE,
    recorder                JSONB,
    asserter                JSONB,
    stage                   JSONB DEFAULT '[]',
    evidence                JSONB DEFAULT '[]',
    note                    JSONB DEFAULT '[]',

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_cond_patient ON fhir_condition(subject_patient_id);
CREATE INDEX idx_fhir_cond_tenant ON fhir_condition(tenant_id);
CREATE INDEX idx_fhir_cond_icd10 ON fhir_condition(icd10_code);
CREATE INDEX idx_fhir_cond_code ON fhir_condition(code_value);
CREATE INDEX idx_fhir_cond_onset ON fhir_condition(onset_datetime DESC);
CREATE INDEX idx_fhir_cond_raw_fhir_gin ON fhir_condition USING GIN(raw_fhir);

-- ============================================================
-- FHIR MedicationRequest Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_medication_request (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type               VARCHAR(50) NOT NULL DEFAULT 'MedicationRequest',
    fhir_id                     VARCHAR(255) UNIQUE,
    tenant_id                   UUID NOT NULL,

    status                      VARCHAR(30) NOT NULL CHECK (status IN (
                                    'active','on-hold','cancelled','completed',
                                    'entered-in-error','stopped','draft','unknown'
                                )),
    status_reason               JSONB,
    intent                      VARCHAR(30) NOT NULL CHECK (intent IN (
                                    'proposal','plan','order','original-order',
                                    'reflex-order','filler-order','instance-order','option'
                                )),
    category                    JSONB DEFAULT '[]',

    medication_codeable_concept JSONB,
    medication_reference        JSONB,
    rxnorm_code                 VARCHAR(50),
    drug_name                   VARCHAR(500),

    subject_patient_id          UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    encounter_id                UUID,
    supporting_information      JSONB DEFAULT '[]',
    authored_on                 TIMESTAMPTZ,
    requester                   JSONB,
    performer                   JSONB,
    performer_type              JSONB,
    recorder                    JSONB,
    reason_code                 JSONB DEFAULT '[]',
    reason_reference            JSONB DEFAULT '[]',
    based_on                    JSONB DEFAULT '[]',
    group_identifier            JSONB,
    course_of_therapy_type      JSONB,
    insurance                   JSONB DEFAULT '[]',
    note                        JSONB DEFAULT '[]',

    dosage_instruction          JSONB DEFAULT '[]',
    dispense_request            JSONB,
    substitution                JSONB,
    prior_prescription          JSONB,
    detected_issue              JSONB DEFAULT '[]',
    event_history               JSONB DEFAULT '[]',

    meta                        JSONB,
    raw_fhir                    JSONB,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_medrx_patient ON fhir_medication_request(subject_patient_id);
CREATE INDEX idx_fhir_medrx_tenant ON fhir_medication_request(tenant_id);
CREATE INDEX idx_fhir_medrx_status ON fhir_medication_request(status);
CREATE INDEX idx_fhir_medrx_rxnorm ON fhir_medication_request(rxnorm_code);
CREATE INDEX idx_fhir_medrx_authored ON fhir_medication_request(authored_on DESC);
CREATE INDEX idx_fhir_medrx_raw_fhir_gin ON fhir_medication_request USING GIN(raw_fhir);

-- ============================================================
-- FHIR DiagnosticReport Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_diagnostic_report (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'DiagnosticReport',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    status                  VARCHAR(20) NOT NULL CHECK (status IN (
                                'registered','partial','preliminary','final',
                                'amended','corrected','appended','cancelled','entered-in-error','unknown'
                            )),
    category                JSONB DEFAULT '[]',
    code                    JSONB NOT NULL,
    code_system             VARCHAR(255),
    code_value              VARCHAR(100),
    code_display            VARCHAR(500),

    subject_patient_id      UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    encounter_id            UUID,
    effective_datetime      TIMESTAMPTZ,
    effective_period        JSONB,
    issued                  TIMESTAMPTZ,
    performer               JSONB DEFAULT '[]',
    results_interpreter     JSONB DEFAULT '[]',
    specimen                JSONB DEFAULT '[]',
    result                  JSONB DEFAULT '[]',
    imaging_study           JSONB DEFAULT '[]',
    media                   JSONB DEFAULT '[]',
    conclusion              TEXT,
    conclusion_code         JSONB DEFAULT '[]',
    presented_form          JSONB DEFAULT '[]',

    embedding               vector(1536),

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_diagrpt_patient ON fhir_diagnostic_report(subject_patient_id);
CREATE INDEX idx_fhir_diagrpt_tenant ON fhir_diagnostic_report(tenant_id);
CREATE INDEX idx_fhir_diagrpt_code ON fhir_diagnostic_report(code_value);
CREATE INDEX idx_fhir_diagrpt_issued ON fhir_diagnostic_report(issued DESC);
CREATE INDEX idx_fhir_diagrpt_raw_fhir_gin ON fhir_diagnostic_report USING GIN(raw_fhir);

-- ============================================================
-- FHIR Appointment Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_appointment (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'Appointment',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    status                  VARCHAR(30) NOT NULL CHECK (status IN (
                                'proposed','pending','booked','arrived','fulfilled',
                                'cancelled','noshow','entered-in-error','checked-in','waitlist'
                            )),
    cancellation_reason     JSONB,
    service_category        JSONB DEFAULT '[]',
    service_type            JSONB DEFAULT '[]',
    specialty               JSONB DEFAULT '[]',
    appointment_type        JSONB,
    reason_code             JSONB DEFAULT '[]',
    reason_reference        JSONB DEFAULT '[]',
    priority                INTEGER DEFAULT 0,
    description             TEXT,
    supporting_information  JSONB DEFAULT '[]',
    start                   TIMESTAMPTZ,
    end                     TIMESTAMPTZ,
    minutes_duration        INTEGER,
    slot                    JSONB DEFAULT '[]',
    created_at_fhir         TIMESTAMPTZ,
    comment                 TEXT,
    based_on                JSONB DEFAULT '[]',
    participant             JSONB DEFAULT '[]',
    requested_period        JSONB DEFAULT '[]',

    subject_patient_id      UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_appt_patient ON fhir_appointment(subject_patient_id);
CREATE INDEX idx_fhir_appt_tenant ON fhir_appointment(tenant_id);
CREATE INDEX idx_fhir_appt_status ON fhir_appointment(status);
CREATE INDEX idx_fhir_appt_start ON fhir_appointment(start);

-- ============================================================
-- FHIR CarePlan Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_care_plan (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'CarePlan',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    status                  VARCHAR(20) NOT NULL CHECK (status IN (
                                'draft','active','on-hold','revoked','completed','entered-in-error','unknown'
                            )),
    intent                  VARCHAR(20) NOT NULL CHECK (intent IN (
                                'proposal','plan','order','option'
                            )),
    category                JSONB DEFAULT '[]',
    title                   VARCHAR(500),
    description             TEXT,

    subject_patient_id      UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    encounter_id            UUID,
    period_start            TIMESTAMPTZ,
    period_end              TIMESTAMPTZ,
    created_at_fhir         TIMESTAMPTZ,
    author                  JSONB,
    contributor             JSONB DEFAULT '[]',
    care_team               JSONB DEFAULT '[]',
    addresses               JSONB DEFAULT '[]',
    supporting_info         JSONB DEFAULT '[]',
    goal                    JSONB DEFAULT '[]',
    activity                JSONB DEFAULT '[]',
    note                    JSONB DEFAULT '[]',

    embedding               vector(1536),

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_careplan_patient ON fhir_care_plan(subject_patient_id);
CREATE INDEX idx_fhir_careplan_tenant ON fhir_care_plan(tenant_id);
CREATE INDEX idx_fhir_careplan_status ON fhir_care_plan(status);

-- ============================================================
-- FHIR AllergyIntolerance Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_allergy_intolerance (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'AllergyIntolerance',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    clinical_status         JSONB,
    verification_status     JSONB,
    type                    VARCHAR(20) CHECK (type IN ('allergy','intolerance')),
    category                JSONB DEFAULT '[]',
    criticality             VARCHAR(20) CHECK (criticality IN ('low','high','unable-to-assess')),
    code                    JSONB,
    code_value              VARCHAR(100),
    code_display            VARCHAR(500),

    patient_id              UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    encounter_id            UUID,
    onset_datetime          TIMESTAMPTZ,
    onset_age               JSONB,
    onset_period            JSONB,
    onset_range             JSONB,
    onset_string            TEXT,
    recorded_date           TIMESTAMPTZ,
    recorder                JSONB,
    asserter                JSONB,
    last_occurrence         TIMESTAMPTZ,
    note                    JSONB DEFAULT '[]',
    reaction                JSONB DEFAULT '[]',

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_allergy_patient ON fhir_allergy_intolerance(patient_id);
CREATE INDEX idx_fhir_allergy_tenant ON fhir_allergy_intolerance(tenant_id);
CREATE INDEX idx_fhir_allergy_code ON fhir_allergy_intolerance(code_value);

-- ============================================================
-- FHIR Encounter Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_encounter (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'Encounter',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    status                  VARCHAR(30) NOT NULL CHECK (status IN (
                                'planned','arrived','triaged','in-progress','onleave',
                                'finished','cancelled','entered-in-error','unknown'
                            )),
    status_history          JSONB DEFAULT '[]',
    class                   JSONB NOT NULL,
    class_history           JSONB DEFAULT '[]',
    type                    JSONB DEFAULT '[]',
    service_type            JSONB,
    priority                JSONB,

    subject_patient_id      UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    episode_of_care         JSONB DEFAULT '[]',
    based_on                JSONB DEFAULT '[]',
    participant             JSONB DEFAULT '[]',
    appointment             JSONB DEFAULT '[]',

    period_start            TIMESTAMPTZ,
    period_end              TIMESTAMPTZ,
    length                  JSONB,
    reason_code             JSONB DEFAULT '[]',
    reason_reference        JSONB DEFAULT '[]',
    diagnosis               JSONB DEFAULT '[]',
    account                 JSONB DEFAULT '[]',
    hospitalization         JSONB,
    location                JSONB DEFAULT '[]',
    service_provider        JSONB,
    part_of                 JSONB,

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_enc_patient ON fhir_encounter(subject_patient_id);
CREATE INDEX idx_fhir_enc_tenant ON fhir_encounter(tenant_id);
CREATE INDEX idx_fhir_enc_status ON fhir_encounter(status);
CREATE INDEX idx_fhir_enc_period_start ON fhir_encounter(period_start DESC);

-- ============================================================
-- FHIR Procedure Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_procedure (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'Procedure',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    status                  VARCHAR(30) NOT NULL CHECK (status IN (
                                'preparation','in-progress','not-done','on-hold',
                                'stopped','completed','entered-in-error','unknown'
                            )),
    status_reason           JSONB,
    category                JSONB,
    code                    JSONB NOT NULL,
    code_system             VARCHAR(255),
    code_value              VARCHAR(100),
    code_display            VARCHAR(500),
    cpt_code                VARCHAR(20),

    subject_patient_id      UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    encounter_id            UUID,
    performed_datetime      TIMESTAMPTZ,
    performed_period        JSONB,
    performed_string        TEXT,
    performed_age           JSONB,
    performed_range         JSONB,
    recorder                JSONB,
    asserter                JSONB,
    performer               JSONB DEFAULT '[]',
    location                JSONB,
    reason_code             JSONB DEFAULT '[]',
    reason_reference        JSONB DEFAULT '[]',
    body_site               JSONB DEFAULT '[]',
    outcome                 JSONB,
    report                  JSONB DEFAULT '[]',
    complication            JSONB DEFAULT '[]',
    complication_detail     JSONB DEFAULT '[]',
    follow_up               JSONB DEFAULT '[]',
    note                    JSONB DEFAULT '[]',
    focal_device            JSONB DEFAULT '[]',
    used_reference          JSONB DEFAULT '[]',
    used_code               JSONB DEFAULT '[]',

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_proc_patient ON fhir_procedure(subject_patient_id);
CREATE INDEX idx_fhir_proc_tenant ON fhir_procedure(tenant_id);
CREATE INDEX idx_fhir_proc_code ON fhir_procedure(code_value);
CREATE INDEX idx_fhir_proc_performed ON fhir_procedure(performed_datetime DESC);

-- ============================================================
-- FHIR Immunization Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_immunization (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'Immunization',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    status                  VARCHAR(20) NOT NULL CHECK (status IN (
                                'completed','entered-in-error','not-done'
                            )),
    status_reason           JSONB,
    vaccine_code            JSONB NOT NULL,
    cvx_code                VARCHAR(20),
    vaccine_display         VARCHAR(500),

    patient_id              UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    encounter_id            UUID,
    occurrence_datetime     TIMESTAMPTZ,
    occurrence_string       TEXT,
    recorded               TIMESTAMPTZ,
    primary_source          BOOLEAN,
    report_origin           JSONB,
    location                JSONB,
    manufacturer            JSONB,
    lot_number              VARCHAR(100),
    expiration_date         DATE,
    site                    JSONB,
    route                   JSONB,
    dose_quantity           JSONB,
    performer               JSONB DEFAULT '[]',
    note                    JSONB DEFAULT '[]',
    reason_code             JSONB DEFAULT '[]',
    reason_reference        JSONB DEFAULT '[]',
    is_subpotent            BOOLEAN,
    subpotent_reason        JSONB DEFAULT '[]',
    education               JSONB DEFAULT '[]',
    program_eligibility     JSONB DEFAULT '[]',
    funding_source          JSONB,
    reaction                JSONB DEFAULT '[]',
    protocol_applied        JSONB DEFAULT '[]',

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_imm_patient ON fhir_immunization(patient_id);
CREATE INDEX idx_fhir_imm_tenant ON fhir_immunization(tenant_id);
CREATE INDEX idx_fhir_imm_cvx ON fhir_immunization(cvx_code);
CREATE INDEX idx_fhir_imm_occurrence ON fhir_immunization(occurrence_datetime DESC);

-- ============================================================
-- FHIR DocumentReference Resource
-- ============================================================
CREATE TABLE IF NOT EXISTS fhir_document_reference (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    resource_type           VARCHAR(50) NOT NULL DEFAULT 'DocumentReference',
    fhir_id                 VARCHAR(255) UNIQUE,
    tenant_id               UUID NOT NULL,

    master_identifier       JSONB,
    identifier              JSONB DEFAULT '[]',
    status                  VARCHAR(20) NOT NULL CHECK (status IN (
                                'current','superseded','entered-in-error'
                            )),
    doc_status              VARCHAR(20) CHECK (doc_status IN (
                                'preliminary','final','amended','entered-in-error'
                            )),
    type                    JSONB,
    category                JSONB DEFAULT '[]',

    subject_patient_id      UUID REFERENCES fhir_patient(id) ON DELETE CASCADE,
    date                    TIMESTAMPTZ,
    author                  JSONB DEFAULT '[]',
    authenticator           JSONB,
    custodian               JSONB,
    relates_to              JSONB DEFAULT '[]',
    description             TEXT,
    security_label          JSONB DEFAULT '[]',
    content                 JSONB NOT NULL,
    context                 JSONB,

    embedding               vector(1536),

    meta                    JSONB,
    raw_fhir                JSONB,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fhir_docref_patient ON fhir_document_reference(subject_patient_id);
CREATE INDEX idx_fhir_docref_tenant ON fhir_document_reference(tenant_id);
CREATE INDEX idx_fhir_docref_status ON fhir_document_reference(status);
CREATE INDEX idx_fhir_docref_date ON fhir_document_reference(date DESC);

-- ============================================================
-- Agent Action Log
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_action_log (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID,

    -- Agent identification
    agent_name              VARCHAR(100) NOT NULL,
    agent_tier              VARCHAR(20) CHECK (agent_tier IN ('tier1','tier2','tier3','orchestrator')),
    pipeline_name           VARCHAR(200),
    session_id              UUID,
    task_id                 VARCHAR(255),

    -- Action details
    action_type             VARCHAR(100) NOT NULL,
    action_subtype          VARCHAR(100),
    input_data              JSONB,
    output_data             JSONB,
    tool_calls              JSONB DEFAULT '[]',

    -- Patient context
    patient_id              UUID REFERENCES fhir_patient(id) ON DELETE SET NULL,
    resource_type           VARCHAR(50),
    resource_id             UUID,

    -- Execution metadata
    status                  VARCHAR(20) NOT NULL CHECK (status IN (
                                'started','in_progress','completed','failed','cancelled'
                            )) DEFAULT 'started',
    error_message           TEXT,
    error_traceback         TEXT,
    duration_ms             INTEGER,
    tokens_used             INTEGER,
    model_used              VARCHAR(100),
    cost_usd                DECIMAL(10,6),

    -- LangGraph state
    langgraph_state         JSONB,
    langgraph_node          VARCHAR(100),
    langgraph_edge          VARCHAR(200),

    -- A2A context
    a2a_message_id          VARCHAR(255),
    a2a_sender_agent        VARCHAR(100),
    a2a_receiver_agent      VARCHAR(100),
    a2a_channel             VARCHAR(100),

    -- HITL context
    hitl_required           BOOLEAN DEFAULT FALSE,
    hitl_decision           VARCHAR(50),
    hitl_reviewer_id        UUID,
    hitl_reviewed_at        TIMESTAMPTZ,
    hitl_notes              TEXT,

    -- Timestamps
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_agent_log_agent_name ON agent_action_log(agent_name);
CREATE INDEX idx_agent_log_patient ON agent_action_log(patient_id);
CREATE INDEX idx_agent_log_tenant ON agent_action_log(tenant_id);
CREATE INDEX idx_agent_log_status ON agent_action_log(status);
CREATE INDEX idx_agent_log_started_at ON agent_action_log(started_at DESC);
CREATE INDEX idx_agent_log_session ON agent_action_log(session_id);
CREATE INDEX idx_agent_log_task ON agent_action_log(task_id);
CREATE INDEX idx_agent_log_pipeline ON agent_action_log(pipeline_name);
CREATE INDEX idx_agent_log_a2a ON agent_action_log(a2a_message_id) WHERE a2a_message_id IS NOT NULL;
CREATE INDEX idx_agent_log_input_gin ON agent_action_log USING GIN(input_data);
CREATE INDEX idx_agent_log_output_gin ON agent_action_log USING GIN(output_data);

-- ============================================================
-- Update Timestamp Trigger
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_fhir_patient_updated_at
    BEFORE UPDATE ON fhir_patient
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_observation_updated_at
    BEFORE UPDATE ON fhir_observation
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_condition_updated_at
    BEFORE UPDATE ON fhir_condition
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_medication_request_updated_at
    BEFORE UPDATE ON fhir_medication_request
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_diagnostic_report_updated_at
    BEFORE UPDATE ON fhir_diagnostic_report
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_appointment_updated_at
    BEFORE UPDATE ON fhir_appointment
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_care_plan_updated_at
    BEFORE UPDATE ON fhir_care_plan
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_allergy_intolerance_updated_at
    BEFORE UPDATE ON fhir_allergy_intolerance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_encounter_updated_at
    BEFORE UPDATE ON fhir_encounter
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_procedure_updated_at
    BEFORE UPDATE ON fhir_procedure
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_immunization_updated_at
    BEFORE UPDATE ON fhir_immunization
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhir_document_reference_updated_at
    BEFORE UPDATE ON fhir_document_reference
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
