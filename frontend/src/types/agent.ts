// Agent TypeScript Type Definitions
// InHealth Chronic Care — 25-agent AI pipeline

// ─── Agent Tiers ──────────────────────────────────────────────────────────────

export type AgentTier =
  | 'tier1_ingestion'
  | 'tier2_analysis'
  | 'tier3_clinical'
  | 'tier4_coordination'
  | 'tier5_engagement'

export const AGENT_TIER_LABELS: Record<AgentTier, string> = {
  tier1_ingestion: 'Tier 1 — Data Ingestion',
  tier2_analysis: 'Tier 2 — Analysis',
  tier3_clinical: 'Tier 3 — Clinical Intelligence',
  tier4_coordination: 'Tier 4 — Care Coordination',
  tier5_engagement: 'Tier 5 — Patient Engagement',
}

export const AGENT_TIER_COLORS: Record<AgentTier, string> = {
  tier1_ingestion: '#1d6fdb',
  tier2_analysis: '#7c3aed',
  tier3_clinical: '#e11d48',
  tier4_coordination: '#d97706',
  tier5_engagement: '#16a34a',
}

// ─── Agent Status ─────────────────────────────────────────────────────────────

export type AgentStatus = 'idle' | 'running' | 'active' | 'error' | 'paused' | 'disabled'

export interface AgentStatusInfo {
  agentId: string
  agentName: string
  status: AgentStatus
  tier: AgentTier
  lastRun?: string          // ISO datetime
  nextScheduledRun?: string
  executionsToday: number
  averageRuntime: number    // seconds
  successRate: number       // 0-100
  errorMessage?: string
  currentPatientId?: string
  queueDepth: number
}

// ─── Agent Definitions (all 25 agents) ───────────────────────────────────────

export type AgentId =
  // Tier 1: Data Ingestion & Processing
  | 'fhir_ingestion_agent'
  | 'ehr_sync_agent'
  | 'lab_result_agent'
  | 'vital_signs_agent'
  | 'cgm_data_agent'
  // Tier 2: Analysis & Risk Assessment
  | 'risk_stratification_agent'
  | 'predictive_analytics_agent'
  | 'nlp_notes_agent'
  | 'drug_interaction_agent'
  | 'population_health_agent'
  // Tier 3: Clinical Intelligence
  | 'clinical_guidelines_agent'
  | 'diagnosis_support_agent'
  | 'treatment_optimizer_agent'
  | 'care_gap_detection_agent'
  | 'medication_adherence_agent'
  // Tier 4: Care Coordination
  | 'care_plan_agent'
  | 'appointment_scheduler_agent'
  | 'referral_agent'
  | 'sdoh_assessment_agent'
  | 'billing_coding_agent'
  // Tier 5: Patient Engagement
  | 'patient_education_agent'
  | 'health_coaching_agent'
  | 'notification_agent'
  | 'telemedicine_agent'
  | 'research_matching_agent'

export interface AgentDefinition {
  id: AgentId
  name: string
  description: string
  tier: AgentTier
  icon: string
  capabilities: string[]
  triggers: AgentTrigger[]
  outputs: string[]
  requiresHITL: boolean
  avgRuntime: number   // seconds
  schedule?: string    // cron-like
}

