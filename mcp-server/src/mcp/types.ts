// MCP Protocol Types for InHealth Chronic Care Platform

export interface MCPContext {
  protocol: "MCP/1.0";
  context: {
    patient: PatientContext;
    conversation_history: Message[];
    available_tools: MCPTool[];
    constraints: ClinicalConstraints;
  };
}

export interface MCPTool {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}

export interface PatientContext {
  id: string;
  demographics: PatientDemographics;
  conditions: Condition[];
  medications: Medication[];
  recent_vitals: Vital[];
  allergies: Allergy[];
  risk_scores: RiskScore[];
  recent_encounters: EncounterNote[];
  diagnostic_reports: DiagnosticReportSummary[];
  clinical_notes: ClinicalNote[];
}

export interface PatientDemographics {
  name: string;
  date_of_birth: string;
  gender: "male" | "female" | "other" | "unknown";
  age: number;
  address?: Address;
  contact?: ContactInfo;
  insurance_id?: string;
  mrn: string; // Medical Record Number
  language?: string;
}

export interface Address {
  line: string[];
  city: string;
  state: string;
  postal_code: string;
  country: string;
  latitude?: number;
  longitude?: number;
}

export interface ContactInfo {
  phone?: string;
  email?: string;
  emergency_contact?: EmergencyContact;
}

export interface EmergencyContact {
  name: string;
  relationship: string;
  phone: string;
}

export interface Condition {
  id: string;
  code: string; // ICD-10 or SNOMED CT
  system: "ICD-10" | "SNOMED-CT" | "ICD-11";
  display: string;
  status: "active" | "inactive" | "resolved" | "remission";
  onset_date?: string;
  recorded_date: string;
  severity?: "mild" | "moderate" | "severe";
  body_site?: string;
  stage?: string;
  clinical_status: string;
  verification_status: "confirmed" | "provisional" | "differential" | "refuted";
}

export interface Medication {
  id: string;
  code: string; // RxNorm
  display: string;
  status: "active" | "stopped" | "on-hold" | "completed" | "cancelled";
  dosage: Dosage;
  route?: string;
  start_date?: string;
  end_date?: string;
  prescriber?: string;
  indication?: string;
  dispense_request?: DispenseRequest;
}

export interface Dosage {
  text: string;
  dose_quantity?: {
    value: number;
    unit: string;
  };
  frequency: string;
  period?: number;
  period_unit?: "s" | "min" | "h" | "d" | "wk" | "mo" | "a";
  as_needed?: boolean;
}

export interface DispenseRequest {
  quantity: number;
  unit: string;
  expected_supply_duration?: number;
  refills_allowed?: number;
}

export interface Vital {
  id: string;
  type: VitalType;
  value: number | VitalComponent[];
  unit: string;
  recorded_at: string;
  recorded_by?: string;
  status: "final" | "preliminary" | "amended" | "corrected";
  device?: string;
  interpretation?: "N" | "H" | "L" | "HH" | "LL" | "A" | "AA";
  reference_range?: {
    low?: number;
    high?: number;
    text?: string;
  };
}

export type VitalType =
  | "blood_pressure"
  | "heart_rate"
  | "blood_glucose"
  | "oxygen_saturation"
  | "temperature"
  | "weight"
  | "height"
  | "bmi"
  | "respiratory_rate"
  | "hba1c"
  | "cholesterol"
  | "egfr"
  | "creatinine";

export interface VitalComponent {
  code: string;
  display: string;
  value: number;
  unit: string;
}

export interface Allergy {
  id: string;
  substance: string;
  substance_code?: string;
  system?: string;
  category: "food" | "medication" | "environment" | "biologic";
  criticality: "low" | "high" | "unable-to-assess";
  status: "active" | "inactive" | "resolved";
  reactions?: AllergyReaction[];
  onset_date?: string;
  recorded_date: string;
  note?: string;
}

export interface AllergyReaction {
  substance?: string;
  manifestation: string;
  severity?: "mild" | "moderate" | "severe";
  description?: string;
}

export interface RiskScore {
  model: string;
  score: number;
  risk_level: "low" | "moderate" | "high" | "critical";
  calculated_at: string;
  factors: RiskFactor[];
  recommendation?: string;
  expires_at?: string;
}

export interface RiskFactor {
  name: string;
  value: string | number;
  weight: number;
  direction: "positive" | "negative"; // positive increases risk
}

export interface EncounterNote {
  id: string;
  status: "planned" | "in-progress" | "finished" | "cancelled";
  encounter_class: string; // ambulatory, emergency, inpatient, etc.
  type_display: string;
  reason_display?: string;
  period_start: string;
  period_end?: string;
  discharge_disposition?: string;
  soap_notes?: {
    chief_complaint?: string;
    assessment?: string;
    treatment_plan?: string;
  };
}

