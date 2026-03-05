// Neo4j constraints and indexes for InHealth
// This file is auto-applied on first startup via APOC

// ── Patient ──────────────────────────────────────────────────────────────────
CREATE CONSTRAINT patient_id_unique IF NOT EXISTS
FOR (p:Patient) REQUIRE p.id IS UNIQUE;

// ── Provider ─────────────────────────────────────────────────────────────────
CREATE CONSTRAINT provider_id_unique IF NOT EXISTS
FOR (p:Provider) REQUIRE p.id IS UNIQUE;

// ── Condition ────────────────────────────────────────────────────────────────
CREATE CONSTRAINT condition_code_unique IF NOT EXISTS
FOR (c:Condition) REQUIRE c.code IS UNIQUE;

// ── Medication ───────────────────────────────────────────────────────────────
CREATE CONSTRAINT medication_code_unique IF NOT EXISTS
FOR (m:Medication) REQUIRE m.code IS UNIQUE;

// ── Observation ──────────────────────────────────────────────────────────────
CREATE INDEX observation_patient_idx IF NOT EXISTS
FOR (o:Observation) ON (o.patient_id);
