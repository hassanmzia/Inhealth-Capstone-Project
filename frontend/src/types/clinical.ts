// Clinical Data TypeScript Type Definitions
// InHealth Chronic Care Platform

// ─── Vital Signs ──────────────────────────────────────────────────────────────

export type VitalType =
  | 'heart_rate'
  | 'blood_pressure_systolic'
  | 'blood_pressure_diastolic'
  | 'spo2'
  | 'temperature'
  | 'weight'
  | 'height'
  | 'bmi'
  | 'respiratory_rate'
  | 'pain_score'
  | 'glucose'
  | 'ecg'

export type VitalStatus = 'normal' | 'warning' | 'critical' | 'unknown'

export type VitalTrend = 'up' | 'down' | 'stable'

export interface VitalSign {
  id: string
  patientId: string
  type: VitalType
  value: number
  unit: string
  timestamp: string       // ISO datetime
  status: VitalStatus
  trend?: VitalTrend
  source: 'manual' | 'device' | 'ehr' | 'iot'
  deviceId?: string
  loincCode?: string
  // BP has two values
  systolic?: number
  diastolic?: number
  // Reference ranges
  normalMin?: number
  normalMax?: number
  criticalMin?: number
  criticalMax?: number
  // ECG-specific fields
  ecgRhythm?: EcgRhythm
  ecgWaveform?: number[]  // raw waveform samples
}

export type EcgRhythm =
  | 'normal_sinus'
  | 'sinus_bradycardia'
  | 'sinus_tachycardia'
  | 'atrial_fibrillation'
  | 'atrial_flutter'
  | 'ventricular_tachycardia'
  | 'ventricular_fibrillation'

export const ECG_RHYTHM_LABELS: Record<EcgRhythm, string> = {
  normal_sinus: 'Normal Sinus Rhythm',
  sinus_bradycardia: 'Sinus Bradycardia',
  sinus_tachycardia: 'Sinus Tachycardia',
  atrial_fibrillation: 'Atrial Fibrillation',
  atrial_flutter: 'Atrial Flutter',
  ventricular_tachycardia: 'V-Tach',
  ventricular_fibrillation: 'V-Fib',
}

export const ECG_RHYTHM_STATUS: Record<EcgRhythm, VitalStatus> = {
  normal_sinus: 'normal',
  sinus_bradycardia: 'warning',
  sinus_tachycardia: 'warning',
  atrial_fibrillation: 'critical',
  atrial_flutter: 'critical',
  ventricular_tachycardia: 'critical',
  ventricular_fibrillation: 'critical',
}

export interface VitalSignSeries {
  type: VitalType
  label: string
  unit: string
  color: string
  data: Array<{
    timestamp: string
    value: number
    status: VitalStatus
  }>
  normalRange?: { min: number; max: number }
  criticalRange?: { min: number; max: number }
}

export const VITAL_RANGES: Record<VitalType, { normal: [number, number]; critical: [number, number]; unit: string }> = {
  heart_rate: { normal: [60, 100], critical: [40, 150], unit: 'bpm' },
  blood_pressure_systolic: { normal: [90, 140], critical: [70, 180], unit: 'mmHg' },
  blood_pressure_diastolic: { normal: [60, 90], critical: [40, 110], unit: 'mmHg' },
  spo2: { normal: [95, 100], critical: [88, 100], unit: '%' },
  temperature: { normal: [36.1, 37.2], critical: [35, 40], unit: '°C' },
  weight: { normal: [0, 999], critical: [0, 999], unit: 'kg' },
  height: { normal: [0, 250], critical: [0, 250], unit: 'cm' },
  bmi: { normal: [18.5, 24.9], critical: [10, 50], unit: 'kg/m²' },
  respiratory_rate: { normal: [12, 20], critical: [8, 30], unit: '/min' },
  pain_score: { normal: [0, 3], critical: [7, 10], unit: '/10' },
  glucose: { normal: [70, 180], critical: [54, 400], unit: 'mg/dL' },
  ecg: { normal: [60, 100], critical: [40, 150], unit: 'bpm' },
}

// ─── Lab Results ──────────────────────────────────────────────────────────────

export type LabResultStatus = 'normal' | 'low' | 'high' | 'critical_low' | 'critical_high' | 'pending' | 'cancelled'

export interface LabResult {
  id: string
  patientId: string
  loincCode: string
  name: string
  value: number | string
  unit: string
  referenceRange?: string
  normalMin?: number
  normalMax?: number
  criticalMin?: number
  criticalMax?: number
  status: LabResultStatus
  collectedAt: string
  resultedAt: string
  orderedBy?: string
  laboratoryName?: string
  specimenType?: string
  note?: string
  panelName?: string    // e.g., "Basic Metabolic Panel"
  panelId?: string
  fhirObservationId?: string
}