export interface DiagnosticReportSummary {
  id: string;
  status: "registered" | "partial" | "preliminary" | "final" | "amended" | "corrected" | "cancelled";
  category: string; // LAB, RAD (radiology), PAT (pathology), etc.
  code: string; // LOINC code
  display: string;
  effective_date: string;
  conclusion?: string;
  results_summary?: string;
}

export interface ClinicalNote {
  id: string;
  type_code: string;
  type_display: string; // "Progress Note", "Discharge Summary", etc.
  date: string;
  description?: string;
  content_title?: string;
  category?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system" | "agent";
  content: string;
  timestamp: string;
  agent_id?: string;
  agent_name?: string;
  metadata?: Record<string, unknown>;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
}

export interface ToolCall {
  id: string;
  tool_name: string;
  parameters: Record<string, unknown>;
  timestamp: string;
}

export interface ToolResult {
  tool_call_id: string;
  tool_name: string;
  result: unknown;
  success: boolean;
  error?: string;
  execution_time_ms: number;
  timestamp: string;
}

export interface ClinicalConstraints {
  safety_rules: string[];
  clinical_guidelines: string[];
  drug_contraindications: string[];
  patient_specific_restrictions?: string[];
  emergency_protocols?: string[];
  formulary_restrictions?: string[];
}

export interface MCPRequest {
  patient_id: string;
  agent_id: string;
  include_history?: boolean;
  history_limit?: number;
  tool_filter?: string[];
}

export interface MCPToolExecuteRequest {
  tool_name: string;
  parameters: Record<string, unknown>;
  patient_id?: string;
  agent_id: string;
  correlation_id?: string;
}

export interface MCPToolExecuteResponse {
  tool_name: string;
  result: unknown;
  success: boolean;
  error?: string;
  execution_time_ms: number;
  timestamp: string;
  correlation_id?: string;
}

export interface FHIRBundle {
  resourceType: "Bundle";
  type: string;
  total?: number;
  entry?: FHIREntry[];
}

export interface FHIREntry {
  resource: FHIRResource;
  fullUrl?: string;
}

export interface FHIRResource {
  resourceType: string;
  id: string;
  [key: string]: unknown;
}

export interface VectorSearchResult {
  id: string;
  score: number;
  payload: {
    title?: string;
    content: string;
    source?: string;
    category?: string;
    guideline_type?: string;
    [key: string]: unknown;
  };
}

export interface DrugInteraction {
  drug1: string;
  drug2: string;
  severity: "contraindicated" | "major" | "moderate" | "minor";
  description: string;
  mechanism?: string;
  management?: string;
}

export interface Neo4jQueryResult {
  records: Array<{
    keys: string[];
    fields: unknown[];
    get: (key: string) => unknown;
  }>;
  summary: {
    query: { text: string };
    counters: Record<string, number>;
  };
}

export interface MLRiskResult {
  model_name: string;
  patient_id: string;
  risk_score: number;
  risk_level: "low" | "moderate" | "high" | "critical";
  confidence: number;
  features_used: string[];
  timestamp: string;
  recommendations: string[];
}

export interface NotificationRequest {
  recipient_type: "patient" | "provider" | "care_team";
  recipient_id: string;
  notification_type: "sms" | "email" | "push" | "in_app";
  priority: "low" | "normal" | "high" | "urgent";
  subject: string;
  body: string;
  patient_id?: string;
  metadata?: Record<string, unknown>;
}

export interface AppointmentRequest {
  patient_id: string;
  provider_id?: string;
  appointment_type: string;
  preferred_date?: string;
  preferred_time?: string;
  duration_minutes?: number;
  reason: string;
  urgency: "routine" | "urgent" | "emergency";
  notes?: string;
}

export interface HospitalSearchRequest {
  patient_id?: string;
  latitude: number;
  longitude: number;
  radius_km?: number;
  specialties?: string[];
  emergency_capable?: boolean;
  insurance_accepted?: string;
}

export interface NL2SQLRequest {
  natural_language_query: string;
  patient_id?: string;
  context?: string;
  allowed_tables?: string[];
}

export interface AuditLog {
  event_type: "tool_execution" | "context_request" | "auth_event";
  agent_id: string;
  patient_id?: string;
  tool_name?: string;
  parameters?: Record<string, unknown>;
  result_summary?: string;
  success: boolean;
  error?: string;
  execution_time_ms?: number;
  timestamp: string;
  ip_address?: string;
  correlation_id?: string;
}