export const AGENT_DEFINITIONS: AgentDefinition[] = [
  // ── Tier 1 ────────────────────────────────────────────────────────────────
  {
    id: 'fhir_ingestion_agent',
    name: 'FHIR Ingestion Agent',
    description: 'Ingests and validates FHIR R4 resources from external EHR systems',
    tier: 'tier1_ingestion',
    icon: 'Database',
    capabilities: ['FHIR R4 validation', 'resource mapping', 'deduplication'],
    triggers: ['ehr_sync', 'manual', 'webhook'],
    outputs: ['validated_fhir_bundle'],
    requiresHITL: false,
    avgRuntime: 12,
  },
  {
    id: 'ehr_sync_agent',
    name: 'EHR Sync Agent',
    description: 'Bi-directional sync with Epic, Cerner, and other EHR systems via SMART on FHIR',
    tier: 'tier1_ingestion',
    icon: 'RefreshCw',
    capabilities: ['SMART on FHIR', 'bi-directional sync', 'conflict resolution'],
    triggers: ['scheduled', 'manual'],
    outputs: ['synced_records'],
    requiresHITL: false,
    avgRuntime: 45,
    schedule: '*/15 * * * *',
  },
  {
    id: 'lab_result_agent',
    name: 'Lab Result Agent',
    description: 'Processes incoming lab results, flags abnormals, triggers downstream analysis',
    tier: 'tier1_ingestion',
    icon: 'FlaskConical',
    capabilities: ['HL7 parsing', 'normal range evaluation', 'critical value detection'],
    triggers: ['hl7_message', 'fhir_observation', 'manual'],
    outputs: ['processed_labs', 'critical_alerts'],
    requiresHITL: false,
    avgRuntime: 8,
  },
  {
    id: 'vital_signs_agent',
    name: 'Vital Signs Agent',
    description: 'Real-time processing of vital signs from IoT devices and manual entry',
    tier: 'tier1_ingestion',
    icon: 'Activity',
    capabilities: ['real-time processing', 'anomaly detection', 'trend analysis'],
    triggers: ['iot_stream', 'manual_entry', 'device_webhook'],
    outputs: ['processed_vitals', 'vital_alerts'],
    requiresHITL: false,
    avgRuntime: 2,
  },
  {
    id: 'cgm_data_agent',
    name: 'CGM Data Agent',
    description: 'Processes continuous glucose monitoring data, calculates TIR, GMI, and patterns',
    tier: 'tier1_ingestion',
    icon: 'TrendingUp',
    capabilities: ['CGM integration', 'TIR calculation', 'pattern recognition', 'LSTM prediction'],
    triggers: ['cgm_stream', 'scheduled'],
    outputs: ['glucose_analytics', 'predicted_glucose', 'tir_report'],
    requiresHITL: false,
    avgRuntime: 15,
  },
  // ── Tier 2 ────────────────────────────────────────────────────────────────
  {
    id: 'risk_stratification_agent',
    name: 'Risk Stratification Agent',
    description: 'ML-powered risk scoring using clinical data, SDOH, and historical patterns',
    tier: 'tier2_analysis',
    icon: 'BarChart3',
    capabilities: ['ML risk models', 'multi-factor analysis', 'temporal risk trends'],
    triggers: ['data_update', 'scheduled_daily', 'manual'],
    outputs: ['risk_scores', 'risk_factors', 'population_stratification'],
    requiresHITL: false,
    avgRuntime: 25,
    schedule: '0 6 * * *',
  },
  {
    id: 'predictive_analytics_agent',
    name: 'Predictive Analytics Agent',
    description: 'Predicts readmission risk, disease progression, and clinical deterioration',
    tier: 'tier2_analysis',
    icon: 'BrainCircuit',
    capabilities: ['readmission prediction', 'deterioration forecasting', 'survival analysis'],
    triggers: ['scheduled', 'admission', 'manual'],
    outputs: ['predictions', 'confidence_intervals', 'feature_importance'],
    requiresHITL: false,
    avgRuntime: 35,
  },
  {
    id: 'nlp_notes_agent',
    name: 'NLP Clinical Notes Agent',
    description: 'Extracts structured data from unstructured clinical notes using NLP',
    tier: 'tier2_analysis',
    icon: 'FileText',
    capabilities: ['NER', 'symptom extraction', 'SOAP note parsing', 'ICD-10 suggestion'],
    triggers: ['note_created', 'manual'],
    outputs: ['structured_data', 'extracted_diagnoses', 'suggested_codes'],
    requiresHITL: true,
    avgRuntime: 18,
  },
  {
    id: 'drug_interaction_agent',
    name: 'Drug Interaction Agent',
    description: 'Checks for drug-drug, drug-disease, and drug-allergy interactions',
    tier: 'tier2_analysis',
    icon: 'AlertTriangle',
    capabilities: ['DDI checking', 'contraindication detection', 'allergy cross-reactivity'],
    triggers: ['prescription_created', 'medication_change', 'manual'],
    outputs: ['interaction_alerts', 'severity_ratings', 'alternatives'],
    requiresHITL: true,
    avgRuntime: 5,
  },
  {
    id: 'population_health_agent',
    name: 'Population Health Agent',
    description: 'Analyzes population-level trends, disease prevalence, and care disparities',
    tier: 'tier2_analysis',
    icon: 'Globe',
    capabilities: ['cohort analysis', 'disparity detection', 'trend forecasting'],
    triggers: ['scheduled_weekly', 'manual'],
    outputs: ['population_metrics', 'disparity_reports', 'trend_analysis'],
    requiresHITL: false,
    avgRuntime: 120,
    schedule: '0 2 * * 1',
  },
  // ── Tier 3 ────────────────────────────────────────────────────────────────
  {
    id: 'clinical_guidelines_agent',
    name: 'Clinical Guidelines Agent',
    description: 'Applies ACC/AHA, ADA, KDIGO guidelines to generate evidence-based recommendations',
    tier: 'tier3_clinical',
    icon: 'BookOpen',
    capabilities: ['guideline matching', 'evidence grading', 'recommendation generation'],
    triggers: ['diagnosis_change', 'lab_result', 'scheduled', 'manual'],
    outputs: ['recommendations', 'evidence_citations', 'care_gaps'],
    requiresHITL: true,
    avgRuntime: 20,
  },
  {
    id: 'diagnosis_support_agent',
    name: 'Diagnosis Support Agent',
    description: 'Differential diagnosis generator using symptom clusters and clinical findings',
    tier: 'tier3_clinical',
    icon: 'Stethoscope',
    capabilities: ['differential diagnosis', 'symptom analysis', 'diagnostic uncertainty'],
    triggers: ['encounter_start', 'manual'],
    outputs: ['differential_list', 'probability_scores', 'suggested_workup'],
    requiresHITL: true,
    avgRuntime: 30,
  },
  {
    id: 'treatment_optimizer_agent',
    name: 'Treatment Optimizer Agent',
    description: 'Personalizes treatment regimens based on patient phenotype and guideline adherence',
    tier: 'tier3_clinical',
    icon: 'Target',
    capabilities: ['treatment personalization', 'outcome prediction', 'dose optimization'],
    triggers: ['recommendation_request', 'manual'],
    outputs: ['treatment_plan', 'outcome_projections', 'monitoring_parameters'],
    requiresHITL: true,
    avgRuntime: 40,
  },
  {
    id: 'care_gap_detection_agent',
    name: 'Care Gap Detection Agent',
    description: 'Identifies missed preventive care, overdue screenings, and quality measure gaps',
    tier: 'tier3_clinical',
    icon: 'ClipboardCheck',
    capabilities: ['HEDIS measures', 'preventive care tracking', 'screening due dates'],
    triggers: ['scheduled_daily', 'patient_update', 'manual'],
    outputs: ['care_gaps', 'priority_scores', 'closure_recommendations'],
    requiresHITL: false,
    avgRuntime: 10,
    schedule: '0 7 * * *',
  },
  {
    id: 'medication_adherence_agent',
    name: 'Medication Adherence Agent',
    description: 'Monitors medication adherence via PDC, refill patterns, and patient-reported data',
    tier: 'tier3_clinical',
    icon: 'Pill',
    capabilities: ['PDC calculation', 'refill gap analysis', 'adherence barriers'],
    triggers: ['refill_event', 'scheduled_weekly', 'manual'],
    outputs: ['adherence_scores', 'barrier_assessment', 'intervention_recommendations'],
    requiresHITL: false,
    avgRuntime: 12,
  },
  // ── Tier 4 ────────────────────────────────────────────────────────────────
  {
    id: 'care_plan_agent',
    name: 'Care Plan Agent',
    description: 'Generates and updates personalized care plans with measurable goals and milestones',
    tier: 'tier4_coordination',
    icon: 'ClipboardList',
    capabilities: ['care plan generation', 'goal setting', 'progress tracking'],
    triggers: ['diagnosis_change', 'risk_update', 'manual'],
    outputs: ['care_plan', 'goals', 'action_items'],
    requiresHITL: true,
    avgRuntime: 25,
  },
  {
    id: 'appointment_scheduler_agent',
    name: 'Appointment Scheduler Agent',
    description: 'Intelligently schedules follow-up appointments based on clinical urgency and availability',
    tier: 'tier4_coordination',
    icon: 'Calendar',
    capabilities: ['priority scheduling', 'slot optimization', 'reminder generation'],
    triggers: ['care_gap_detected', 'discharge', 'risk_escalation', 'manual'],
    outputs: ['scheduled_appointments', 'reminders', 'wait_list_updates'],
    requiresHITL: false,
    avgRuntime: 8,
  },
  {
    id: 'referral_agent',
    name: 'Referral Agent',
    description: 'Manages specialist referrals, tracks referral loop closure, and payer authorization',
    tier: 'tier4_coordination',
    icon: 'ArrowRightLeft',
    capabilities: ['specialist matching', 'payer authorization', 'referral tracking'],
    triggers: ['referral_order', 'manual'],
    outputs: ['referral_packets', 'authorization_requests', 'tracking_updates'],
    requiresHITL: true,
    avgRuntime: 20,
  },
  {
    id: 'sdoh_assessment_agent',
    name: 'SDOH Assessment Agent',
    description: 'Screens for social determinants of health and connects to community resources',
    tier: 'tier4_coordination',
    icon: 'Users',
    capabilities: ['SDOH screening', 'resource matching', 'barrier identification'],
    triggers: ['new_patient', 'annual_review', 'manual'],
    outputs: ['sdoh_profile', 'resource_referrals', 'barrier_report'],
    requiresHITL: false,
    avgRuntime: 15,
  },
  {
    id: 'billing_coding_agent',
    name: 'Billing & Coding Agent',
    description: 'Suggests appropriate ICD-10, CPT codes and validates documentation for billing',
    tier: 'tier4_coordination',
    icon: 'Receipt',
    capabilities: ['ICD-10 coding', 'CPT coding', 'documentation validation', 'HCC capture'],
    triggers: ['encounter_complete', 'manual'],
    outputs: ['suggested_codes', 'documentation_gaps', 'hcc_opportunities'],
    requiresHITL: true,
    avgRuntime: 15,
  },
  // ── Tier 5 ────────────────────────────────────────────────────────────────
  {
    id: 'patient_education_agent',
    name: 'Patient Education Agent',
    description: 'Generates personalized, literacy-adapted patient education materials',
    tier: 'tier5_engagement',
    icon: 'GraduationCap',
    capabilities: ['content personalization', 'literacy adaptation', 'multilingual support'],
    triggers: ['diagnosis_change', 'care_plan_update', 'manual'],
    outputs: ['education_materials', 'quiz_content', 'reading_level_score'],
    requiresHITL: false,
    avgRuntime: 20,
  },
  {
    id: 'health_coaching_agent',
    name: 'Health Coaching Agent',
    description: 'AI health coach providing motivational support and behavior change guidance',
    tier: 'tier5_engagement',
    icon: 'Heart',
    capabilities: ['motivational interviewing', 'goal coaching', 'streak tracking'],
    triggers: ['patient_message', 'scheduled', 'milestone'],
    outputs: ['coaching_messages', 'goal_updates', 'reward_events'],
    requiresHITL: false,
    avgRuntime: 10,
  },
  {
    id: 'notification_agent',
    name: 'Notification Agent',
    description: 'Orchestrates multi-channel notifications (push, SMS, email) for patients and clinicians',
    tier: 'tier5_engagement',
    icon: 'Bell',
    capabilities: ['multi-channel delivery', 'preference management', 'escalation logic'],
    triggers: ['any_alert', 'scheduled', 'reminder_due'],
    outputs: ['delivered_notifications', 'escalation_events'],
    requiresHITL: false,
    avgRuntime: 3,
  },
  {
    id: 'telemedicine_agent',
    name: 'Telemedicine Agent',
    description: 'Manages virtual visit workflows including pre-visit prep and post-visit summaries',
    tier: 'tier5_engagement',
    icon: 'Video',
    capabilities: ['visit prep', 'real-time transcription', 'post-visit summary', 'action item extraction'],
    triggers: ['appointment_start', 'appointment_complete', 'manual'],
    outputs: ['visit_summary', 'action_items', 'follow_up_orders'],
    requiresHITL: true,
    avgRuntime: 60,
  },
  {
    id: 'research_matching_agent',
    name: 'Research Matching Agent',
    description: 'Matches patients to relevant clinical trials, literature, and genomic studies',
    tier: 'tier5_engagement',
    icon: 'Microscope',
    capabilities: ['trial matching', 'eligibility screening', 'literature search', 'genomic correlation'],
    triggers: ['scheduled_weekly', 'diagnosis_change', 'manual'],
    outputs: ['matched_trials', 'relevant_literature', 'genomic_insights'],
    requiresHITL: false,
    avgRuntime: 45,
  },
]

