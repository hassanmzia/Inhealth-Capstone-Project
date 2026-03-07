import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  Heart,
  Thermometer,
  Wind,
  Droplets,
  User,
  Play,
  Square,
  Settings2,
  AlertTriangle,
  CheckCircle2,
  Zap,
  RefreshCw,
  BrainCircuit,
  ShieldAlert,
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { cn } from '@/lib/utils'
import { usePatient, useConditions, useMedications } from '@/hooks/useFHIR'
import * as fhirService from '@/services/fhir'
import type { FHIRPatient, FHIRCondition, FHIRMedicationRequest, FHIRAllergyIntolerance } from '@/types/fhir'

// ─── Patient Clinical Context ────────────────────────────────────────────────

interface PatientClinicalContext {
  patientId: string
  name: string
  age: number | null
  gender: string | null
  weight_kg: number | null
  conditions: string[]             // Display names of active conditions
  conditionCodes: string[]         // ICD-10 / SNOMED codes
  medications: string[]            // Display names of active meds
  medicationCodes: string[]        // RxNorm codes
  allergies: string[]              // Display names
  allergyCategories: string[]      // 'medication' | 'food' | etc.
  // Derived clinical flags
  hasCKD: boolean
  hasLiverDisease: boolean
  hasCOPD: boolean
  hasAsthma: boolean
  hasDiabetes: boolean
  hasHeartFailure: boolean
  hasHypertension: boolean
  isOnAnticoagulants: boolean
  isOnBetaBlockers: boolean
  isOnACEInhibitors: boolean
  hasNSAIDAllergy: boolean
  hasPropololAllergy: boolean
  hasSuccinylcholineContraindication: boolean
  isImmunocompromised: boolean
  hasGIBleedHistory: boolean
}

/** Extract condition display name from FHIR Condition */
function getConditionName(c: FHIRCondition): string {
  return c.code?.text ?? c.code?.coding?.[0]?.display ?? 'Unknown condition'
}

function getConditionCode(c: FHIRCondition): string {
  return c.code?.coding?.[0]?.code ?? ''
}

/** Extract medication display name from FHIR MedicationRequest */
function getMedName(m: FHIRMedicationRequest): string {
  return m.medicationCodeableConcept?.text ?? m.medicationCodeableConcept?.coding?.[0]?.display ?? 'Unknown medication'
}

function getMedCode(m: FHIRMedicationRequest): string {
  return m.medicationCodeableConcept?.coding?.[0]?.code ?? ''
}

/** Extract allergy display name */
function getAllergyName(a: FHIRAllergyIntolerance): string {
  return a.code?.text ?? a.code?.coding?.[0]?.display ?? 'Unknown allergy'
}

/** Check if a string list contains any of the given keywords (case-insensitive) */
function containsAny(items: string[], keywords: string[]): boolean {
  const lower = items.map((s) => s.toLowerCase())
  return keywords.some((kw) => lower.some((item) => item.includes(kw.toLowerCase())))
}

// Medication class keywords for clinical flagging
const ANTICOAGULANT_KEYWORDS = ['warfarin', 'coumadin', 'heparin', 'enoxaparin', 'lovenox', 'rivaroxaban', 'xarelto', 'apixaban', 'eliquis', 'dabigatran', 'pradaxa', 'edoxaban']
const BETA_BLOCKER_KEYWORDS = ['metoprolol', 'atenolol', 'propranolol', 'carvedilol', 'bisoprolol', 'labetalol', 'nadolol', 'sotalol', 'nebivolol']
const ACE_INHIBITOR_KEYWORDS = ['lisinopril', 'enalapril', 'ramipril', 'captopril', 'benazepril', 'fosinopril', 'quinapril', 'perindopril']
const CKD_KEYWORDS = ['chronic kidney', 'ckd', 'renal failure', 'renal insufficiency', 'kidney disease', 'nephropathy', 'end stage renal']
const LIVER_KEYWORDS = ['cirrhosis', 'hepatitis', 'liver disease', 'hepatic', 'liver failure']
const COPD_KEYWORDS = ['copd', 'chronic obstructive']
const ASTHMA_KEYWORDS = ['asthma']
const DIABETES_KEYWORDS = ['diabetes', 'diabetic', 'type 1 dm', 'type 2 dm', 't1dm', 't2dm']
const HF_KEYWORDS = ['heart failure', 'chf', 'cardiomyopathy', 'reduced ejection']
const HTN_KEYWORDS = ['hypertension', 'high blood pressure', 'htn']
const IMMUNOCOMPROMISED_KEYWORDS = ['hiv', 'aids', 'transplant', 'immunodeficiency', 'leukemia', 'lymphoma', 'chemotherapy']
const GI_BLEED_KEYWORDS = ['gi bleed', 'gastrointestinal bleed', 'peptic ulcer', 'gastric ulcer', 'duodenal ulcer', 'melena', 'hematemesis']
const NSAID_KEYWORDS = ['nsaid', 'ibuprofen', 'naproxen', 'aspirin', 'diclofenac', 'indomethacin', 'ketorolac', 'celecoxib', 'meloxicam']

/** Build PatientClinicalContext from FHIR data */
function buildPatientContext(
  patient: FHIRPatient | undefined,
  conditions: FHIRCondition[],
  medications: FHIRMedicationRequest[],
  allergies: FHIRAllergyIntolerance[],
  patientId: string,
  patientName: string,
): PatientClinicalContext {
  const conditionNames = conditions.map(getConditionName)
  const conditionCodes = conditions.map(getConditionCode)
  const medNames = medications.map(getMedName)
  const medCodes = medications.map(getMedCode)
  const allergyNames = allergies.map(getAllergyName)
  const allergyCategories = allergies.flatMap((a) => a.category ?? [])

  // Calculate age from birthDate
  let age: number | null = null
  if (patient?.birthDate) {
    const birth = new Date(patient.birthDate)
    const today = new Date()
    age = today.getFullYear() - birth.getFullYear()
    const monthDiff = today.getMonth() - birth.getMonth()
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--
    }
  }

  return {
    patientId,
    name: patientName,
    age,
    gender: patient?.gender ?? null,
    weight_kg: null, // Would need recent vitals observation for weight
    conditions: conditionNames,
    conditionCodes,
    medications: medNames,
    medicationCodes: medCodes,
    allergies: allergyNames,
    allergyCategories,
    hasCKD: containsAny(conditionNames, CKD_KEYWORDS),
    hasLiverDisease: containsAny(conditionNames, LIVER_KEYWORDS),
    hasCOPD: containsAny(conditionNames, COPD_KEYWORDS),
    hasAsthma: containsAny(conditionNames, ASTHMA_KEYWORDS),
    hasDiabetes: containsAny(conditionNames, DIABETES_KEYWORDS),
    hasHeartFailure: containsAny(conditionNames, HF_KEYWORDS),
    hasHypertension: containsAny(conditionNames, HTN_KEYWORDS),
    isOnAnticoagulants: containsAny(medNames, ANTICOAGULANT_KEYWORDS),
    isOnBetaBlockers: containsAny(medNames, BETA_BLOCKER_KEYWORDS),
    isOnACEInhibitors: containsAny(medNames, ACE_INHIBITOR_KEYWORDS),
    hasNSAIDAllergy: containsAny(allergyNames, NSAID_KEYWORDS),
    hasPropololAllergy: containsAny(allergyNames, ['propofol']),
    hasSuccinylcholineContraindication: containsAny(conditionNames, ['hyperkalemia', 'burn', 'crush', 'neuromuscular', 'malignant hyperthermia', 'myasthenia', 'guillain']),
    isImmunocompromised: containsAny(conditionNames, IMMUNOCOMPROMISED_KEYWORDS),
    hasGIBleedHistory: containsAny(conditionNames, GI_BLEED_KEYWORDS),
  }
}

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

// ─── Vital Configuration ─────────────────────────────────────────────────────

interface VitalConfig {
  key: string
  label: string
  unit: string
  icon: React.ElementType
  color: string
  chartColor: string
  min: number
  max: number
  normalLow: number
  normalHigh: number
  step: number
  defaultBaseline: number
}

