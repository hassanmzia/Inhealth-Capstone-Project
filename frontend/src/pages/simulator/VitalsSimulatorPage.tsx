import { useState, useCallback, useRef, useEffect } from 'react'
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
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { cn } from '@/lib/utils'

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
}

function generateLocalRecommendations(readings: GeneratedReading[]): AIRecommendation[] {
  const recs: AIRecommendation[] = []
  if (readings.length === 0) return recs

  const latest = readings[readings.length - 1]
  const v = latest.values
  let id = 0

  // Heart rate checks
  if (v.heartRate > 120) {
    recs.push({ id: String(++id), severity: 'critical', title: 'Severe Tachycardia Detected', description: `Heart rate at ${v.heartRate} bpm. Consider immediate evaluation for arrhythmia, sepsis, or hypovolemia. 12-lead ECG recommended.`, agent: 'Cardiac Monitor Agent', timestamp: latest.timestamp, icdCode: 'R00.0', icdDisplay: 'Tachycardia, unspecified', cptCodes: [{ code: '93000', display: '12-lead ECG with interpretation' }, { code: '93040', display: 'Rhythm ECG (1-3 leads)' }, { code: '99291', display: 'Critical care, first 30-74 min' }], treatment: 'IV Metoprolol 5mg q5min (max 15mg), continuous telemetry monitoring, fluid resuscitation if hypovolemic' })
  } else if (v.heartRate > 100) {
    recs.push({ id: String(++id), severity: 'warning', title: 'Tachycardia Alert', description: `Heart rate elevated at ${v.heartRate} bpm. Assess for pain, anxiety, fever, dehydration, or medication effects.`, agent: 'Cardiac Monitor Agent', timestamp: latest.timestamp, icdCode: 'R00.0', icdDisplay: 'Tachycardia, unspecified', cptCodes: [{ code: '93000', display: '12-lead ECG with interpretation' }, { code: '93005', display: 'ECG tracing only' }], treatment: 'PO Metoprolol 25-50mg BID, address underlying cause (hydration, pain management, antipyretics)' })
  } else if (v.heartRate < 50) {
    recs.push({ id: String(++id), severity: 'critical', title: 'Severe Bradycardia', description: `Heart rate critically low at ${v.heartRate} bpm. Check for heart block, medication effects (beta-blockers), or vagal response. Prepare for possible transcutaneous pacing.`, agent: 'Cardiac Monitor Agent', timestamp: latest.timestamp, icdCode: 'R00.1', icdDisplay: 'Bradycardia, unspecified', cptCodes: [{ code: '93000', display: '12-lead ECG with interpretation' }, { code: '33210', display: 'Temporary transvenous pacemaker insertion' }, { code: '99291', display: 'Critical care, first 30-74 min' }], treatment: 'Atropine 1mg IV q3-5min (max 3mg), transcutaneous pacing if unresponsive, hold beta-blockers/CCBs' })
  }

  // Blood pressure checks
  if (v.systolicBP > 180 || v.diastolicBP > 120) {
    recs.push({ id: String(++id), severity: 'critical', title: 'Hypertensive Emergency', description: `BP ${v.systolicBP}/${v.diastolicBP} mmHg. Assess for end-organ damage. Consider IV antihypertensives. Target 25% reduction in first hour.`, agent: 'BP Management Agent', timestamp: latest.timestamp, icdCode: 'I16.1', icdDisplay: 'Hypertensive emergency', cptCodes: [{ code: '99291', display: 'Critical care, first 30-74 min' }, { code: '36000', display: 'IV access for drug administration' }, { code: '93000', display: '12-lead ECG with interpretation' }], treatment: 'IV Nicardipine 5mg/hr (titrate 2.5mg/hr q5min, max 15mg/hr) or IV Labetalol 20mg bolus then 2mg/min drip. Target 25% MAP reduction in 1hr.' })
  } else if (v.systolicBP > 160 || v.diastolicBP > 100) {
    recs.push({ id: String(++id), severity: 'warning', title: 'Hypertension Stage 2', description: `BP ${v.systolicBP}/${v.diastolicBP} mmHg. Review current antihypertensive regimen. Consider dose adjustment or adding second agent.`, agent: 'BP Management Agent', timestamp: latest.timestamp, icdCode: 'I10', icdDisplay: 'Essential (primary) hypertension', cptCodes: [{ code: '99214', display: 'Office visit, moderate complexity' }, { code: '93000', display: '12-lead ECG with interpretation' }], treatment: 'Lisinopril 10-20mg daily or Amlodipine 5-10mg daily. Add HCTZ 12.5-25mg if on monotherapy. Recheck BP in 2-4 weeks.' })
  } else if (v.systolicBP < 90) {
    recs.push({ id: String(++id), severity: 'critical', title: 'Hypotension Alert', description: `Systolic BP at ${v.systolicBP} mmHg. Assess for shock, dehydration, or sepsis. Consider fluid resuscitation.`, agent: 'BP Management Agent', timestamp: latest.timestamp, icdCode: 'I95.9', icdDisplay: 'Hypotension, unspecified', cptCodes: [{ code: '99291', display: 'Critical care, first 30-74 min' }, { code: '36000', display: 'IV access for drug administration' }, { code: '96360', display: 'IV infusion, hydration (first 31-60 min)' }], treatment: 'NS bolus 500-1000mL IV, Trendelenburg position, Norepinephrine 0.1-0.5 mcg/kg/min if unresponsive to fluids' })
  }

  // SpO2 checks
  if (v.spo2 < 90) {
    recs.push({ id: String(++id), severity: 'critical', title: 'Severe Hypoxemia', description: `SpO2 at ${v.spo2}%. Initiate supplemental O2 immediately. Consider ABG, CXR, and possible intubation if not improving.`, agent: 'Respiratory Agent', timestamp: latest.timestamp, icdCode: 'J96.01', icdDisplay: 'Acute respiratory failure with hypoxia', cptCodes: [{ code: '94760', display: 'Pulse oximetry (continuous)' }, { code: '71046', display: 'Chest X-ray, 2 views' }, { code: '82803', display: 'Arterial blood gas (ABG)' }, { code: '31500', display: 'Emergency endotracheal intubation' }], treatment: 'High-flow O2 via non-rebreather mask 15L/min, prepare for intubation if SpO2 not improving. RSI: Propofol 1.5mg/kg + Succinylcholine 1.5mg/kg.' })
  } else if (v.spo2 < 94) {
    recs.push({ id: String(++id), severity: 'warning', title: 'Desaturation Warning', description: `SpO2 at ${v.spo2}%. Apply supplemental O2 via nasal cannula. Monitor closely and consider ABG.`, agent: 'Respiratory Agent', timestamp: latest.timestamp, icdCode: 'R09.02', icdDisplay: 'Hypoxemia', cptCodes: [{ code: '94760', display: 'Pulse oximetry (continuous)' }, { code: '82803', display: 'Arterial blood gas (ABG)' }, { code: '71046', display: 'Chest X-ray, 2 views' }], treatment: 'Nasal cannula O2 2-4L/min, titrate to SpO2 > 94%. If COPD patient, target 88-92%. Obtain ABG if not improving.' })
  }

  // Glucose checks
  if (v.glucose > 300) {
    recs.push({ id: String(++id), severity: 'critical', title: 'Severe Hyperglycemia', description: `Blood glucose at ${v.glucose} mg/dL. Check for DKA (ketones, anion gap). Start insulin protocol and IV fluids. Monitor q1h.`, agent: 'Glycemic Control Agent', timestamp: latest.timestamp, icdCode: 'E11.65', icdDisplay: 'Type 2 DM with hyperglycemia', cptCodes: [{ code: '82947', display: 'Blood glucose quantitative' }, { code: '82570', display: 'Urine creatinine' }, { code: '80048', display: 'Basic metabolic panel (BMP)' }, { code: '96360', display: 'IV infusion, hydration' }], treatment: 'Insulin IV drip 0.1 units/kg/hr, NS 1L/hr x 2hr then 250mL/hr. Check BMP, ketones, anion gap. Monitor BG q1h. Replace K+ if < 5.3 mEq/L.' })
  } else if (v.glucose > 200) {
    recs.push({ id: String(++id), severity: 'warning', title: 'Hyperglycemia Alert', description: `Blood glucose elevated at ${v.glucose} mg/dL. Administer correction dose per sliding scale. Reassess in 2 hours.`, agent: 'Glycemic Control Agent', timestamp: latest.timestamp, icdCode: 'R73.9', icdDisplay: 'Hyperglycemia, unspecified', cptCodes: [{ code: '82947', display: 'Blood glucose quantitative' }, { code: '83036', display: 'Hemoglobin A1c (HbA1c)' }], treatment: 'Rapid-acting insulin per sliding scale (Lispro/Aspart). BG 201-250: 2U, 251-300: 4U, 301-350: 6U. Reassess in 2hr.' })
  } else if (v.glucose < 70) {
    recs.push({ id: String(++id), severity: 'critical', title: 'Hypoglycemia Detected', description: `Blood glucose critically low at ${v.glucose} mg/dL. Administer 15g fast-acting carbohydrate. If NPO or unconscious, give IV dextrose 50%.`, agent: 'Glycemic Control Agent', timestamp: latest.timestamp, icdCode: 'E16.2', icdDisplay: 'Hypoglycemia, unspecified', cptCodes: [{ code: '82947', display: 'Blood glucose quantitative' }, { code: '96374', display: 'IV push, single drug' }, { code: '80048', display: 'Basic metabolic panel (BMP)' }], treatment: 'If conscious: 15g oral glucose (4oz juice), recheck in 15min. If unconscious/NPO: D50W 25mL (12.5g) IV push or Glucagon 1mg IM. Hold insulin/sulfonylureas.' })
  }

  // Temperature checks
  if (v.temperature > 102) {
    recs.push({ id: String(++id), severity: 'critical', title: 'High Fever', description: `Temperature ${v.temperature}°F. Obtain blood cultures x2, CBC, lactate. Consider empiric antibiotics. Sepsis screening recommended.`, agent: 'Infection Control Agent', timestamp: latest.timestamp, icdCode: 'R50.9', icdDisplay: 'Fever, unspecified', cptCodes: [{ code: '87040', display: 'Blood culture, aerobic' }, { code: '85025', display: 'CBC with differential' }, { code: '83605', display: 'Lactic acid (lactate)' }, { code: '71046', display: 'Chest X-ray, 2 views' }], treatment: 'Acetaminophen 1000mg IV/PO q6h, blood cultures x2 from separate sites, empiric Vancomycin 25mg/kg IV + Piperacillin-Tazobactam 4.5g IV q6h.' })
  } else if (v.temperature > 100.4) {
    recs.push({ id: String(++id), severity: 'warning', title: 'Fever Detected', description: `Temperature ${v.temperature}°F. Administer antipyretics. Evaluate for infection source. Consider UA, CXR if new onset.`, agent: 'Infection Control Agent', timestamp: latest.timestamp, icdCode: 'R50.9', icdDisplay: 'Fever, unspecified', cptCodes: [{ code: '85025', display: 'CBC with differential' }, { code: '81001', display: 'Urinalysis, automated with micro' }, { code: '71046', display: 'Chest X-ray, 2 views' }], treatment: 'Acetaminophen 650-1000mg PO q6h or Ibuprofen 400-600mg PO q6h. Obtain UA, CBC, CXR if new onset. Cooling measures PRN.' })
  }

  // Respiratory rate checks
  if (v.respRate > 28) {
    recs.push({ id: String(++id), severity: 'critical', title: 'Tachypnea — Respiratory Failure Risk', description: `Respiratory rate at ${v.respRate} br/min. Assess for respiratory distress, metabolic acidosis, or anxiety. ABG recommended.`, agent: 'Respiratory Agent', timestamp: latest.timestamp, icdCode: 'R06.82', icdDisplay: 'Tachypnea, not elsewhere classified', cptCodes: [{ code: '82803', display: 'Arterial blood gas (ABG)' }, { code: '94760', display: 'Pulse oximetry (continuous)' }, { code: '71046', display: 'Chest X-ray, 2 views' }, { code: '99291', display: 'Critical care, first 30-74 min' }], treatment: 'Supplemental O2, obtain ABG stat. If metabolic acidosis: identify and treat cause. If respiratory failure: consider BiPAP or intubation.' })
  } else if (v.respRate > 22) {
    recs.push({ id: String(++id), severity: 'warning', title: 'Elevated Respiratory Rate', description: `Respiratory rate at ${v.respRate} br/min. Monitor closely. Assess for pain, fever, or anxiety as contributing factors.`, agent: 'Respiratory Agent', timestamp: latest.timestamp, icdCode: 'R06.82', icdDisplay: 'Tachypnea, not elsewhere classified', cptCodes: [{ code: '94760', display: 'Pulse oximetry (continuous)' }, { code: '71046', display: 'Chest X-ray, 2 views' }], treatment: 'Continuous pulse oximetry, address underlying cause. Anxiolytic if anxiety-driven. Pain management if pain-related.' })
  }

  // Multi-vital pattern detection (SIRS/Sepsis)
  if (v.heartRate > 100 && v.systolicBP < 100 && v.temperature > 100.4 && v.respRate > 22) {
    recs.push({ id: String(++id), severity: 'critical', title: 'SIRS/Sepsis Criteria Met', description: `Multiple abnormalities: HR ${v.heartRate}, BP ${v.systolicBP}/${v.diastolicBP}, Temp ${v.temperature}°F, RR ${v.respRate}. Activate sepsis bundle: cultures, lactate, IV fluids 30mL/kg, broad-spectrum antibiotics within 1 hour.`, agent: 'Sepsis Screening Agent', timestamp: latest.timestamp, icdCode: 'A41.9', icdDisplay: 'Sepsis, unspecified organism', cptCodes: [{ code: '99291', display: 'Critical care, first 30-74 min' }, { code: '87040', display: 'Blood culture, aerobic' }, { code: '83605', display: 'Lactic acid (lactate)' }, { code: '36000', display: 'IV access for drug administration' }, { code: '96360', display: 'IV infusion, hydration' }], treatment: 'SEP-1 Bundle: Blood cultures x2, Lactate level, NS 30mL/kg IV bolus within 3hr, Broad-spectrum ABX within 1hr (Vanc + Zosyn). Repeat lactate if > 2. Vasopressors if MAP < 65 after fluids.' })
  }

  if (recs.length === 0) {
    recs.push({ id: '0', severity: 'info', title: 'All Vitals Within Normal Range', description: 'No abnormalities detected. Continue routine monitoring per care plan.', agent: 'Clinical Decision Support', timestamp: latest.timestamp, icdCode: 'Z00.00', icdDisplay: 'General adult medical examination', cptCodes: [{ code: '99213', display: 'Office visit, low complexity' }], treatment: 'Continue current care plan. Next routine vitals check per protocol.' })
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

  // Static patient list (no backend dependency)
  const patients: Patient[] = [
    { id: 'p1', name: 'Maria Garcia' },
    { id: 'p2', name: 'James Wilson' },
    { id: 'p3', name: 'Susan Chen' },
    { id: 'p4', name: 'Robert Johnson' },
    { id: 'p5', name: 'Aisha Patel' },
  ]

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
      // Generate local AI recommendations from latest readings
      const recs = generateLocalRecommendations(trimmed)
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