// ─── Agent Execution ──────────────────────────────────────────────────────────

export type AgentExecutionStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'pending_hitl'

export interface AgentExecution {
  id: string
  agentId: AgentId
  agentName: string
  tier: AgentTier
  status: AgentExecutionStatus
  patientId?: string
  patientName?: string
  triggeredBy: string
  triggeredAt: string      // ISO datetime
  startedAt?: string
  completedAt?: string
  runtimeSeconds?: number
  input?: Record<string, unknown>
  output?: Record<string, unknown>
  error?: string
  traceId?: string         // Langfuse trace ID
  spanId?: string
  tokensUsed?: number
  costUsd?: number
  requiresApproval?: boolean
  approvedBy?: string
  approvedAt?: string
}

// ─── A2A Messages ─────────────────────────────────────────────────────────────

export type A2AMessageType =
  | 'task_request'
  | 'task_response'
  | 'status_update'
  | 'escalation'
  | 'data_share'
  | 'approval_request'
  | 'approval_response'

export interface A2AMessage {
  id: string
  type: A2AMessageType
  fromAgent: AgentId
  toAgent: AgentId | 'orchestrator'
  timestamp: string
  correlationId: string
  payload: Record<string, unknown>
  priority: 'low' | 'normal' | 'high' | 'critical'
  ttl?: number             // seconds
}