const VITAL_CONFIGS: VitalConfig[] = [
  { key: 'heartRate', label: 'Heart Rate', unit: 'bpm', icon: Heart, color: 'text-danger-500', chartColor: '#e11d48', min: 30, max: 200, normalLow: 60, normalHigh: 100, step: 1, defaultBaseline: 75 },
  { key: 'systolicBP', label: 'Systolic BP', unit: 'mmHg', icon: Activity, color: 'text-primary-500', chartColor: '#3b82f6', min: 60, max: 250, normalLow: 90, normalHigh: 140, step: 1, defaultBaseline: 125 },
  { key: 'diastolicBP', label: 'Diastolic BP', unit: 'mmHg', icon: Activity, color: 'text-indigo-500', chartColor: '#6366f1', min: 40, max: 150, normalLow: 60, normalHigh: 90, step: 1, defaultBaseline: 80 },
  { key: 'spo2', label: 'SpO2', unit: '%', icon: Droplets, color: 'text-sky-500', chartColor: '#0ea5e9', min: 70, max: 100, normalLow: 95, normalHigh: 100, step: 1, defaultBaseline: 97 },
  { key: 'temperature', label: 'Temperature', unit: '°F', icon: Thermometer, color: 'text-orange-500', chartColor: '#f97316', min: 95, max: 106, normalLow: 97.8, normalHigh: 99.1, step: 0.1, defaultBaseline: 98.6 },
  { key: 'respRate', label: 'Respiratory Rate', unit: 'br/min', icon: Wind, color: 'text-teal-500', chartColor: '#14b8a6', min: 6, max: 40, normalLow: 12, normalHigh: 20, step: 1, defaultBaseline: 16 },
  { key: 'glucose', label: 'Blood Glucose', unit: 'mg/dL', icon: Droplets, color: 'text-purple-500', chartColor: '#8b5cf6', min: 30, max: 500, normalLow: 70, normalHigh: 140, step: 1, defaultBaseline: 110 },
]

// ─── Simulation Profiles ─────────────────────────────────────────────────────

interface SimulationProfile {
  name: string
  description: string
  overrides: Record<string, { baseline: number; variability: number; anomalyChance: number }>
}

const PROFILES: SimulationProfile[] = [
  {
    name: 'Healthy Patient',
    description: 'Normal vital ranges with minimal variability',
    overrides: {
      heartRate: { baseline: 72, variability: 5, anomalyChance: 0 },
      systolicBP: { baseline: 118, variability: 6, anomalyChance: 0 },
      diastolicBP: { baseline: 76, variability: 4, anomalyChance: 0 },
      spo2: { baseline: 98, variability: 1, anomalyChance: 0 },
      temperature: { baseline: 98.6, variability: 0.3, anomalyChance: 0 },
      respRate: { baseline: 15, variability: 2, anomalyChance: 0 },
      glucose: { baseline: 100, variability: 12, anomalyChance: 0 },
    },
  },
  {
    name: 'Hypertensive Crisis',
    description: 'Dangerously elevated BP with tachycardia',
    overrides: {
      heartRate: { baseline: 110, variability: 8, anomalyChance: 0.3 },
      systolicBP: { baseline: 195, variability: 15, anomalyChance: 0.4 },
      diastolicBP: { baseline: 115, variability: 8, anomalyChance: 0.3 },
      spo2: { baseline: 94, variability: 2, anomalyChance: 0.2 },
      temperature: { baseline: 98.8, variability: 0.4, anomalyChance: 0 },
      respRate: { baseline: 22, variability: 3, anomalyChance: 0.1 },
      glucose: { baseline: 135, variability: 20, anomalyChance: 0.1 },
    },
  },
  {
    name: 'Diabetic Emergency',
    description: 'Severe hyperglycemia with dehydration signs',
    overrides: {
      heartRate: { baseline: 105, variability: 10, anomalyChance: 0.2 },
      systolicBP: { baseline: 100, variability: 10, anomalyChance: 0.1 },
      diastolicBP: { baseline: 65, variability: 6, anomalyChance: 0.1 },
      spo2: { baseline: 96, variability: 2, anomalyChance: 0.1 },
      temperature: { baseline: 99.2, variability: 0.5, anomalyChance: 0.1 },
      respRate: { baseline: 24, variability: 4, anomalyChance: 0.2 },
      glucose: { baseline: 380, variability: 40, anomalyChance: 0.5 },
    },
  },
  {
    name: 'Respiratory Distress',
    description: 'Low SpO2, elevated respiratory rate, tachycardia',
    overrides: {
      heartRate: { baseline: 115, variability: 10, anomalyChance: 0.3 },
      systolicBP: { baseline: 135, variability: 10, anomalyChance: 0.1 },
      diastolicBP: { baseline: 85, variability: 5, anomalyChance: 0.1 },
      spo2: { baseline: 88, variability: 3, anomalyChance: 0.4 },
      temperature: { baseline: 100.4, variability: 0.6, anomalyChance: 0.2 },
      respRate: { baseline: 30, variability: 5, anomalyChance: 0.3 },
      glucose: { baseline: 120, variability: 15, anomalyChance: 0 },
    },
  },
  {
    name: 'Sepsis Onset',
    description: 'Fever, tachycardia, hypotension, elevated respiratory rate',
    overrides: {
      heartRate: { baseline: 120, variability: 12, anomalyChance: 0.3 },
      systolicBP: { baseline: 88, variability: 12, anomalyChance: 0.3 },
      diastolicBP: { baseline: 55, variability: 8, anomalyChance: 0.3 },
      spo2: { baseline: 92, variability: 3, anomalyChance: 0.3 },
      temperature: { baseline: 102.8, variability: 0.8, anomalyChance: 0.2 },
      respRate: { baseline: 28, variability: 5, anomalyChance: 0.3 },
      glucose: { baseline: 165, variability: 30, anomalyChance: 0.2 },
    },
  },
  {
    name: 'Bradycardia Event',
    description: 'Dangerously low heart rate with normal other vitals',
    overrides: {
      heartRate: { baseline: 42, variability: 6, anomalyChance: 0.4 },
      systolicBP: { baseline: 95, variability: 8, anomalyChance: 0.1 },
      diastolicBP: { baseline: 60, variability: 5, anomalyChance: 0.1 },
      spo2: { baseline: 95, variability: 2, anomalyChance: 0.1 },
      temperature: { baseline: 97.5, variability: 0.4, anomalyChance: 0 },
      respRate: { baseline: 14, variability: 2, anomalyChance: 0 },
      glucose: { baseline: 105, variability: 10, anomalyChance: 0 },
    },
  },
]

// ─── Simulation Engine ───────────────────────────────────────────────────────

interface VitalParams {
  baseline: number
  variability: number
  anomalyChance: number
}

interface GeneratedReading {
  timestamp: string
  values: Record<string, number>
  alerts: string[]
}

function generateReading(
  params: Record<string, VitalParams>,
  timeLabel: string,
): GeneratedReading {
  const values: Record<string, number> = {}
  const alerts: string[] = []

  for (const config of VITAL_CONFIGS) {
    const p = params[config.key]
    if (!p) continue

    // Gaussian-ish noise using Box-Muller (clamp u1 away from 0 to avoid -Infinity from log)
    const u1 = Math.max(1e-10, Math.random())
    const u2 = Math.random()
    const gaussian = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2)

    let value = p.baseline + gaussian * p.variability

    // Anomaly spike
    if (Math.random() < p.anomalyChance) {
      const direction = Math.random() > 0.5 ? 1 : -1
      value += direction * p.variability * 2.5
    }

    // Clamp to vital range
    value = Math.max(config.min, Math.min(config.max, value))

    // Round appropriately
    value = config.step < 1
      ? Math.round(value * 10) / 10
      : Math.round(value)

    values[config.key] = value

    // Check thresholds
    if (value > config.normalHigh) {
      alerts.push(`${config.label}: ${value} ${config.unit} (HIGH)`)
    } else if (value < config.normalLow) {
      alerts.push(`${config.label}: ${value} ${config.unit} (LOW)`)
    }
  }

  return { timestamp: timeLabel, values, alerts }
}

// ─── AI Recommendation Types ────────────────────────────────────────────────

interface AIRecommendation {
  id: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  description: string
  agent: string
  timestamp: string
  icdCode?: string
  icdDisplay?: string
  cptCodes?: { code: string; display: string }[]
  treatment?: string
  contraindications?: string[]    // Patient-specific safety warnings
  patientFactors?: string[]       // Relevant patient factors that influenced the recommendation
}

/**
 * Generate patient-aware clinical recommendations based on vitals AND patient context.
 *
 * When patient context is available, recommendations are personalized:
 * - Drug contraindications are checked against conditions, medications, and allergies
 * - Dosing is adjusted for renal/hepatic impairment
 * - Alternative agents are suggested when first-line is contraindicated
 * - Relevant patient factors are surfaced alongside each recommendation
 */