export interface LabPanel {
  id: string
  name: string
  collectedAt: string
  resultedAt: string
  status: 'final' | 'preliminary' | 'pending'
  results: LabResult[]
}

// ─── Risk Scores ──────────────────────────────────────────────────────────────

export type RiskCategory = 'critical' | 'high' | 'medium' | 'low'

export interface RiskScore {
  id: string
  patientId: string
  type: RiskScoreType
  score: number           // 0-100
  category: RiskCategory
  calculatedAt: string
  validUntil?: string
  model: string
  modelVersion: string
  confidence: number      // 0-100
  features: RiskFeature[]
  trend?: 'increasing' | 'decreasing' | 'stable'
  previousScore?: number
  previousCalculatedAt?: string
}

export type RiskScoreType =
  | 'readmission_30day'
  | 'readmission_90day'
  | 'cardiovascular'
  | 'diabetes_complications'
  | 'ckd_progression'
  | 'fall_risk'
  | 'mortality_1year'
  | 'ed_utilization'
  | 'medication_nonadherence'
  | 'composite'

export interface RiskFeature {
  name: string
  displayName: string
  value: number | string
  importance: number      // 0-1 (SHAP value magnitude)
  direction: 'increases_risk' | 'decreases_risk'
  category: 'demographics' | 'clinical' | 'labs' | 'medications' | 'utilization' | 'sdoh'
}

// ─── Care Gaps ────────────────────────────────────────────────────────────────

export type CareGapPriority = 'critical' | 'high' | 'medium' | 'low'
export type CareGapStatus = 'open' | 'in_progress' | 'closed' | 'deferred' | 'excluded'
export type CareGapCategory = 'preventive' | 'chronic_management' | 'medication' | 'referral' | 'follow_up' | 'immunization' | 'screening'

export interface CareGap {
  id: string
  patientId: string
  title: string
  description: string
  category: CareGapCategory
  priority: CareGapPriority
  status: CareGapStatus
  dueDate?: string
  openedAt: string
  closedAt?: string
  deferredUntil?: string
  measure?: string          // HEDIS measure code
  measureDescription?: string
  aiRecommendation?: string
  recommendationSource?: string
  evidenceLevel?: 'A' | 'B' | 'C' | 'D'
  assignedTo?: string
  closedBy?: string
  closureNote?: string
  icdCode?: string
  cptCode?: string
  relatedConditions?: string[]
}

// ─── Clinical Encounter ───────────────────────────────────────────────────────

export type EncounterType = 'office_visit' | 'telehealth' | 'emergency' | 'inpatient' | 'preventive' | 'follow_up' | 'procedure'

export interface Encounter {
  id: string
  patientId: string
  type: EncounterType
  status: 'planned' | 'in_progress' | 'completed' | 'cancelled'
  encounterDate: string
  duration?: number       // minutes
  provider: {
    id: string
    name: string
    specialty: string
    npi?: string
  }
  facility?: {
    id: string
    name: string
    address?: string
  }
  chiefComplaint?: string
  diagnoses: Array<{
    code: string
    display: string
    type: 'primary' | 'secondary'
  }>
  procedures?: Array<{
    code: string
    display: string
    date: string
  }>
  vitalSigns?: VitalSign[]
  notes?: string
  disposition?: string
  followUpInstructions?: string
  billingCodes?: string[]
  fhirEncounterId?: string
}

// ─── Medication ───────────────────────────────────────────────────────────────

export type MedicationAdherenceStatus = 'adherent' | 'partial' | 'non_adherent' | 'unknown'

export interface Medication {
  id: string
  patientId: string
  name: string
  genericName?: string
  brandName?: string
  rxNormCode?: string
  ndc?: string
  dose: string
  doseUnit: string
  frequency: string
  route: string
  indication?: string
  prescribedBy?: string
  prescribedDate: string
  startDate: string
  endDate?: string
  status: 'active' | 'discontinued' | 'on_hold' | 'completed'
  adherenceStatus?: MedicationAdherenceStatus
  pdc?: number           // Proportion of Days Covered 0-1
  lastFillDate?: string
  nextRefillDate?: string
  daysSupply?: number
  refillsRemaining?: number
  interactions?: MedicationInteraction[]
  isControlledSubstance?: boolean
  isPriorAuthRequired?: boolean
  tierLevel?: number     // Formulary tier
  copay?: number
  fhirMedicationRequestId?: string
}

export interface MedicationInteraction {
  id: string
  drug1: string
  drug2: string
  severity: 'contraindicated' | 'major' | 'moderate' | 'minor'
  description: string
  mechanism?: string
  clinicalSignificance?: string
  recommendation: string
  source: string
}