// ─── HITL (Human-in-the-Loop) ─────────────────────────────────────────────────

export type HITLDecision = 'approved' | 'rejected' | 'modified' | 'escalated' | 'deferred'

export interface HITLRequest {
  id: string
  executionId: string
  agentId: AgentId
  agentName: string
  patientId: string
  patientName: string
  requestType: 'approve_recommendation' | 'review_diagnosis' | 'confirm_action' | 'review_code'
  title: string
  description: string
  recommendation: string
  evidenceLevel: 'A' | 'B' | 'C' | 'D'
  confidence: number       // 0-100
  urgency: 'routine' | 'soon' | 'urgent' | 'critical'
  expiresAt: string
  createdAt: string
  decision?: HITLDecision
  decidedBy?: string
  decidedAt?: string
  modifiedRecommendation?: string
  decisionNote?: string
  featureImportance?: Array<{
    feature: string
    value: number
    direction: 'positive' | 'negative'
  }>
  sourceGuideline?: string
  sourceUrl?: string
}

// ─── LangGraph Pipeline ───────────────────────────────────────────────────────

export interface PipelineNode {
  id: string
  type: 'agent' | 'router' | 'aggregator' | 'hitl_gate' | 'start' | 'end'
  agentId?: AgentId
  label: string
  status?: AgentStatus
  position: { x: number; y: number }
}