function generateLocalRecommendations(
  readings: GeneratedReading[],
  ctx: PatientClinicalContext | null,
): AIRecommendation[] {
  const recs: AIRecommendation[] = []
  if (readings.length === 0) return recs

  const latest = readings[readings.length - 1]
  const v = latest.values
  let id = 0

  // ── Heart Rate ──────────────────────────────────────────────────────────────

  if (v.heartRate > 120) {
    const contraindications: string[] = []
    const patientFactors: string[] = []
    let treatment: string

    if (ctx?.isOnBetaBlockers) {
      patientFactors.push(`Already on beta-blocker (${ctx.medications.filter((m) => containsAny([m], BETA_BLOCKER_KEYWORDS)).join(', ')})`)
      contraindications.push('CAUTION: Patient already on beta-blocker — additional IV Metoprolol may cause severe bradycardia/hypotension')
      treatment = 'Assess current beta-blocker compliance before additional dosing. Consider IV Diltiazem 0.25mg/kg over 2min if rate control needed. Continuous telemetry. Fluid resuscitation if hypovolemic.'
    } else if (ctx?.hasHeartFailure) {
      patientFactors.push('History of heart failure')
      treatment = 'IV Amiodarone 150mg over 10min (preferred in HF). Avoid Metoprolol bolus in acute decompensated HF. Continuous telemetry monitoring, fluid resuscitation if hypovolemic.'
    } else {
      treatment = 'IV Metoprolol 5mg q5min (max 15mg), continuous telemetry monitoring, fluid resuscitation if hypovolemic.'
    }
    if (ctx?.hasAsthma || ctx?.hasCOPD) {
      contraindications.push('CONTRAINDICATED: Non-selective beta-blockers in asthma/COPD — use IV Diltiazem or Amiodarone instead')
      patientFactors.push(ctx.hasCOPD ? 'History of COPD' : 'History of asthma')
      treatment = 'IV Diltiazem 0.25mg/kg over 2min (beta-blockers contraindicated in reactive airway disease). Continuous telemetry. Fluid resuscitation if hypovolemic.'
    }

    recs.push({
      id: String(++id), severity: 'critical', title: 'Severe Tachycardia Detected',
      description: `Heart rate at ${v.heartRate} bpm. Consider immediate evaluation for arrhythmia, sepsis, or hypovolemia. 12-lead ECG recommended.`,
      agent: 'Cardiac Monitor Agent', timestamp: latest.timestamp,
      icdCode: 'R00.0', icdDisplay: 'Tachycardia, unspecified',
      cptCodes: [{ code: '93000', display: '12-lead ECG with interpretation' }, { code: '93040', display: 'Rhythm ECG (1-3 leads)' }, { code: '99291', display: 'Critical care, first 30-74 min' }],
      treatment, contraindications, patientFactors,
    })
  } else if (v.heartRate > 100) {
    const contraindications: string[] = []
    const patientFactors: string[] = []
    let treatment = 'PO Metoprolol 25-50mg BID, address underlying cause (hydration, pain management, antipyretics).'
    if (ctx?.hasAsthma || ctx?.hasCOPD) {
      contraindications.push('CONTRAINDICATED: Non-selective beta-blockers in asthma/COPD — consider Diltiazem 120-240mg daily')
      patientFactors.push(ctx.hasCOPD ? 'COPD' : 'Asthma')
      treatment = 'PO Diltiazem ER 120-240mg daily (beta-blockers contraindicated). Address underlying cause (hydration, pain management, antipyretics).'
    }
    if (ctx?.isOnBetaBlockers) {
      patientFactors.push('Already on beta-blocker')
      treatment = 'Assess adherence to current beta-blocker before adding new rate-control agents. Address underlying cause.'
    }

    recs.push({
      id: String(++id), severity: 'warning', title: 'Tachycardia Alert',
      description: `Heart rate elevated at ${v.heartRate} bpm. Assess for pain, anxiety, fever, dehydration, or medication effects.`,
      agent: 'Cardiac Monitor Agent', timestamp: latest.timestamp,
      icdCode: 'R00.0', icdDisplay: 'Tachycardia, unspecified',
      cptCodes: [{ code: '93000', display: '12-lead ECG with interpretation' }, { code: '93005', display: 'ECG tracing only' }],
      treatment, contraindications, patientFactors,
    })
  } else if (v.heartRate < 50) {
    const patientFactors: string[] = []
    let treatment = 'Atropine 1mg IV q3-5min (max 3mg), transcutaneous pacing if unresponsive, hold beta-blockers/CCBs.'
    if (ctx?.isOnBetaBlockers) {
      patientFactors.push(`On beta-blocker (${ctx.medications.filter((m) => containsAny([m], BETA_BLOCKER_KEYWORDS)).join(', ')}) — likely contributing to bradycardia`)
      treatment = `HOLD current beta-blocker. Atropine 1mg IV q3-5min (max 3mg). Transcutaneous pacing if unresponsive. Current beta-blocker: ${ctx.medications.filter((m) => containsAny([m], BETA_BLOCKER_KEYWORDS)).join(', ')}.`
    }

    recs.push({
      id: String(++id), severity: 'critical', title: 'Severe Bradycardia',
      description: `Heart rate critically low at ${v.heartRate} bpm. Check for heart block, medication effects (beta-blockers), or vagal response. Prepare for possible transcutaneous pacing.`,
      agent: 'Cardiac Monitor Agent', timestamp: latest.timestamp,
      icdCode: 'R00.1', icdDisplay: 'Bradycardia, unspecified',
      cptCodes: [{ code: '93000', display: '12-lead ECG with interpretation' }, { code: '33210', display: 'Temporary transvenous pacemaker insertion' }, { code: '99291', display: 'Critical care, first 30-74 min' }],
      treatment, patientFactors,
    })
  }

  // ── Blood Pressure ─────────────────────────────────────────────────────────

  if (v.systolicBP > 180 || v.diastolicBP > 120) {
    const patientFactors: string[] = []
    const contraindications: string[] = []
    let treatment = 'IV Nicardipine 5mg/hr (titrate 2.5mg/hr q5min, max 15mg/hr) or IV Labetalol 20mg bolus then 2mg/min drip. Target 25% MAP reduction in 1hr.'
    if (ctx?.hasHeartFailure) {
      patientFactors.push('Heart failure — prefer Nicardipine or Nitroprusside, avoid Labetalol in acute decompensation')
      treatment = 'IV Nicardipine 5mg/hr (titrate 2.5mg/hr q5min, max 15mg/hr). Avoid Labetalol in acute decompensated HF. IV Nitroglycerin 5-20mcg/min if pulmonary edema. Target 25% MAP reduction in 1hr.'
    }
    if (ctx?.hasAsthma || ctx?.hasCOPD) {
      contraindications.push('CONTRAINDICATED: IV Labetalol (non-selective beta-blocker) in asthma/COPD')
      patientFactors.push(ctx.hasCOPD ? 'COPD' : 'Asthma')
      treatment = 'IV Nicardipine 5mg/hr (titrate 2.5mg/hr q5min, max 15mg/hr). Labetalol CONTRAINDICATED (reactive airway disease). Target 25% MAP reduction in 1hr.'
    }
    if (ctx?.hasCKD) {
      patientFactors.push('CKD — monitor renal function closely, adjust Nicardipine if needed')
    }

    recs.push({
      id: String(++id), severity: 'critical', title: 'Hypertensive Emergency',
      description: `BP ${v.systolicBP}/${v.diastolicBP} mmHg. Assess for end-organ damage. Consider IV antihypertensives. Target 25% reduction in first hour.`,
      agent: 'BP Management Agent', timestamp: latest.timestamp,
      icdCode: 'I16.1', icdDisplay: 'Hypertensive emergency',
      cptCodes: [{ code: '99291', display: 'Critical care, first 30-74 min' }, { code: '36000', display: 'IV access for drug administration' }, { code: '93000', display: '12-lead ECG with interpretation' }],
      treatment, contraindications, patientFactors,
    })
  } else if (v.systolicBP > 160 || v.diastolicBP > 100) {
    const patientFactors: string[] = []
    const contraindications: string[] = []
    let treatment = 'Lisinopril 10-20mg daily or Amlodipine 5-10mg daily. Add HCTZ 12.5-25mg if on monotherapy. Recheck BP in 2-4 weeks.'
    if (ctx?.hasCKD) {
      patientFactors.push('CKD — ACE inhibitors/ARBs preferred for renoprotection (per KDIGO 2024), monitor K+ and Cr')
      contraindications.push('CAUTION: HCTZ less effective with eGFR < 30; consider loop diuretic (Furosemide 20-40mg) instead')
      treatment = 'Lisinopril 10-20mg daily (renoprotective per KDIGO 2024). Monitor K+ and Cr at 1-2 weeks. If eGFR < 30: Furosemide 20-40mg daily instead of HCTZ. Recheck BP in 2-4 weeks.'
    }
    if (ctx?.hasDiabetes) {
      patientFactors.push('Diabetes — ACE inhibitor preferred (ADA 2024: renoprotection in diabetic nephropathy)')
    }
    if (ctx?.isOnACEInhibitors) {
      patientFactors.push(`Already on ACE inhibitor (${ctx.medications.filter((m) => containsAny([m], ACE_INHIBITOR_KEYWORDS)).join(', ')})`)
      treatment = `Assess adherence to current ACE inhibitor. Consider adding Amlodipine 5-10mg daily as second agent. ${ctx.hasCKD ? 'Furosemide 20-40mg if volume overloaded.' : 'Add HCTZ 12.5-25mg if needed.'} Recheck BP in 2-4 weeks.`
    }

    recs.push({
      id: String(++id), severity: 'warning', title: 'Hypertension Stage 2',
      description: `BP ${v.systolicBP}/${v.diastolicBP} mmHg. Review current antihypertensive regimen. Consider dose adjustment or adding second agent.`,
      agent: 'BP Management Agent', timestamp: latest.timestamp,
      icdCode: 'I10', icdDisplay: 'Essential (primary) hypertension',
      cptCodes: [{ code: '99214', display: 'Office visit, moderate complexity' }, { code: '93000', display: '12-lead ECG with interpretation' }],
      treatment, contraindications, patientFactors,
    })
  } else if (v.systolicBP < 90) {
    const patientFactors: string[] = []
    if (ctx?.isOnACEInhibitors || ctx?.isOnBetaBlockers) {
      const culprits = [
        ...(ctx.isOnACEInhibitors ? ctx.medications.filter((m) => containsAny([m], ACE_INHIBITOR_KEYWORDS)) : []),
        ...(ctx.isOnBetaBlockers ? ctx.medications.filter((m) => containsAny([m], BETA_BLOCKER_KEYWORDS)) : []),
      ]
      patientFactors.push(`Currently on antihypertensives (${culprits.join(', ')}) — HOLD these medications`)
    }
    if (ctx?.hasHeartFailure) {
      patientFactors.push('Heart failure — cautious fluid resuscitation, risk of pulmonary edema')
    }

    recs.push({
      id: String(++id), severity: 'critical', title: 'Hypotension Alert',
      description: `Systolic BP at ${v.systolicBP} mmHg. Assess for shock, dehydration, or sepsis. Consider fluid resuscitation.`,
      agent: 'BP Management Agent', timestamp: latest.timestamp,
      icdCode: 'I95.9', icdDisplay: 'Hypotension, unspecified',
      cptCodes: [{ code: '99291', display: 'Critical care, first 30-74 min' }, { code: '36000', display: 'IV access for drug administration' }, { code: '96360', display: 'IV infusion, hydration (first 31-60 min)' }],
      treatment: ctx?.hasHeartFailure
        ? 'NS 250mL IV bolus (cautious — HF patient, risk of pulmonary edema). Reassess after each 250mL. Norepinephrine 0.1-0.5mcg/kg/min if unresponsive. HOLD antihypertensives.'
        : 'NS bolus 500-1000mL IV, Trendelenburg position, Norepinephrine 0.1-0.5mcg/kg/min if unresponsive to fluids.' + (ctx?.isOnACEInhibitors || ctx?.isOnBetaBlockers ? ' HOLD current antihypertensives.' : ''),
      patientFactors,
    })
  }

  // ── SpO2 ────────────────────────────────────────────────────────────────────

  if (v.spo2 < 90) {
    const contraindications: string[] = []
    const patientFactors: string[] = []

    // Build personalized RSI recommendation
    let rsiDrugs = 'RSI if needed: '
    if (ctx?.hasPropololAllergy) {
      contraindications.push('ALLERGY: Propofol — use Ketamine 1-2mg/kg IV instead')
      rsiDrugs += 'Ketamine 1-2mg/kg IV'
    } else if (v.systolicBP < 100) {
      contraindications.push('CAUTION: Propofol causes hypotension — patient is already hypotensive. Use Ketamine 1-2mg/kg IV instead')
      rsiDrugs += 'Ketamine 1-2mg/kg IV (Propofol avoided due to hypotension)'
    } else {
      rsiDrugs += 'Propofol 1.5mg/kg IV'
    }

    if (ctx?.hasSuccinylcholineContraindication) {
      contraindications.push('CONTRAINDICATED: Succinylcholine (risk of fatal hyperkalemia) — use Rocuronium 1.2mg/kg IV instead')
      patientFactors.push('Succinylcholine contraindication detected in patient history')
      rsiDrugs += ' + Rocuronium 1.2mg/kg IV'
    } else if (ctx?.hasCKD) {
      contraindications.push('CAUTION: Succinylcholine in CKD — risk of hyperkalemia. Prefer Rocuronium 1.2mg/kg IV')
      patientFactors.push('CKD — hyperkalemia risk with Succinylcholine')
      rsiDrugs += ' + Rocuronium 1.2mg/kg IV (preferred over Succinylcholine in CKD)'
    } else {
      rsiDrugs += ' + Succinylcholine 1.5mg/kg IV'
    }

    // Weight-based note
    if (ctx?.weight_kg) {
      rsiDrugs += ` (patient weight: ${ctx.weight_kg}kg)`
    }

    // SpO2 target for COPD
    let o2Target = 'SpO2 > 94%'
    if (ctx?.hasCOPD) {
      patientFactors.push('COPD — target SpO2 88-92% to avoid CO2 retention (GOLD 2024)')
      o2Target = 'SpO2 88-92% (COPD — avoid O2-induced hypercapnia per GOLD 2024)'
    }

    const treatment = `High-flow O2 via non-rebreather mask 15L/min, target ${o2Target}. Prepare for intubation if not improving. ${rsiDrugs}.`

    recs.push({
      id: String(++id), severity: 'critical', title: 'Severe Hypoxemia',
      description: `SpO2 at ${v.spo2}%. Initiate supplemental O2 immediately. Consider ABG, CXR, and possible intubation if not improving.`,
      agent: 'Respiratory Agent', timestamp: latest.timestamp,
      icdCode: 'J96.01', icdDisplay: 'Acute respiratory failure with hypoxia',
      cptCodes: [{ code: '94760', display: 'Pulse oximetry (continuous)' }, { code: '71046', display: 'Chest X-ray, 2 views' }, { code: '82803', display: 'Arterial blood gas (ABG)' }, { code: '31500', display: 'Emergency endotracheal intubation' }],
      treatment, contraindications, patientFactors,
    })
  } else if (v.spo2 < 94) {
    const patientFactors: string[] = []
    let treatment = 'Nasal cannula O2 2-4L/min, titrate to SpO2 > 94%. Obtain ABG if not improving.'
    if (ctx?.hasCOPD) {
      patientFactors.push('COPD — target SpO2 88-92% (GOLD 2024), risk of CO2 narcosis with high-flow O2')
      treatment = 'Nasal cannula O2 1-2L/min, target SpO2 88-92% (COPD per GOLD 2024). Avoid high-flow O2 — risk of CO2 retention. Obtain ABG to assess PaCO2.'
    }

    recs.push({
      id: String(++id), severity: 'warning', title: 'Desaturation Warning',
      description: `SpO2 at ${v.spo2}%. Apply supplemental O2 via nasal cannula. Monitor closely and consider ABG.`,
      agent: 'Respiratory Agent', timestamp: latest.timestamp,
      icdCode: 'R09.02', icdDisplay: 'Hypoxemia',
      cptCodes: [{ code: '94760', display: 'Pulse oximetry (continuous)' }, { code: '82803', display: 'Arterial blood gas (ABG)' }, { code: '71046', display: 'Chest X-ray, 2 views' }],
      treatment, patientFactors,
    })
  }

  // ── Glucose ─────────────────────────────────────────────────────────────────

  if (v.glucose > 300) {
    const patientFactors: string[] = []
    if (ctx?.hasDiabetes) patientFactors.push('Known diabetic — check medication adherence and recent changes')
    if (ctx?.hasCKD) patientFactors.push('CKD — monitor potassium closely during insulin therapy, adjust fluid rate')

    recs.push({
      id: String(++id), severity: 'critical', title: 'Severe Hyperglycemia',
      description: `Blood glucose at ${v.glucose} mg/dL. Check for DKA (ketones, anion gap). Start insulin protocol and IV fluids. Monitor q1h.`,
      agent: 'Glycemic Control Agent', timestamp: latest.timestamp,
      icdCode: 'E11.65', icdDisplay: 'Type 2 DM with hyperglycemia',
      cptCodes: [{ code: '82947', display: 'Blood glucose quantitative' }, { code: '82570', display: 'Urine creatinine' }, { code: '80048', display: 'Basic metabolic panel (BMP)' }, { code: '96360', display: 'IV infusion, hydration' }],
      treatment: ctx?.hasCKD
        ? 'Insulin IV drip 0.1 units/kg/hr. NS 500mL/hr (reduced rate for CKD). Check BMP, ketones, anion gap. Monitor BG q1h, K+ q2h. Replace K+ if < 5.3 mEq/L (cautious in CKD).'
        : 'Insulin IV drip 0.1 units/kg/hr, NS 1L/hr x 2hr then 250mL/hr. Check BMP, ketones, anion gap. Monitor BG q1h. Replace K+ if < 5.3 mEq/L.',
      patientFactors,
    })
  } else if (v.glucose > 200) {
    const patientFactors: string[] = []
    if (ctx?.hasDiabetes) patientFactors.push('Known diabetic — review current insulin regimen and adherence')

    recs.push({
      id: String(++id), severity: 'warning', title: 'Hyperglycemia Alert',
      description: `Blood glucose elevated at ${v.glucose} mg/dL. Administer correction dose per sliding scale. Reassess in 2 hours.`,
      agent: 'Glycemic Control Agent', timestamp: latest.timestamp,
      icdCode: 'R73.9', icdDisplay: 'Hyperglycemia, unspecified',
      cptCodes: [{ code: '82947', display: 'Blood glucose quantitative' }, { code: '83036', display: 'Hemoglobin A1c (HbA1c)' }],
      treatment: 'Rapid-acting insulin per sliding scale (Lispro/Aspart). BG 201-250: 2U, 251-300: 4U, 301-350: 6U. Reassess in 2hr.',
      patientFactors,
    })
  } else if (v.glucose < 70) {
    const patientFactors: string[] = []
    if (ctx?.hasDiabetes) patientFactors.push('Known diabetic — review insulin/sulfonylurea dosing for dose reduction')

    recs.push({
      id: String(++id), severity: 'critical', title: 'Hypoglycemia Detected',
      description: `Blood glucose critically low at ${v.glucose} mg/dL. Administer 15g fast-acting carbohydrate. If NPO or unconscious, give IV dextrose 50%.`,
      agent: 'Glycemic Control Agent', timestamp: latest.timestamp,
      icdCode: 'E16.2', icdDisplay: 'Hypoglycemia, unspecified',
      cptCodes: [{ code: '82947', display: 'Blood glucose quantitative' }, { code: '96374', display: 'IV push, single drug' }, { code: '80048', display: 'Basic metabolic panel (BMP)' }],
      treatment: 'If conscious: 15g oral glucose (4oz juice), recheck in 15min. If unconscious/NPO: D50W 25mL (12.5g) IV push or Glucagon 1mg IM. Hold insulin/sulfonylureas.',
      patientFactors,
    })
  }

  // ── Temperature ─────────────────────────────────────────────────────────────

  if (v.temperature > 102) {
    const patientFactors: string[] = []
    const contraindications: string[] = []
    let treatment = 'Acetaminophen 1000mg IV/PO q6h, blood cultures x2 from separate sites, empiric Vancomycin 25mg/kg IV + Piperacillin-Tazobactam 4.5g IV q6h.'
    if (ctx?.hasCKD) {
      patientFactors.push('CKD — adjust antibiotic dosing for renal function')
      treatment = 'Acetaminophen 1000mg IV/PO q6h, blood cultures x2 from separate sites, empiric Vancomycin (dose per trough, renal-adjusted) + Piperacillin-Tazobactam 3.375g IV q8h (CKD-adjusted). Monitor drug levels.'
    }
    if (ctx?.hasLiverDisease) {
      contraindications.push('CAUTION: Acetaminophen max 2g/day in liver disease (hepatotoxicity risk)')
      patientFactors.push('Liver disease — reduce acetaminophen max daily dose to 2g')
      treatment = treatment.replace('1000mg', '500mg') + ' MAX Acetaminophen 2g/day (liver disease).'
    }
    if (ctx?.isImmunocompromised) {
      patientFactors.push('Immunocompromised — broader antimicrobial coverage warranted, consider fungal coverage')
    }

    recs.push({
      id: String(++id), severity: 'critical', title: 'High Fever',
      description: `Temperature ${v.temperature}°F. Obtain blood cultures x2, CBC, lactate. Consider empiric antibiotics. Sepsis screening recommended.`,
      agent: 'Infection Control Agent', timestamp: latest.timestamp,
      icdCode: 'R50.9', icdDisplay: 'Fever, unspecified',
      cptCodes: [{ code: '87040', display: 'Blood culture, aerobic' }, { code: '85025', display: 'CBC with differential' }, { code: '83605', display: 'Lactic acid (lactate)' }, { code: '71046', display: 'Chest X-ray, 2 views' }],
      treatment, contraindications, patientFactors,
    })
  } else if (v.temperature > 100.4) {
    const contraindications: string[] = []
    const patientFactors: string[] = []

    // Build antipyretic recommendation based on patient factors
    let antipyretic = 'Acetaminophen 650-1000mg PO q6h'
    const alternatives: string[] = []

    if (ctx?.hasLiverDisease) {
      contraindications.push('CAUTION: Acetaminophen max 2g/day in liver disease')
      patientFactors.push('Liver disease')
      antipyretic = 'Acetaminophen 500mg PO q6h (max 2g/day due to liver disease)'
    }

    // NSAID contraindication checks
    const nsaidContraindicated = ctx?.hasCKD || ctx?.isOnAnticoagulants || ctx?.hasGIBleedHistory || ctx?.hasNSAIDAllergy || ctx?.hasHeartFailure
    if (nsaidContraindicated) {
      const reasons: string[] = []
      if (ctx?.hasCKD) reasons.push('CKD (nephrotoxic)')
      if (ctx?.isOnAnticoagulants) reasons.push(`on anticoagulant (${ctx.medications.filter((m) => containsAny([m], ANTICOAGULANT_KEYWORDS)).join(', ')}) — bleeding risk`)
      if (ctx?.hasGIBleedHistory) reasons.push('GI bleed history')
      if (ctx?.hasNSAIDAllergy) reasons.push('NSAID allergy')
      if (ctx?.hasHeartFailure) reasons.push('heart failure (fluid retention)')
      contraindications.push(`CONTRAINDICATED: Ibuprofen/NSAIDs — ${reasons.join('; ')}`)
      patientFactors.push(...reasons)
    } else {
      alternatives.push('Ibuprofen 400-600mg PO q6h')
    }

    const treatment = alternatives.length > 0
      ? `${antipyretic} or ${alternatives.join(' or ')}. Obtain UA, CBC, CXR if new onset. Cooling measures PRN.`
      : `${antipyretic} (NSAIDs contraindicated for this patient). Obtain UA, CBC, CXR if new onset. Cooling measures PRN.`

    recs.push({
      id: String(++id), severity: 'warning', title: 'Fever Detected',
      description: `Temperature ${v.temperature}°F. Administer antipyretics. Evaluate for infection source. Consider UA, CXR if new onset.`,
      agent: 'Infection Control Agent', timestamp: latest.timestamp,
      icdCode: 'R50.9', icdDisplay: 'Fever, unspecified',
      cptCodes: [{ code: '85025', display: 'CBC with differential' }, { code: '81001', display: 'Urinalysis, automated with micro' }, { code: '71046', display: 'Chest X-ray, 2 views' }],
      treatment, contraindications, patientFactors,
    })
  }

  // ── Respiratory Rate ────────────────────────────────────────────────────────

  if (v.respRate > 28) {
    const patientFactors: string[] = []
    if (ctx?.hasCOPD) patientFactors.push('COPD — may have chronically elevated baseline RR')
    if (ctx?.hasHeartFailure) patientFactors.push('Heart failure — assess for pulmonary edema')

    recs.push({
      id: String(++id), severity: 'critical', title: 'Tachypnea — Respiratory Failure Risk',
      description: `Respiratory rate at ${v.respRate} br/min. Assess for respiratory distress, metabolic acidosis, or anxiety. ABG recommended.`,
      agent: 'Respiratory Agent', timestamp: latest.timestamp,
      icdCode: 'R06.82', icdDisplay: 'Tachypnea, not elsewhere classified',
      cptCodes: [{ code: '82803', display: 'Arterial blood gas (ABG)' }, { code: '94760', display: 'Pulse oximetry (continuous)' }, { code: '71046', display: 'Chest X-ray, 2 views' }, { code: '99291', display: 'Critical care, first 30-74 min' }],
      treatment: ctx?.hasHeartFailure
        ? 'Supplemental O2, obtain ABG stat. Assess for pulmonary edema (CXR, BNP). IV Furosemide 40mg if volume overloaded. BiPAP if hypoxic. Intubation if worsening.'
        : 'Supplemental O2, obtain ABG stat. If metabolic acidosis: identify and treat cause. If respiratory failure: consider BiPAP or intubation.',
      patientFactors,
    })
  } else if (v.respRate > 22) {
    const patientFactors: string[] = []
    const contraindications: string[] = []
    let treatment = 'Continuous pulse oximetry, address underlying cause. Pain management if pain-related.'

    // CRITICAL FIX: Do NOT recommend anxiolytics if patient is hypoxic
    if (v.spo2 < 92) {
      contraindications.push('CONTRAINDICATED: Anxiolytics/benzodiazepines — patient is hypoxic (SpO2 ' + v.spo2 + '%), respiratory depressants will worsen hypoxemia')
      patientFactors.push('Concurrent hypoxemia — tachypnea is likely compensatory, do NOT suppress respiratory drive')
      treatment = 'Continuous pulse oximetry. DO NOT administer anxiolytics/sedatives — tachypnea is likely compensatory for hypoxemia. Address underlying cause of desaturation first.'
    }
    if (ctx?.hasCOPD) patientFactors.push('COPD — may have chronically elevated baseline')

    recs.push({
      id: String(++id), severity: 'warning', title: 'Elevated Respiratory Rate',
      description: `Respiratory rate at ${v.respRate} br/min. Monitor closely. Assess for pain, fever, or anxiety as contributing factors.`,
      agent: 'Respiratory Agent', timestamp: latest.timestamp,
      icdCode: 'R06.82', icdDisplay: 'Tachypnea, not elsewhere classified',
      cptCodes: [{ code: '94760', display: 'Pulse oximetry (continuous)' }, { code: '71046', display: 'Chest X-ray, 2 views' }],
      treatment, contraindications, patientFactors,
    })
  }

  // ── Multi-vital: SIRS/Sepsis ────────────────────────────────────────────────

  if (v.heartRate > 100 && v.systolicBP < 100 && v.temperature > 100.4 && v.respRate > 22) {
    const patientFactors: string[] = []
    if (ctx?.isImmunocompromised) patientFactors.push('Immunocompromised — atypical infections possible, broader coverage needed')
    if (ctx?.hasCKD) patientFactors.push('CKD — adjust fluid bolus volume and antibiotic dosing for renal function')
    if (ctx?.hasHeartFailure) patientFactors.push('Heart failure — cautious with 30mL/kg fluid bolus, reassess after each 250-500mL')

    const fluidRec = ctx?.hasHeartFailure
      ? 'NS 250-500mL IV bolus, reassess after each bolus (HF — risk of pulmonary edema)'
      : 'NS 30mL/kg IV bolus within 3hr'
    const abxRec = ctx?.hasCKD
      ? 'Broad-spectrum ABX within 1hr (renal-adjusted): Vancomycin (trough-guided) + Pip-Tazo 3.375g IV q8h'
      : 'Broad-spectrum ABX within 1hr (Vanc + Zosyn)'

    recs.push({
      id: String(++id), severity: 'critical', title: 'SIRS/Sepsis Criteria Met',
      description: `Multiple abnormalities: HR ${v.heartRate}, BP ${v.systolicBP}/${v.diastolicBP}, Temp ${v.temperature}°F, RR ${v.respRate}. Activate sepsis bundle: cultures, lactate, IV fluids, broad-spectrum antibiotics within 1 hour.`,
      agent: 'Sepsis Screening Agent', timestamp: latest.timestamp,
      icdCode: 'A41.9', icdDisplay: 'Sepsis, unspecified organism',
      cptCodes: [{ code: '99291', display: 'Critical care, first 30-74 min' }, { code: '87040', display: 'Blood culture, aerobic' }, { code: '83605', display: 'Lactic acid (lactate)' }, { code: '36000', display: 'IV access for drug administration' }, { code: '96360', display: 'IV infusion, hydration' }],
      treatment: `SEP-1 Bundle: Blood cultures x2, Lactate level, ${fluidRec}, ${abxRec}. Repeat lactate if > 2. Vasopressors if MAP < 65 after fluids.`,
      patientFactors,
    })
  }

  // ── Normal ──────────────────────────────────────────────────────────────────

  if (recs.length === 0) {
    recs.push({
      id: '0', severity: 'info', title: 'All Vitals Within Normal Range',
      description: 'No abnormalities detected. Continue routine monitoring per care plan.',
      agent: 'Clinical Decision Support', timestamp: latest.timestamp,
      icdCode: 'Z00.00', icdDisplay: 'General adult medical examination',
      cptCodes: [{ code: '99213', display: 'Office visit, low complexity' }],
      treatment: 'Continue current care plan. Next routine vitals check per protocol.',
      patientFactors: ctx ? [`${ctx.name}: ${ctx.conditions.length} active conditions, ${ctx.medications.length} medications`] : [],
    })
  }

  return recs
}

