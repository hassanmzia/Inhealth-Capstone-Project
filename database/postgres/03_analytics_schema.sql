-- ============================================================
-- InHealth Chronic Care - Population Analytics Schema
-- PostgreSQL database initialization script
-- ============================================================

-- ============================================================
-- Cohort Definitions
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_cohort (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    description         TEXT DEFAULT '',
    criteria            JSONB NOT NULL DEFAULT '{}',
    -- criteria example: {"conditions": ["E11"], "age_min": 18, "age_max": 80, "risk_level": "high"}
    patient_count       INTEGER DEFAULT 0,
    created_by          UUID REFERENCES auth_user(id),
    is_active           BOOLEAN DEFAULT TRUE,
    last_computed_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_analytics_cohort_tenant ON analytics_cohort(tenant_id);

-- ============================================================
-- Cohort Membership (materialized for performance)
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_cohort_member (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cohort_id           UUID NOT NULL REFERENCES analytics_cohort(id) ON DELETE CASCADE,
    patient_id          UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    enrolled_at         TIMESTAMPTZ DEFAULT NOW(),
    risk_score          NUMERIC(5,4),
    risk_level          VARCHAR(20),  -- low, medium, high, critical
    UNIQUE(cohort_id, patient_id)
);

CREATE INDEX idx_cohort_member_cohort ON analytics_cohort_member(cohort_id);
CREATE INDEX idx_cohort_member_patient ON analytics_cohort_member(patient_id);
CREATE INDEX idx_cohort_member_risk ON analytics_cohort_member(cohort_id, risk_level);

-- ============================================================
-- Population Risk Stratification Snapshots
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_risk_snapshot (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    snapshot_date       DATE NOT NULL,
    total_patients      INTEGER DEFAULT 0,
    risk_distribution   JSONB NOT NULL DEFAULT '{}',
    -- {"low": 450, "medium": 230, "high": 85, "critical": 15}
    disease_prevalence  JSONB NOT NULL DEFAULT '{}',
    -- {"E11": 320, "I10": 410, "J44": 95, "N18": 78, "I50": 45}
    avg_risk_score      NUMERIC(5,4),
    care_gap_summary    JSONB NOT NULL DEFAULT '{}',
    -- {"A1C_overdue": 42, "eye_exam_overdue": 67, ...}
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_risk_snapshot_tenant_date ON analytics_risk_snapshot(tenant_id, snapshot_date);

-- ============================================================
-- Quality Measure Results (HEDIS/CMS measures)
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_quality_measure (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    measure_code        VARCHAR(50) NOT NULL,  -- e.g., NQF-0059 (Diabetes A1C Control)
    measure_name        VARCHAR(255) NOT NULL,
    reporting_period    VARCHAR(20) NOT NULL,   -- e.g., 2026-Q1
    denominator         INTEGER DEFAULT 0,      -- eligible patients
    numerator           INTEGER DEFAULT 0,      -- meeting measure
    exclusions          INTEGER DEFAULT 0,
    performance_rate    NUMERIC(5,4),           -- numerator / (denominator - exclusions)
    benchmark_rate      NUMERIC(5,4),           -- national/regional benchmark
    star_rating         SMALLINT,               -- 1-5 star CMS rating
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, measure_code, reporting_period)
);

CREATE INDEX idx_quality_measure_tenant ON analytics_quality_measure(tenant_id, reporting_period);

-- ============================================================
-- Predictive Model Audit Log
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_prediction_log (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    patient_id          UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    model_name          VARCHAR(100) NOT NULL,   -- e.g., xgboost_7day_v2, rf_disease_v1
    model_version       VARCHAR(50) NOT NULL,
    prediction_type     VARCHAR(50) NOT NULL,    -- risk_score, classification, regression
    input_features      JSONB NOT NULL DEFAULT '{}',
    prediction_result   JSONB NOT NULL DEFAULT '{}',
    confidence_score    NUMERIC(5,4),
    explanation         JSONB DEFAULT '{}',      -- SHAP / feature importance values
    clinician_override  BOOLEAN DEFAULT FALSE,
    override_reason     TEXT DEFAULT '',
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_prediction_log_patient ON analytics_prediction_log(patient_id, created_at DESC);
CREATE INDEX idx_prediction_log_model ON analytics_prediction_log(model_name, created_at DESC);
CREATE INDEX idx_prediction_log_tenant ON analytics_prediction_log(tenant_id, created_at DESC);

-- ============================================================
-- Agent Performance Metrics (daily aggregation)
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_agent_metrics (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    metric_date         DATE NOT NULL,
    agent_name          VARCHAR(100) NOT NULL,
    agent_tier          VARCHAR(20) NOT NULL,
    total_executions    INTEGER DEFAULT 0,
    successful          INTEGER DEFAULT 0,
    failed              INTEGER DEFAULT 0,
    avg_latency_ms      NUMERIC(10,2),
    p95_latency_ms      NUMERIC(10,2),
    p99_latency_ms      NUMERIC(10,2),
    total_tokens_used   BIGINT DEFAULT 0,
    estimated_cost_usd  NUMERIC(10,4) DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, metric_date, agent_name)
);

CREATE INDEX idx_agent_metrics_date ON analytics_agent_metrics(metric_date, agent_name);

-- ============================================================
-- Patient Engagement Tracking
-- ============================================================
CREATE TABLE IF NOT EXISTS analytics_engagement_event (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    patient_id          UUID NOT NULL REFERENCES fhir_patient(id) ON DELETE CASCADE,
    event_type          VARCHAR(50) NOT NULL,
    -- portal_login, vitals_submitted, message_sent, appointment_kept,
    -- medication_taken, goal_completed, education_viewed
    event_data          JSONB DEFAULT '{}',
    source              VARCHAR(50) DEFAULT 'web',  -- web, mobile, iot, api
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_engagement_event_patient ON analytics_engagement_event(patient_id, created_at DESC);
CREATE INDEX idx_engagement_event_type ON analytics_engagement_event(tenant_id, event_type, created_at DESC);