export interface PipelineEdge {
  id: string
  source: string
  target: string
  label?: string
  type?: 'default' | 'conditional' | 'parallel'
}

export interface AgentPipeline {
  id: string
  name: string
  description: string
  nodes: PipelineNode[]
  edges: PipelineEdge[]
  status: 'idle' | 'running' | 'completed' | 'error'
  startedAt?: string
  completedAt?: string
  activeNodeId?: string
}

// ─── Langfuse Trace ───────────────────────────────────────────────────────────

export interface LangfuseTrace {
  id: string
  name: string
  sessionId?: string
  userId?: string
  input?: unknown
  output?: unknown
  metadata?: Record<string, unknown>
  tags?: string[]
  createdAt: string
  updatedAt: string
  totalCost?: number
  totalTokens?: number
}

// ─── Agent Trigger Types ──────────────────────────────────────────────────────

export type AgentTrigger =
  | 'manual'
  | 'scheduled'
  | 'scheduled_daily'
  | 'scheduled_weekly'
  | 'ehr_sync'
  | 'webhook'
  | 'hl7_message'
  | 'fhir_observation'
  | 'iot_stream'
  | 'device_webhook'
  | 'cgm_stream'
  | 'data_update'
  | 'admission'
  | 'discharge'
  | 'note_created'
  | 'prescription_created'
  | 'medication_change'
  | 'diagnosis_change'
  | 'lab_result'
  | 'risk_update'
  | 'risk_escalation'
  | 'encounter_start'
  | 'encounter_complete'
  | 'recommendation_request'
  | 'patient_update'
  | 'refill_event'
  | 'care_gap_detected'
  | 'referral_order'
  | 'new_patient'
  | 'annual_review'
  | 'patient_message'
  | 'milestone'
  | 'appointment_start'
  | 'appointment_complete'
  | 'any_alert'
  | 'reminder_due'

// ─── Agent Performance Metrics ────────────────────────────────────────────────

export interface AgentMetrics {
  agentId: AgentId
  period: 'day' | 'week' | 'month'
  totalExecutions: number
  successfulExecutions: number
  failedExecutions: number
  pendingHITL: number
  averageRuntimeSeconds: number
  p95RuntimeSeconds: number
  totalTokensUsed: number
  totalCostUsd: number
  hitlApprovalRate: number
  hitlRejectionRate: number
  impactedPatients: number
}