// ─── Component ───────────────────────────────────────────────────────────────

interface Patient {
  id: string
  name: string
}

export default function VitalsSimulatorPage() {
  const [selectedPatientId, setSelectedPatientId] = useState<string>('p1')
  const [selectedProfile, setSelectedProfile] = useState<number>(0)
  const [params, setParams] = useState<Record<string, VitalParams>>(() => {
    const p: Record<string, VitalParams> = {}
    for (const cfg of VITAL_CONFIGS) {
      p[cfg.key] = { baseline: cfg.defaultBaseline, variability: (cfg.normalHigh - cfg.normalLow) * 0.15, anomalyChance: 0.05 }
    }
    return p
  })
  const [readings, setReadings] = useState<GeneratedReading[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [intervalMs, setIntervalMs] = useState(2000)
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([])
  const [showConfig, setShowConfig] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const readingCountRef = useRef(0)
  const [allergies, setAllergies] = useState<FHIRAllergyIntolerance[]>([])

  // Static patient list (no backend dependency)
  const patients: Patient[] = [
    { id: 'p1', name: 'Maria Garcia' },
    { id: 'p2', name: 'James Wilson' },
    { id: 'p3', name: 'Susan Chen' },
    { id: 'p4', name: 'Robert Johnson' },
    { id: 'p5', name: 'Aisha Patel' },
  ]

  // ─── Fetch Patient Clinical Context ──────────────────────────────────────
  const { data: fhirPatient } = usePatient(selectedPatientId)
  const { data: conditionsResult } = useConditions(selectedPatientId, 'active')
  const { data: medicationsResult } = useMedications(selectedPatientId, 'active')

  // Fetch allergies (no dedicated hook, use service directly)
  useEffect(() => {
    if (!selectedPatientId) return
    fhirService.getAllergies(selectedPatientId)
      .then((result) => setAllergies(result.entry?.map((e) => e.resource as FHIRAllergyIntolerance) ?? []))
      .catch(() => setAllergies([]))
  }, [selectedPatientId])

  // Build patient clinical context from FHIR data
  const patientContext = useMemo<PatientClinicalContext | null>(() => {
    const patientName = patients.find((p) => p.id === selectedPatientId)?.name ?? selectedPatientId
    const conditions: FHIRCondition[] = conditionsResult?.entry?.map((e) => e.resource as FHIRCondition) ?? []
    const medications: FHIRMedicationRequest[] = medicationsResult?.entry?.map((e) => e.resource as FHIRMedicationRequest) ?? []

    return buildPatientContext(
      fhirPatient,
      conditions,
      medications,
      allergies,
      selectedPatientId,
      patientName,
    )
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fhirPatient, conditionsResult, medicationsResult, allergies, selectedPatientId])

  // Stable ref for patient context so tick callback always has latest
  const patientContextRef = useRef(patientContext)
  patientContextRef.current = patientContext

  // Refs for stable references in tick callback (avoids interval restart on every render)
  const paramsRef = useRef(params)
  paramsRef.current = params
  const intervalMsRef = useRef(intervalMs)
  intervalMsRef.current = intervalMs

  const tick = useCallback(() => {
    readingCountRef.current += 1
    const timeLabel = `T+${readingCountRef.current * (intervalMsRef.current / 1000)}s`
    const reading = generateReading(paramsRef.current, timeLabel)

    setReadings((prev) => {
      const next = [...prev, reading]
      const trimmed = next.length > 60 ? next.slice(-60) : next
      // Generate patient-aware AI recommendations from latest readings
      const recs = generateLocalRecommendations(trimmed, patientContextRef.current)
      // Use queueMicrotask to avoid setting state inside setState
      queueMicrotask(() => setRecommendations(recs))
      return trimmed
    })
  }, [])

  const startSimulation = () => {
    if (isRunning) return
    setIsRunning(true)
    readingCountRef.current = 0
    setReadings([])
    setRecommendations([])
    // Generate first reading immediately
    tick()
    timerRef.current = setInterval(tick, intervalMs)
  }

  const stopSimulation = () => {
    setIsRunning(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  // Restart interval when intervalMs changes during running
  useEffect(() => {
    if (isRunning && timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = setInterval(tick, intervalMs)
    }
  }, [intervalMs, tick, isRunning])

  const applyProfile = (index: number) => {
    setSelectedProfile(index)
    const profile = PROFILES[index]
    const newParams: Record<string, VitalParams> = {}
    for (const cfg of VITAL_CONFIGS) {
      newParams[cfg.key] = profile.overrides[cfg.key] ?? {
        baseline: cfg.defaultBaseline,
        variability: (cfg.normalHigh - cfg.normalLow) * 0.15,
        anomalyChance: 0.05,
      }
    }
    setParams(newParams)
  }

  const latestReading = readings.length > 0 ? readings[readings.length - 1] : null

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      {/* Header */}
      <motion.div variants={ITEM} className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Zap className="w-5 h-5 text-primary-500" />
            Vitals Simulator
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Generate realistic vital signs to test AI agent recommendations and alert thresholds
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Patient selector */}
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <select
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              disabled={isRunning}
              className="pl-9 pr-4 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 appearance-none cursor-pointer disabled:opacity-50"
            >
              {patients.map((p: Patient) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          {/* Config toggle */}
          <button
            onClick={() => setShowConfig(!showConfig)}
            className={cn(
              'p-2 rounded-lg border border-border transition-colors',
              showConfig ? 'bg-primary-600 text-white border-primary-600' : 'bg-card text-muted-foreground hover:text-foreground',
            )}
            title="Advanced settings"
          >
            <Settings2 className="w-4 h-4" />
          </button>

          {/* Start/Stop */}
          {isRunning ? (
            <button
              onClick={stopSimulation}
              className="flex items-center gap-2 px-4 py-2 bg-danger-600 text-white rounded-lg hover:bg-danger-700 transition-colors text-sm font-medium"
            >
              <Square className="w-4 h-4" /> Stop
            </button>
          ) : (
            <button
              onClick={startSimulation}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm font-medium"
            >
              <Play className="w-4 h-4" /> Start Simulation
            </button>
          )}
        </div>
      </motion.div>

      {/* Simulation Profiles */}
      <motion.div variants={ITEM}>
        <h2 className="text-sm font-bold text-foreground mb-3">Simulation Profiles</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {PROFILES.map((profile, i) => (
            <button
              key={profile.name}
              onClick={() => applyProfile(i)}
              disabled={isRunning}
              className={cn(
                'p-3 rounded-xl border text-left transition-all disabled:opacity-50',
                selectedProfile === i
                  ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20 shadow-sm'
                  : 'border-border bg-card hover:border-primary-300 hover:shadow-sm',
              )}
            >
              <p className="text-xs font-semibold text-foreground">{profile.name}</p>
              <p className="text-[10px] text-muted-foreground mt-1 line-clamp-2">{profile.description}</p>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Advanced Configuration */}
      {showConfig && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="clinical-card"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-foreground">Advanced Configuration</h2>
            <div className="flex items-center gap-3">
              <label className="text-xs text-muted-foreground">Interval:</label>
              <select
                value={intervalMs}
                onChange={(e) => setIntervalMs(Number(e.target.value))}
                className="px-2 py-1 rounded border border-border bg-card text-xs"
              >
                <option value={1000}>1s</option>
                <option value={2000}>2s</option>
                <option value={5000}>5s</option>
                <option value={10000}>10s</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {VITAL_CONFIGS.map((cfg) => {
              const p = params[cfg.key]
              return (
                <div key={cfg.key} className="p-3 rounded-lg bg-muted/50 border border-border">
                  <div className="flex items-center gap-2 mb-2">
                    <cfg.icon className={cn('w-4 h-4', cfg.color)} />
                    <span className="text-xs font-semibold text-foreground">{cfg.label}</span>
                  </div>
                  <div className="space-y-2">
                    <div>
                      <div className="flex justify-between text-[10px] text-muted-foreground">
                        <span>Baseline</span>
                        <span className="font-mono">{p.baseline} {cfg.unit}</span>
                      </div>
                      <input
                        type="range"
                        min={cfg.min}
                        max={cfg.max}
                        step={cfg.step}
                        value={p.baseline}
                        onChange={(e) => setParams((prev) => ({ ...prev, [cfg.key]: { ...prev[cfg.key], baseline: Number(e.target.value) } }))}
                        disabled={isRunning}
                        className="w-full h-1.5 accent-primary-500"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-muted-foreground">
                        <span>Variability</span>
                        <span className="font-mono">±{p.variability.toFixed(1)}</span>
                      </div>
                      <input
                        type="range"
                        min={0}
                        max={(cfg.max - cfg.min) * 0.3}
                        step={cfg.step}
                        value={p.variability}
                        onChange={(e) => setParams((prev) => ({ ...prev, [cfg.key]: { ...prev[cfg.key], variability: Number(e.target.value) } }))}
                        disabled={isRunning}
                        className="w-full h-1.5 accent-primary-500"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-[10px] text-muted-foreground">
                        <span>Anomaly Chance</span>
                        <span className="font-mono">{Math.round(p.anomalyChance * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={p.anomalyChance}
                        onChange={(e) => setParams((prev) => ({ ...prev, [cfg.key]: { ...prev[cfg.key], anomalyChance: Number(e.target.value) } }))}
                        disabled={isRunning}
                        className="w-full h-1.5 accent-primary-500"
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </motion.div>
      )}

      {/* Live Vital Cards */}
      {latestReading && (
        <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {VITAL_CONFIGS.map((cfg) => {
            const value = latestReading.values[cfg.key]
            const status: 'normal' | 'warning' | 'critical' =
              value > cfg.normalHigh * 1.3 || value < cfg.normalLow * 0.7
                ? 'critical'
                : value > cfg.normalHigh || value < cfg.normalLow
                ? 'warning'
                : 'normal'

            return (
              <div
                key={cfg.key}
                className={cn(
                  'clinical-card border transition-all',
                  status === 'critical' && 'border-danger-500/50 bg-danger-50/30 dark:bg-danger-900/10 animate-pulse',
                  status === 'warning' && 'border-warning-500/30 bg-warning-50/30 dark:bg-warning-900/10',
                  status === 'normal' && 'border-secondary-500/20 bg-secondary-50/20 dark:bg-secondary-900/5',
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <cfg.icon className={cn('w-4 h-4', cfg.color)} />
                  {status !== 'normal' && <AlertTriangle className={cn('w-3.5 h-3.5', status === 'critical' ? 'text-danger-500' : 'text-warning-500')} />}
                </div>
                <p className="text-xl font-bold font-mono text-foreground">
                  {cfg.step < 1 ? value.toFixed(1) : value}
                </p>
                <p className="text-[10px] text-muted-foreground">{cfg.unit}</p>
                <p className="text-[10px] font-medium text-foreground mt-0.5">{cfg.label}</p>
              </div>
            )
          })}
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trend Charts */}
        <div className="lg:col-span-2 space-y-4">
          {readings.length > 0 && (
            <motion.div variants={ITEM} className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {VITAL_CONFIGS.slice(0, 4).map((cfg) => (
                <div key={cfg.key} className="clinical-card">
                  <h3 className="text-xs font-bold text-foreground mb-3 flex items-center gap-2">
                    <cfg.icon className={cn('w-3.5 h-3.5', cfg.color)} />
                    {cfg.label}
                  </h3>
                  <div style={{ height: 140 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={readings} margin={{ top: 5, right: 8, bottom: 0, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.4} />
                        <XAxis dataKey="timestamp" tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                        <YAxis tick={{ fontSize: 9, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                        <Tooltip
                          formatter={(v: number) => [`${cfg.step < 1 ? v.toFixed(1) : v} ${cfg.unit}`, cfg.label]}
                          contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 11 }}
                        />
                        <ReferenceLine y={cfg.normalHigh} stroke="#e11d48" strokeDasharray="3 3" strokeOpacity={0.5} />
                        <ReferenceLine y={cfg.normalLow} stroke="#f59e0b" strokeDasharray="3 3" strokeOpacity={0.5} />
                        <Line
                          type="monotone"
                          dataKey={(d: GeneratedReading) => d.values[cfg.key]}
                          stroke={cfg.chartColor}
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              ))}
            </motion.div>
          )}

          {readings.length === 0 && !isRunning && (
            <motion.div variants={ITEM} className="clinical-card text-center py-16">
              <Zap className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-sm text-muted-foreground">
                Select a profile and click <strong>Start Simulation</strong> to generate vitals
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                AI agents will analyze the generated data and provide real-time recommendations
              </p>
            </motion.div>
          )}
        </div>

        {/* AI Recommendations Panel */}
        <motion.div variants={ITEM} className="clinical-card lg:sticky lg:top-6 self-start">
          <div className="flex items-center gap-2 mb-4">
            <BrainCircuit className="w-5 h-5 text-primary-500" />
            <h2 className="text-sm font-bold text-foreground">AI Recommendations</h2>
            {isRunning && (
              <RefreshCw className="w-3.5 h-3.5 text-primary-400 animate-spin ml-auto" />
            )}
          </div>

          {/* Patient Context Summary */}
          {patientContext && (patientContext.conditions.length > 0 || patientContext.medications.length > 0 || patientContext.allergies.length > 0) && (
            <div className="mb-3 p-2.5 rounded-lg bg-primary-50/50 dark:bg-primary-900/10 border border-primary-200/40 dark:border-primary-800/30">
              <p className="text-[10px] font-bold text-primary-700 dark:text-primary-300 mb-1.5">
                Personalizing for: {patientContext.name}
                {patientContext.age ? ` (${patientContext.age}y, ${patientContext.gender ?? 'unknown'})` : ''}
              </p>
              {patientContext.conditions.length > 0 && (
                <p className="text-[10px] text-primary-600 dark:text-primary-400 leading-relaxed">
                  <span className="font-semibold">Conditions:</span> {patientContext.conditions.slice(0, 5).join(', ')}{patientContext.conditions.length > 5 ? ` (+${patientContext.conditions.length - 5} more)` : ''}
                </p>
              )}
              {patientContext.medications.length > 0 && (
                <p className="text-[10px] text-primary-600 dark:text-primary-400 leading-relaxed mt-0.5">
                  <span className="font-semibold">Medications:</span> {patientContext.medications.slice(0, 5).join(', ')}{patientContext.medications.length > 5 ? ` (+${patientContext.medications.length - 5} more)` : ''}
                </p>
              )}
              {patientContext.allergies.length > 0 && (
                <p className="text-[10px] text-danger-600 dark:text-danger-400 leading-relaxed mt-0.5">
                  <span className="font-semibold">Allergies:</span> {patientContext.allergies.join(', ')}
                </p>
              )}
            </div>
          )}

          {recommendations.length === 0 ? (
            <div className="text-center py-8">
              <BrainCircuit className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-xs text-muted-foreground">
                Recommendations will appear when simulation starts
              </p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto">
              {recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className={cn(
                    'p-3 rounded-lg border',
                    rec.severity === 'critical' && 'border-danger-500/40 bg-danger-50/50 dark:bg-danger-900/20',
                    rec.severity === 'warning' && 'border-warning-500/30 bg-warning-50/50 dark:bg-warning-900/20',
                    rec.severity === 'info' && 'border-secondary-500/30 bg-secondary-50/50 dark:bg-secondary-900/20',
                  )}
                >
                  <div className="flex items-start gap-2">
                    {rec.severity === 'critical' && <AlertTriangle className="w-4 h-4 text-danger-500 flex-shrink-0 mt-0.5" />}
                    {rec.severity === 'warning' && <AlertTriangle className="w-4 h-4 text-warning-500 flex-shrink-0 mt-0.5" />}
                    {rec.severity === 'info' && <CheckCircle2 className="w-4 h-4 text-secondary-500 flex-shrink-0 mt-0.5" />}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-foreground">{rec.title}</p>
                      <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{rec.description}</p>

                      {/* ICD-10 & CPT Codes */}
                      {rec.icdCode && (
                        <div className="mt-2 space-y-1.5">
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded font-mono font-bold">
                              ICD-10: {rec.icdCode}
                            </span>
                            <span className="text-[10px] text-muted-foreground">{rec.icdDisplay}</span>
                          </div>
                          {rec.cptCodes && rec.cptCodes.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {rec.cptCodes.map((cpt) => (
                                <span
                                  key={cpt.code}
                                  className="text-[10px] px-1.5 py-0.5 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 rounded font-mono"
                                  title={cpt.display}
                                >
                                  CPT {cpt.code}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Contraindication Warnings */}
                      {rec.contraindications && rec.contraindications.length > 0 && (
                        <div className="mt-2 p-2 bg-danger-50/80 dark:bg-danger-900/20 rounded border border-danger-300/50 dark:border-danger-700/40">
                          <p className="text-[10px] font-semibold text-danger-700 dark:text-danger-300 mb-1 flex items-center gap-1">
                            <ShieldAlert className="w-3 h-3" />
                            Patient Safety Alerts
                          </p>
                          {rec.contraindications.map((ci, i) => (
                            <p key={i} className="text-[10px] text-danger-600 dark:text-danger-400 leading-relaxed">
                              {ci}
                            </p>
                          ))}
                        </div>
                      )}

                      {/* Patient-Specific Factors */}
                      {rec.patientFactors && rec.patientFactors.length > 0 && (
                        <div className="mt-1.5 p-2 bg-blue-50/60 dark:bg-blue-900/15 rounded border border-blue-200/50 dark:border-blue-800/30">
                          <p className="text-[10px] font-semibold text-blue-700 dark:text-blue-300 mb-0.5">Patient Factors</p>
                          <ul className="space-y-0.5">
                            {rec.patientFactors.map((pf, i) => (
                              <li key={i} className="text-[10px] text-blue-600 dark:text-blue-400 leading-relaxed flex items-start gap-1">
                                <span className="mt-0.5 shrink-0">•</span>
                                <span>{pf}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Treatment Plan */}
                      {rec.treatment && (
                        <div className="mt-2 p-2 bg-muted/50 rounded border border-muted">
                          <p className="text-[10px] font-semibold text-foreground mb-0.5">Recommended Treatment</p>
                          <p className="text-[10px] text-muted-foreground leading-relaxed">{rec.treatment}</p>
                        </div>
                      )}

                      <div className="flex items-center gap-2 mt-2">
                        <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded font-medium text-muted-foreground">
                          {rec.agent}
                        </span>
                        <span className="text-[10px] text-muted-foreground">{rec.timestamp}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Stats Footer */}
      {readings.length > 0 && (
        <motion.div variants={ITEM} className="flex items-center gap-6 text-xs text-muted-foreground">
          <span>Readings generated: <strong className="text-foreground">{readings.length}</strong></span>
          <span>Alerts triggered: <strong className="text-foreground">{readings.reduce((sum, r) => sum + r.alerts.length, 0)}</strong></span>
          <span>AI recommendations: <strong className="text-foreground">{recommendations.length}</strong></span>
          {isRunning && <span className="flex items-center gap-1"><RefreshCw className="w-3 h-3 animate-spin" /> Simulating every {intervalMs / 1000}s</span>}
        </motion.div>
      )}
    </motion.div>
  )
}