// ─── Patient Summary ──────────────────────────────────────────────────────────

export interface PatientSummary {
  id: string
  fhirPatientId?: string
  mrn: string
  firstName: string
  lastName: string
  dateOfBirth: string
  age: number
  gender: 'male' | 'female' | 'other' | 'unknown'
  race?: string
  ethnicity?: string
  preferredLanguage?: string
  phone?: string
  email?: string
  address?: {
    line: string[]
    city: string
    state: string
    postalCode: string
    country: string
  }
  primaryProvider?: {
    id: string
    name: string
    specialty: string
  }
  insurancePlan?: {
    planName: string
    memberId: string
    groupId?: string
  }
  activeConditions: Array<{
    code: string
    display: string
    onsetDate?: string
    severity?: string
  }>
  riskScore?: RiskScore
  openCareGaps: number
  lastContactDate?: string
  lastEncounterDate?: string
  nextAppointmentDate?: string
  alertStatus: 'critical' | 'warning' | 'normal' | 'none'
  alertCount: number
  isActive: boolean
  tenantId: string
  createdAt: string
  updatedAt: string
  photoUrl?: string
}

// ─── SDOH ─────────────────────────────────────────────────────────────────────

export type SDOHDomain =
  | 'food_insecurity'
  | 'housing_instability'
  | 'transportation'
  | 'financial_strain'
  | 'social_isolation'
  | 'interpersonal_violence'
  | 'education'
  | 'employment'
  | 'health_literacy'

export interface SDOHAssessment {
  id: string
  patientId: string
  assessedAt: string
  assessedBy?: string
  screeningTool: string   // e.g., 'AHC HRSN', 'PRAPARE'
  domains: Array<{
    domain: SDOHDomain
    positiveScreen: boolean
    score?: number
    notes?: string
  }>
  totalScore?: number
  resources?: Array<{
    name: string
    category: SDOHDomain
    phone?: string
    website?: string
    address?: string
    eligibility?: string
    referralStatus?: 'referred' | 'connected' | 'declined' | 'pending'
  }>
}

// ─── Alert / Notification ─────────────────────────────────────────────────────

export type AlertSeverity = 'critical' | 'urgent' | 'soon' | 'routine'
export type AlertCategory =
  | 'vital_sign'
  | 'lab_result'
  | 'medication'
  | 'care_gap'
  | 'risk_score'
  | 'appointment'
  | 'agent_recommendation'
  | 'system'

export interface ClinicalAlert {
  id: string
  patientId: string
  patientName: string
  severity: AlertSeverity
  category: AlertCategory
  title: string
  description: string
  value?: string
  normalRange?: string
  timestamp: string
  isRead: boolean
  isAcknowledged: boolean
  acknowledgedBy?: string
  acknowledgedAt?: string
  escalatedAt?: string
  escalationCount: number
  agentId?: string
  fhirObservationId?: string
  actionUrl?: string
  actions?: Array<{
    label: string
    action: string
    primary?: boolean
  }>
}

// ─── Population Health ─────────────────────────────────────────────────────────

export interface PopulationMetrics {
  tenantId: string
  reportDate: string
  totalPatients: number
  activePatients: number
  riskStratification: {
    critical: number
    high: number
    medium: number
    low: number
  }
  diseasePrevalence: Array<{
    condition: string
    icdCode: string
    count: number
    percentage: number
  }>
  careGapRates: Array<{
    category: CareGapCategory
    openGaps: number
    closureRate: number
  }>
  qualityMeasures: Array<{
    measure: string
    hedisCode: string
    numerator: number
    denominator: number
    rate: number
    benchmark: number
    gap: number
  }>
  readmissionRate30Day: number
  avgRiskScore: number
  medicationAdherenceAvg: number
}

// ─── Health Goals (Patient-facing) ───────────────────────────────────────────

export type GoalStatus = 'active' | 'achieved' | 'not_started' | 'cancelled'
export type GoalCategory = 'weight' | 'glucose' | 'blood_pressure' | 'activity' | 'medication' | 'diet' | 'labs' | 'lifestyle'

export interface HealthGoal {
  id: string
  patientId: string
  category: GoalCategory
  title: string
  description: string
  targetValue?: number
  targetUnit?: string
  currentValue?: number
  baselineValue?: number
  startDate: string
  targetDate?: string
  status: GoalStatus
  progress: number        // 0-100%
  achievedDate?: string
  createdBy: string
  lastUpdated: string
  milestones?: Array<{
    title: string
    targetDate: string
    achieved: boolean
    achievedDate?: string
  }>
  badges?: string[]
  streakDays?: number
}
