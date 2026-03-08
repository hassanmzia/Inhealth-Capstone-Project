import { useState, useMemo, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  User,
  Activity,
  Pill,
  ClipboardList,
  BrainCircuit,
  FlaskConical,
  Users,
  FileText,
  Phone,
  Mail,
  MapPin,
  Calendar,
  Archive,
  ChevronDown,
  ChevronUp,
  Search,
  ExternalLink,
  Loader2,
  Target,
  Settings2,
} from 'lucide-react'
import { format, subDays, subHours, subMinutes } from 'date-fns'
import api from '@/services/api'
import { useCarePlans, useVitalTargets, useUpdateVitalTarget, useInitializeVitalTargets } from '@/hooks/useFHIR'
import type { FHIRCarePlan as FHIRCarePlanType } from '@/services/fhir'
import VitalsMonitor from '@/components/clinical/VitalsMonitor'
import VitalsChart from '@/components/charts/VitalsChart'
import GlucoseChart from '@/components/charts/GlucoseChart'
import EcgWaveform from '@/components/charts/EcgWaveform'
import MedicationList from '@/components/clinical/MedicationList'
import CareGapList from '@/components/clinical/CareGapList'
import AIRecommendationPanel from '@/components/clinical/AIRecommendationPanel'
import AgentControlPanel from '@/components/agents/AgentControlPanel'
import { RiskScoreBadge } from '@/components/charts/RiskScoreGauge'
import { cn } from '@/lib/utils'
import type { PatientSummary, VitalSign, Medication, CareGap } from '@/types/clinical'

// ─── Generate demo vitals when API returns empty ─────────────────────────────
function generateDemoVitals(patientId: string): VitalSign[] {
  const now = new Date()
  const vitals: VitalSign[] = []
  let id = 0

  // Generate 24 hours of data at 30-minute intervals (48 points)
  for (let i = 47; i >= 0; i--) {
    const ts = subMinutes(now, i * 30).toISOString()
    const jitter = () => (Math.random() - 0.5) * 2

    // Heart Rate (60-100 normal)
    const hr = Math.round(72 + Math.sin(i * 0.3) * 8 + jitter() * 5)
    vitals.push({
      id: String(++id), patientId, type: 'heart_rate', value: hr,
      unit: 'bpm', timestamp: ts, status: hr > 100 || hr < 60 ? 'warning' : 'normal',
      source: 'device', normalMin: 60, normalMax: 100,
    })

    // Systolic BP (90-140 normal)
    const sys = Math.round(125 + Math.sin(i * 0.2) * 10 + jitter() * 6)
    const dia = Math.round(78 + Math.sin(i * 0.2) * 6 + jitter() * 4)
    vitals.push({
      id: String(++id), patientId, type: 'blood_pressure_systolic', value: sys,
      unit: 'mmHg', timestamp: ts, status: sys > 140 ? 'warning' : 'normal',
      source: 'device', systolic: sys, diastolic: dia, normalMin: 90, normalMax: 140,
    })
    vitals.push({
      id: String(++id), patientId, type: 'blood_pressure_diastolic', value: dia,
      unit: 'mmHg', timestamp: ts, status: dia > 90 ? 'warning' : 'normal',
      source: 'device', normalMin: 60, normalMax: 90,
    })

    // SpO2 (95-100 normal)
    const spo2 = Math.min(100, Math.round(97 + Math.sin(i * 0.15) * 1.5 + jitter()))
    vitals.push({
      id: String(++id), patientId, type: 'spo2', value: spo2,
      unit: '%', timestamp: ts, status: spo2 < 95 ? 'warning' : 'normal',
      source: 'device', normalMin: 95, normalMax: 100,
    })

    // Temperature (36.1-37.2 °C normal)
    const temp = parseFloat((36.6 + Math.sin(i * 0.25) * 0.4 + jitter() * 0.2).toFixed(1))
    vitals.push({
      id: String(++id), patientId, type: 'temperature', value: temp,
      unit: '°C', timestamp: ts, status: temp > 37.5 ? 'warning' : 'normal',
      source: 'device', normalMin: 36.1, normalMax: 37.2,
    })

    // Respiratory Rate (12-20 normal)
    const rr = Math.round(16 + Math.sin(i * 0.35) * 3 + jitter() * 2)
    vitals.push({
      id: String(++id), patientId, type: 'respiratory_rate', value: rr,
      unit: '/min', timestamp: ts, status: rr > 20 || rr < 12 ? 'warning' : 'normal',
      source: 'device', normalMin: 12, normalMax: 20,
    })

    // Glucose (70-180 mg/dL normal) — every 2 hours (every 4th interval)
    if (i % 4 === 0) {
      const glucose = Math.round(112 + Math.sin(i * 0.4) * 35 + jitter() * 15)
      vitals.push({
        id: String(++id), patientId, type: 'glucose', value: glucose,
        unit: 'mg/dL', timestamp: ts,
        status: glucose > 180 ? 'warning' : glucose < 70 ? 'critical' : 'normal',
        source: 'device', normalMin: 70, normalMax: 180,
      })
    }
  }

  // Add latest ECG observation
  vitals.push({
    id: String(++id), patientId, type: 'ecg', value: 72,
    unit: 'bpm', timestamp: now.toISOString(), status: 'normal',
    source: 'device', ecgRhythm: 'normal_sinus',
  })

  return vitals
}

// Generate archived vitals (older than 24h, up to 7 days)
function generateArchivedVitals(patientId: string): VitalSign[] {
  const now = new Date()
  const vitals: VitalSign[] = []
  let id = 10000

  // Generate 7 days of data at 4-hour intervals (42 points)
  for (let day = 7; day >= 1; day--) {
    for (let h = 0; h < 24; h += 4) {
      const ts = subHours(subDays(now, day), 24 - h).toISOString()
      const jitter = () => (Math.random() - 0.5) * 2
      const phase = day * 6 + h

      vitals.push({
        id: String(++id), patientId, type: 'heart_rate',
        value: Math.round(74 + Math.sin(phase * 0.2) * 10 + jitter() * 4),
        unit: 'bpm', timestamp: ts, status: 'normal', source: 'ehr',
      })

      const sys = Math.round(128 + Math.sin(phase * 0.15) * 12 + jitter() * 5)
      const dia = Math.round(80 + Math.sin(phase * 0.15) * 6 + jitter() * 3)
      vitals.push({
        id: String(++id), patientId, type: 'blood_pressure_systolic',
        value: sys, unit: 'mmHg', timestamp: ts,
        status: sys > 140 ? 'warning' : 'normal', source: 'ehr',
        systolic: sys, diastolic: dia,
      })
      vitals.push({
        id: String(++id), patientId, type: 'blood_pressure_diastolic',
        value: dia, unit: 'mmHg', timestamp: ts, status: 'normal', source: 'ehr',
      })

      vitals.push({
        id: String(++id), patientId, type: 'spo2',
        value: Math.min(100, Math.round(97 + jitter())),
        unit: '%', timestamp: ts, status: 'normal', source: 'ehr',
      })

      vitals.push({
        id: String(++id), patientId, type: 'temperature',
        value: parseFloat((36.7 + Math.sin(phase * 0.3) * 0.3 + jitter() * 0.15).toFixed(1)),
        unit: '°C', timestamp: ts, status: 'normal', source: 'ehr',
      })

      vitals.push({
        id: String(++id), patientId, type: 'respiratory_rate',
        value: Math.round(16 + Math.sin(phase * 0.25) * 2 + jitter()),
        unit: '/min', timestamp: ts, status: 'normal', source: 'ehr',
      })

      if (h % 8 === 0) {
        vitals.push({
          id: String(++id), patientId, type: 'glucose',
          value: Math.round(115 + Math.sin(phase * 0.3) * 30 + jitter() * 10),
          unit: 'mg/dL', timestamp: ts, status: 'normal', source: 'ehr',
        })
      }
    }
  }

  return vitals
}

const TABS = [
  { id: 'overview', label: 'Overview', icon: User },
  { id: 'vitals', label: 'Vitals', icon: Activity },
  { id: 'medications', label: 'Medications', icon: Pill },
  { id: 'clinical', label: 'Clinical', icon: ClipboardList },
  { id: 'agents', label: 'AI Agents', icon: BrainCircuit },
  { id: 'research', label: 'Research', icon: FlaskConical },
  { id: 'sdoh', label: 'SDOH', icon: Users },
  { id: 'documents', label: 'Documents', icon: FileText },
]

export default function PatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('overview')

  const { data: patient, isLoading } = useQuery<PatientSummary>({
    queryKey: ['patient', patientId],
    queryFn: () => api.get(`/patients/${patientId}/`).then((r) => r.data),
    enabled: !!patientId,
  })

  const { data: vitals } = useQuery<VitalSign[]>({
    queryKey: ['patient-vitals', patientId],
    queryFn: () => api.get(`/patients/${patientId}/vitals/`).then((r) => r.data ?? []),
    enabled: !!patientId,
    refetchInterval: 30000,
    placeholderData: [],
  })

  const { data: medications } = useQuery<Medication[]>({
    queryKey: ['patient-medications', patientId],
    queryFn: () => api.get(`/patients/${patientId}/medications/`).then((r) => r.data ?? []),
    enabled: !!patientId,
    placeholderData: [],
  })

  const { data: careGaps } = useQuery<CareGap[]>({
    queryKey: ['care-gaps', patientId],
    queryFn: () => api.get(`/patients/${patientId}/care-gaps/`).then((r) => r.data ?? []),
    enabled: !!patientId,
    placeholderData: [],
  })

  const { data: recommendations, refetch: refetchRecs } = useQuery({
    queryKey: ['patient-recommendations', patientId],
    queryFn: () => api.get(`/agents/recommendations/?patient_id=${patientId}`).then((r) => r.data ?? []),
    enabled: !!patientId,
    placeholderData: [],
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (!patient) {
    return (
      <div className="text-center py-16">
        <p className="text-muted-foreground">Patient not found</p>
        <button onClick={() => navigate('/patients')} className="mt-4 text-primary-600 hover:underline text-sm">
          Back to patients
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-7xl">
      {/* Back button */}
      <button
        onClick={() => navigate('/patients')}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Patients
      </button>

      {/* Patient header */}
      <div className="clinical-card">
        <div className="flex items-start gap-4 flex-wrap">
          {/* Avatar */}
          <div className="w-16 h-16 rounded-full bg-gradient-clinical flex items-center justify-center text-white text-xl font-bold flex-shrink-0">
            {patient.firstName[0]}{patient.lastName[0]}
          </div>

          {/* Basic info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start gap-3 flex-wrap">
              <div>
                <h1 className="text-xl font-bold text-foreground">
                  {patient.firstName} {patient.lastName}
                </h1>
                <p className="text-sm text-muted-foreground">
                  {patient.age}yo · {patient.gender} · MRN: <span className="font-mono">{patient.mrn}</span>
                </p>
              </div>
              {patient.riskScore && (
                <RiskScoreBadge score={patient.riskScore.score} />
              )}
              {patient.openCareGaps > 0 && (
                <span className="text-xs font-semibold text-warning-600 bg-warning-50 dark:bg-warning-900/20 px-2 py-1 rounded-full border border-warning-200">
                  {patient.openCareGaps} Care Gaps
                </span>
              )}
            </div>

            {/* Contact info */}
            <div className="flex flex-wrap gap-4 mt-3 text-xs text-muted-foreground">
              {patient.phone && (
                <span className="flex items-center gap-1">
                  <Phone className="w-3 h-3" /> {patient.phone}
                </span>
              )}
              {patient.email && (
                <span className="flex items-center gap-1">
                  <Mail className="w-3 h-3" /> {patient.email}
                </span>
              )}
              {patient.address && (
                <span className="flex items-center gap-1">
                  <MapPin className="w-3 h-3" />
                  {patient.address.city}, {patient.address.state}
                </span>
              )}
              {patient.nextAppointmentDate && (
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  Next: {format(new Date(patient.nextAppointmentDate), 'MMM d, yyyy')}
                </span>
              )}
            </div>

            {/* Conditions */}
            <div className="flex flex-wrap gap-1.5 mt-3">
              {patient.activeConditions.map((c, i) => (
                <span key={i} className="text-xs font-medium px-2 py-0.5 rounded-full bg-clinical-100 dark:bg-clinical-800 text-clinical-700 dark:text-clinical-300">
                  {c.code} · {c.display}
                </span>
              ))}
            </div>
          </div>

          {/* Provider */}
          {patient.primaryProvider && (
            <div className="text-right text-xs text-muted-foreground">
              <p className="font-semibold text-foreground">{patient.primaryProvider.name}</p>
              <p>{patient.primaryProvider.specialty}</p>
            </div>
          )}
        </div>
      </div>

      {/* Live vitals strip */}
      {vitals && vitals.length > 0 && (
        <VitalsMonitor vitals={vitals} isRealtime compact />
      )}

      {/* Tabs */}
      <div className="border-b border-border overflow-x-auto">
        <nav className="flex gap-1 min-w-max">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border',
              )}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <motion.div key={activeTab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.15 }}>
        {activeTab === 'overview' && (
          <OverviewTab patient={patient} vitals={vitals ?? []} careGaps={careGaps ?? []} recommendations={recommendations ?? []} refetchRecs={refetchRecs} />
        )}
        {activeTab === 'vitals' && (
          <VitalsTab vitals={vitals ?? []} patientId={patientId!} />
        )}
        {activeTab === 'medications' && (
          <MedicationsTab medications={medications ?? []} patient={patient} />
        )}
        {activeTab === 'clinical' && (
          <ClinicalTab careGaps={careGaps ?? []} patientId={patientId!} patient={patient} />
        )}
        {activeTab === 'agents' && (
          <AgentsTab patientId={patientId!} patientName={`${patient.firstName} ${patient.lastName}`} recommendations={recommendations ?? []} refetchRecs={refetchRecs} />
        )}
        {activeTab === 'research' && (
          <ResearchTab patient={patient} />
        )}
        {activeTab === 'sdoh' && (
          <SDOHTab />
        )}
        {activeTab === 'documents' && (
          <DocumentsTab />
        )}
      </motion.div>
    </div>
  )
}

// ─── Tab Components ───────────────────────────────────────────────────────────

function OverviewTab({ patient, vitals, careGaps, recommendations, refetchRecs }: {
  patient: PatientSummary
  vitals: VitalSign[]
  careGaps: CareGap[]
  recommendations: ReturnType<typeof Array.prototype.slice>
  refetchRecs: () => void
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="clinical-card">
          <h3 className="text-sm font-bold text-foreground mb-3">Recent Vitals</h3>
          <VitalsMonitor vitals={vitals} compact />
        </div>
        <div className="clinical-card">
          <h3 className="text-sm font-bold text-foreground mb-3">Care Gaps ({careGaps.filter(g => g.status === 'open').length} open)</h3>
          <CareGapList careGaps={careGaps} patientId={patient.id} />
        </div>
        <CarePlansSection patientId={patient.id} />
        <VitalTargetsSection patientId={patient.id} />
      </div>
      <div className="clinical-card">
        <h3 className="text-sm font-bold text-foreground mb-3">AI Recommendations</h3>
        <AIRecommendationPanel recommendations={recommendations} onDecision={refetchRecs} showHITL />
      </div>
    </div>
  )
}

function VitalsTab({ vitals, patientId }: { vitals: VitalSign[]; patientId: string }) {
  const [showArchived, setShowArchived] = useState(false)

  // Generate demo data when API returns empty
  const activeVitals = useMemo(() => {
    if (vitals.length > 0) return vitals
    return generateDemoVitals(patientId)
  }, [vitals, patientId])

  const archivedVitals = useMemo(() => generateArchivedVitals(patientId), [patientId])

  // Combine active + archived when showing all
  const allVitals = useMemo(
    () => (showArchived ? [...archivedVitals, ...activeVitals] : activeVitals),
    [activeVitals, archivedVitals, showArchived],
  )

  const hasRealVitals = vitals.length > 0
  const latestEcg = activeVitals.find((v) => v.type === 'ecg')
  const latestHr = activeVitals.find((v) => v.type === 'heart_rate')
  // Animate ECG when real heart rate or ECG data exists from API/device
  const ecgIsLive = hasRealVitals && !!(latestEcg || latestHr)

  // Latest values for summary cards
  const latestByType = useMemo(() => {
    const map: Partial<Record<string, VitalSign>> = {}
    for (const v of activeVitals) {
      if (!map[v.type] || v.timestamp > map[v.type]!.timestamp) {
        map[v.type] = v
      }
    }
    return map
  }, [activeVitals])

  const summaryCards = [
    { key: 'heart_rate', label: 'Heart Rate', unit: 'bpm', color: 'text-red-500', bg: 'bg-red-50 dark:bg-red-900/10' },
    { key: 'blood_pressure_systolic', label: 'Blood Pressure', unit: 'mmHg', color: 'text-blue-500', bg: 'bg-blue-50 dark:bg-blue-900/10',
      format: (v: VitalSign) => `${v.systolic ?? v.value}/${v.diastolic ?? '-'}` },
    { key: 'spo2', label: 'SpO2', unit: '%', color: 'text-green-500', bg: 'bg-green-50 dark:bg-green-900/10' },
    { key: 'temperature', label: 'Temperature', unit: '°C', color: 'text-orange-500', bg: 'bg-orange-50 dark:bg-orange-900/10' },
    { key: 'respiratory_rate', label: 'Resp Rate', unit: '/min', color: 'text-teal-500', bg: 'bg-teal-50 dark:bg-teal-900/10' },
    { key: 'glucose', label: 'Glucose', unit: 'mg/dL', color: 'text-purple-500', bg: 'bg-purple-50 dark:bg-purple-900/10' },
  ]

  return (
    <div className="space-y-6">
      {/* Vitals Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {summaryCards.map((card) => {
          const vital = latestByType[card.key]
          if (!vital) return null
          const displayValue = card.format ? card.format(vital) : vital.value
          return (
            <div key={card.key} className={cn('clinical-card p-3 text-center', card.bg)}>
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">{card.label}</p>
              <p className={cn('text-xl font-bold font-mono mt-1', card.color)}>{displayValue}</p>
              <p className="text-[10px] text-muted-foreground">{card.unit}</p>
              {vital.status !== 'normal' && (
                <span className={cn(
                  'inline-block mt-1 text-[9px] font-semibold px-1.5 py-0.5 rounded-full',
                  vital.status === 'critical' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                    : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300',
                )}>
                  {vital.status}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* ECG Waveform */}
      <div className="clinical-card overflow-hidden">
        <h3 className="text-sm font-bold text-foreground mb-4">ECG Monitor</h3>
        <div className="flex justify-center">
          <EcgWaveform
            heartRate={latestEcg?.value ?? latestHr?.value ?? 72}
            rhythm={latestEcg?.ecgRhythm ?? 'normal_sinus'}
            width={Math.min(720, typeof window !== 'undefined' ? window.innerWidth - 120 : 600)}
            height={200}
            isLive={ecgIsLive}
            showOverlay
          />
        </div>
      </div>

      {/* Vitals Trend Chart — all vitals active */}
      <div className="clinical-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-foreground">
            Vitals Trend {showArchived ? '(7 days)' : '(24h)'}
          </h3>
          <button
            onClick={() => setShowArchived(!showArchived)}
            className="flex items-center gap-1.5 text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 transition-colors"
          >
            <Archive className="w-3.5 h-3.5" />
            {showArchived ? 'Show 24h' : 'Show Archived (7d)'}
            {showArchived ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>
        <VitalsChart
          vitals={allVitals}
          height={360}
          showHR
          showBP
          showSpO2
          showTemp
          showRR
          timeRangeHours={showArchived ? 168 : 24}
        />
      </div>

      {/* Glucose Trend */}
      <div className="clinical-card">
        <h3 className="text-sm font-bold text-foreground mb-4">Glucose Trend</h3>
        <GlucoseChart
          readings={allVitals
            .filter((v) => v.type === 'glucose')
            .map((v) => ({ timestamp: v.timestamp, value: v.value }))}
          height={280}
          showPrediction
          showTIR
        />
      </div>

      {/* Archived Vitals Table */}
      {showArchived && (
        <div className="clinical-card">
          <h3 className="text-sm font-bold text-foreground mb-4">Archived Vital Signs (Past 7 Days)</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left p-2 font-medium text-muted-foreground">Date/Time</th>
                  <th className="text-center p-2 font-medium text-muted-foreground">HR (bpm)</th>
                  <th className="text-center p-2 font-medium text-muted-foreground">BP (mmHg)</th>
                  <th className="text-center p-2 font-medium text-muted-foreground">SpO2 (%)</th>
                  <th className="text-center p-2 font-medium text-muted-foreground">Temp (°C)</th>
                  <th className="text-center p-2 font-medium text-muted-foreground">RR (/min)</th>
                  <th className="text-center p-2 font-medium text-muted-foreground">Glucose (mg/dL)</th>
                  <th className="text-center p-2 font-medium text-muted-foreground">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {(() => {
                  // Group archived vitals by timestamp (rounded to nearest hour)
                  const grouped = new Map<string, Record<string, VitalSign>>()
                  for (const v of archivedVitals) {
                    const key = format(new Date(v.timestamp), 'yyyy-MM-dd HH:00')
                    if (!grouped.has(key)) grouped.set(key, {})
                    grouped.get(key)![v.type] = v
                  }
                  const rows = Array.from(grouped.entries()).sort((a, b) => b[0].localeCompare(a[0]))
                  return rows.map(([timeKey, vals]) => {
                    const bp = vals['blood_pressure_systolic']
                    return (
                      <tr key={timeKey} className="hover:bg-muted/50 transition-colors">
                        <td className="p-2 font-medium text-foreground whitespace-nowrap">
                          {format(new Date(timeKey), 'MMM d, HH:mm')}
                        </td>
                        <td className={cn('p-2 text-center font-mono', vals['heart_rate']?.status === 'warning' && 'text-yellow-600 font-bold', vals['heart_rate']?.status === 'critical' && 'text-red-600 font-bold')}>
                          {vals['heart_rate']?.value ?? '—'}
                        </td>
                        <td className={cn('p-2 text-center font-mono', bp?.status === 'warning' && 'text-yellow-600 font-bold')}>
                          {bp ? `${bp.systolic ?? bp.value}/${bp.diastolic ?? vals['blood_pressure_diastolic']?.value ?? '-'}` : '—'}
                        </td>
                        <td className={cn('p-2 text-center font-mono', vals['spo2']?.status === 'warning' && 'text-yellow-600 font-bold')}>
                          {vals['spo2']?.value ?? '—'}
                        </td>
                        <td className="p-2 text-center font-mono">
                          {vals['temperature']?.value ?? '—'}
                        </td>
                        <td className="p-2 text-center font-mono">
                          {vals['respiratory_rate']?.value ?? '—'}
                        </td>
                        <td className={cn('p-2 text-center font-mono', vals['glucose']?.status === 'warning' && 'text-yellow-600 font-bold')}>
                          {vals['glucose']?.value ?? '—'}
                        </td>
                        <td className="p-2 text-center">
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                            {vals['heart_rate']?.source ?? 'ehr'}
                          </span>
                        </td>
                      </tr>
                    )
                  })
                })()}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function generateDemoCareGaps(patient: PatientSummary): CareGap[] {
  const now = new Date()
  const conditions = patient.activeConditions?.map((c) => c.display.toLowerCase()) ?? []
  const gaps: CareGap[] = []
  let id = 0

  const add = (g: Partial<CareGap>) =>
    gaps.push({
      id: `demo-gap-${++id}`,
      patientId: patient.id,
      title: '',
      description: '',
      category: 'chronic_management',
      priority: 'medium',
      status: 'open',
      openedAt: subDays(now, 30 + Math.floor(Math.random() * 60)).toISOString(),
      ...g,
    } as CareGap)

  // Diabetes care gaps
  if (conditions.some((c) => c.includes('diabet'))) {
    add({
      title: 'HbA1c Test Overdue',
      description: 'Last HbA1c was > 90 days ago. Guideline recommends every 3 months for uncontrolled T2DM.',
      category: 'chronic_management',
      priority: 'high',
      dueDate: subDays(now, 15).toISOString(),
      measure: 'HEDIS CDC – HbA1c Testing',
      aiRecommendation: 'Order HbA1c lab. Last result was 8.2% — consider medication adjustment if still elevated.',
    })
    add({
      title: 'Diabetic Eye Exam Due',
      description: 'No dilated eye exam documented in past 12 months.',
      category: 'screening',
      priority: 'medium',
      dueDate: subDays(now, -30).toISOString(),
      measure: 'HEDIS CDC – Eye Exam',
      aiRecommendation: 'Refer to ophthalmology for annual dilated retinal exam.',
    })
    add({
      title: 'Diabetic Foot Exam Needed',
      description: 'Annual comprehensive foot exam not documented.',
      category: 'preventive',
      priority: 'medium',
      dueDate: subDays(now, -14).toISOString(),
      measure: 'ADA Standards of Care',
    })
  }

  // Hypertension care gaps
  if (conditions.some((c) => c.includes('hypertens') || c.includes('blood pressure'))) {
    add({
      title: 'Blood Pressure Not at Goal',
      description: 'Last 3 BP readings above target (>140/90 mmHg).',
      category: 'chronic_management',
      priority: 'high',
      dueDate: subDays(now, -7).toISOString(),
      measure: 'HEDIS CBP – Controlling Blood Pressure',
      aiRecommendation: 'Consider titrating antihypertensive therapy. Home BP monitoring may improve control.',
    })
  }

  // Heart failure care gaps
  if (conditions.some((c) => c.includes('heart failure'))) {
    add({
      title: 'Beta-Blocker Therapy Review',
      description: 'Beta-blocker dose has not been optimized per HF guidelines.',
      category: 'medication',
      priority: 'high',
      dueDate: subDays(now, -10).toISOString(),
      measure: 'ACC/AHA HF Guidelines',
      aiRecommendation: 'Patient on carvedilol 25mg BID — assess tolerability for up-titration to target dose.',
    })
    add({
      title: 'Cardiology Follow-Up Needed',
      description: 'No cardiology visit in the past 6 months for active HF management.',
      category: 'referral',
      priority: 'medium',
      dueDate: subDays(now, -20).toISOString(),
    })
  }

  // CKD care gaps
  if (conditions.some((c) => c.includes('kidney') || c.includes('ckd') || c.includes('renal'))) {
    add({
      title: 'eGFR / Creatinine Monitoring Due',
      description: 'CKD patients require renal function monitoring every 3–6 months.',
      category: 'chronic_management',
      priority: 'high',
      dueDate: subDays(now, 5).toISOString(),
      measure: 'KDIGO CKD Guidelines',
      aiRecommendation: 'Order BMP with eGFR. Last eGFR was 38 mL/min — Stage 3b. Monitor for progression.',
    })
    add({
      title: 'Nephrology Referral',
      description: 'eGFR < 45 — specialist referral recommended per KDIGO guidelines.',
      category: 'referral',
      priority: 'medium',
      dueDate: subDays(now, -30).toISOString(),
    })
  }

  // COPD care gaps
  if (conditions.some((c) => c.includes('copd') || c.includes('pulmonary'))) {
    add({
      title: 'Spirometry Follow-Up Due',
      description: 'No spirometry performed in the past 12 months for COPD monitoring.',
      category: 'screening',
      priority: 'medium',
      dueDate: subDays(now, -21).toISOString(),
      measure: 'GOLD COPD Guidelines',
    })
    add({
      title: 'Influenza Vaccination Due',
      description: 'Annual influenza vaccination not documented for this season.',
      category: 'immunization',
      priority: 'high',
      dueDate: subDays(now, -14).toISOString(),
      aiRecommendation: 'COPD patients are at higher risk. Administer influenza vaccine today if no contraindications.',
    })
  }

  // AFib
  if (conditions.some((c) => c.includes('fibrillation') || c.includes('afib'))) {
    add({
      title: 'CHA₂DS₂-VASc Score Reassessment',
      description: 'Stroke risk score should be reassessed annually.',
      category: 'chronic_management',
      priority: 'medium',
      dueDate: subDays(now, -45).toISOString(),
      measure: 'AHA/ACC AFib Guidelines',
    })
  }

  // Universal preventive gaps
  add({
    title: 'Annual Wellness Visit',
    description: 'No annual wellness visit documented in the current calendar year.',
    category: 'preventive',
    priority: 'low',
    dueDate: subDays(now, -60).toISOString(),
    measure: 'CMS AWV',
  })

  // Default if no conditions
  if (gaps.length <= 1) {
    add({
      title: 'Medication Reconciliation',
      description: 'Medication reconciliation not performed in the last 30 days.',
      category: 'medication',
      priority: 'medium',
      dueDate: subDays(now, -10).toISOString(),
      aiRecommendation: 'Review current medication list with the patient during the next visit.',
    })
    add({
      title: 'Lipid Panel Screening',
      description: 'No lipid panel on file in the past 12 months.',
      category: 'screening',
      priority: 'medium',
      dueDate: subDays(now, -30).toISOString(),
      measure: 'USPSTF Statin Use',
    })
  }

  return gaps
}

function ClinicalTab({ careGaps, patientId, patient }: { careGaps: CareGap[]; patientId: string; patient: PatientSummary }) {
  const gaps = useMemo(() => {
    if (careGaps.length > 0) return careGaps
    return generateDemoCareGaps(patient)
  }, [careGaps, patient])

  return (
    <div className="space-y-6">
      <CarePlansSection patientId={patientId} />
      <div className="clinical-card">
        <h3 className="text-sm font-bold text-foreground mb-4">Care Gaps & Quality Measures</h3>
        <CareGapList careGaps={gaps} patientId={patientId} />
      </div>
    </div>
  )
}

function CarePlansSection({ patientId }: { patientId: string }) {
  const { data: carePlansResult, isLoading } = useCarePlans(patientId)
  const carePlans = carePlansResult?.entry?.map((e: { resource: FHIRCarePlanType }) => e.resource) ?? []

  if (isLoading) {
    return (
      <div className="clinical-card">
        <h3 className="text-sm font-bold text-foreground mb-4">Care Plans</h3>
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading care plans...
        </div>
      </div>
    )
  }

  if (carePlans.length === 0) {
    return (
      <div className="clinical-card">
        <h3 className="text-sm font-bold text-foreground mb-4">Care Plans</h3>
        <p className="text-muted-foreground text-sm">
          No care plans yet. Approve an AI recommendation to auto-generate one.
        </p>
      </div>
    )
  }

  const statusColors: Record<string, string> = {
    active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    draft: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    completed: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    revoked: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
    'on-hold': 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300',
  }

  return (
    <div className="clinical-card">
      <h3 className="text-sm font-bold text-foreground mb-4">
        Care Plans ({carePlans.length})
      </h3>
      <div className="space-y-3">
        {carePlans.map((plan: FHIRCarePlanType) => (
          <div
            key={plan.id || plan.fhir_id}
            className="border border-border rounded-lg p-4 bg-card/50"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <ClipboardList className="w-4 h-4 text-primary-500 flex-shrink-0" />
                  <h4 className="text-sm font-semibold text-foreground truncate">{plan.title}</h4>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2 mt-1">{plan.description}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {plan.ai_generated && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300">
                    <BrainCircuit className="w-3 h-3" /> AI
                  </span>
                )}
                <span className={cn(
                  'px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase',
                  statusColors[plan.status] ?? statusColors.draft,
                )}>
                  {plan.status}
                </span>
              </div>
            </div>
            {/* Goals with outcome tracking */}
            {plan.goals?.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Goals</p>
                {plan.goals.map((goal: { description: string; status: string; priority: string; outcome?: string; pre_avg?: number | null; post_avg?: number | null; in_normal_range?: boolean; last_evaluated?: string }, i: number) => (
                  <div key={i} className="space-y-1">
                    <div className="flex items-center gap-2 text-xs text-foreground">
                      <span className={cn(
                        'w-1.5 h-1.5 rounded-full flex-shrink-0',
                        goal.status === 'in-progress' ? 'bg-blue-500' :
                        goal.status === 'achieved' ? 'bg-green-500' :
                        goal.status === 'at-risk' ? 'bg-red-500' : 'bg-gray-400',
                      )} />
                      <span className="flex-1">{goal.description}</span>
                      {goal.outcome && (
                        <span className={cn(
                          'px-1.5 py-0.5 rounded text-[10px] font-semibold',
                          goal.outcome === 'improved' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300' :
                          goal.outcome === 'worsened' ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' :
                          'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
                        )}>
                          {goal.outcome === 'improved' ? 'Improving' : goal.outcome === 'worsened' ? 'Worsening' : 'Stable'}
                        </span>
                      )}
                    </div>
                    {/* Outcome vitals comparison */}
                    {goal.post_avg != null && (
                      <div className="ml-3.5 flex items-center gap-3 text-[10px] text-muted-foreground">
                        {goal.pre_avg != null && (
                          <span>Before: <span className="font-mono font-semibold text-foreground">{goal.pre_avg}</span></span>
                        )}
                        <span>Current: <span className={cn(
                          'font-mono font-semibold',
                          goal.in_normal_range ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400',
                        )}>{goal.post_avg}</span></span>
                        {goal.in_normal_range && <span className="text-green-600 dark:text-green-400">In range</span>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
            {/* Activities */}
            {plan.activities?.length > 0 && (
              <div className="mt-2 space-y-1">
                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Activities</p>
                {plan.activities.map((act: { detail: string; status: string; evidence_level?: string }, i: number) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className={cn(
                      'mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0',
                      act.status === 'completed' ? 'bg-green-500' :
                      act.status === 'needs-escalation' ? 'bg-red-500' :
                      act.status === 'in-progress' ? 'bg-blue-400' : 'bg-primary-400',
                    )} />
                    <span className="flex-1">{act.detail}</span>
                    <div className="flex items-center gap-1">
                      {act.status === 'needs-escalation' && (
                        <span className="text-[10px] font-semibold text-red-600 dark:text-red-400">Escalated</span>
                      )}
                      {act.status === 'completed' && (
                        <span className="text-[10px] font-semibold text-green-600 dark:text-green-400">Done</span>
                      )}
                      {act.evidence_level && (
                        <span className="text-[10px] font-mono text-primary-600">Lv.{act.evidence_level}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {/* Feedback loop monitoring log */}
            {plan.note && plan.ai_generated && (() => {
              const logEntries = plan.note.split('\n').filter((l: string) => l.match(/^\[.*\] (COMPLETED|ESCALATION|MONITORING):/))
              if (logEntries.length === 0) return null
              return (
                <div className="mt-3 border-t border-border pt-2">
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Feedback Loop</p>
                  <div className="space-y-1 max-h-24 overflow-y-auto">
                    {logEntries.slice(-5).map((entry: string, i: number) => {
                      const isCompleted = entry.includes('COMPLETED')
                      const isEscalation = entry.includes('ESCALATION')
                      return (
                        <div key={i} className={cn(
                          'text-[10px] px-2 py-1 rounded',
                          isCompleted ? 'bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300' :
                          isEscalation ? 'bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300' :
                          'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300',
                        )}>
                          {entry.trim()}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })()}
            {/* Period + feedback indicator */}
            <div className="mt-2 flex items-center justify-between">
              <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                {plan.period_start && <span>Start: {plan.period_start}</span>}
                {plan.period_end && <span>End: {plan.period_end}</span>}
                {plan.created && <span>Created: {format(new Date(plan.created), 'MMM d, yyyy')}</span>}
              </div>
              <div className="flex items-center gap-2">
                {plan.goals?.some((g: { last_evaluated?: string }) => g.last_evaluated) && (
                  <span className="text-[10px] text-muted-foreground">
                    Last checked: {format(new Date(plan.goals.find((g: { last_evaluated?: string }) => g.last_evaluated)!.last_evaluated!), 'MMM d, h:mm a')}
                  </span>
                )}
                {plan.status === 'active' && plan.ai_generated && (
                  <span className="text-[10px] text-blue-500 dark:text-blue-400 font-medium">
                    Monitoring vitals...
                  </span>
                )}
                {plan.status === 'completed' && (
                  <span className="text-[10px] text-green-600 dark:text-green-400 font-semibold">
                    Goals achieved
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

interface VitalTarget {
  id: string
  loinc_code: string
  vital_name: string
  unit: string
  target_low: number
  target_high: number
  source: string
  source_guideline: string
  rationale: string
  adherence_rate: number | null
  times_evaluated: number
  times_in_range: number
  is_active: boolean
}

function VitalTargetsSection({ patientId }: { patientId: string }) {
  const { data: targetsData, isLoading } = useVitalTargets(patientId)
  const initTargets = useInitializeVitalTargets()
  const updateTarget = useUpdateVitalTarget()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editLow, setEditLow] = useState('')
  const [editHigh, setEditHigh] = useState('')

  const targets: VitalTarget[] = targetsData?.results ?? targetsData ?? []

  if (isLoading) {
    return (
      <div className="clinical-card">
        <h3 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
          <Target className="w-4 h-4 text-primary-500" /> Vital Target Policies
        </h3>
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading targets...
        </div>
      </div>
    )
  }

  if (targets.length === 0) {
    return (
      <div className="clinical-card">
        <h3 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
          <Target className="w-4 h-4 text-primary-500" /> Vital Target Policies
        </h3>
        <p className="text-muted-foreground text-sm mb-3">
          No personalized vital targets set. The feedback loop will use evidence-based defaults.
        </p>
        <button
          onClick={() => initTargets.mutate(patientId)}
          disabled={initTargets.isPending}
          className="text-xs px-3 py-1.5 rounded-md bg-primary-500 text-white hover:bg-primary-600 disabled:opacity-50"
        >
          {initTargets.isPending ? 'Creating...' : 'Initialize Default Targets'}
        </button>
      </div>
    )
  }

  const sourceColors: Record<string, string> = {
    clinician: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    guideline: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    ai_suggested: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    care_plan: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  }

  const handleEdit = (target: VitalTarget) => {
    setEditingId(target.id)
    setEditLow(String(target.target_low))
    setEditHigh(String(target.target_high))
  }

  const handleSave = (targetId: string) => {
    updateTarget.mutate({
      id: targetId,
      data: {
        target_low: parseFloat(editLow),
        target_high: parseFloat(editHigh),
        source: 'clinician',
      },
    })
    setEditingId(null)
  }

  return (
    <div className="clinical-card">
      <h3 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
        <Target className="w-4 h-4 text-primary-500" />
        Vital Target Policies ({targets.length})
      </h3>
      <div className="space-y-2">
        {targets.map((target: VitalTarget) => (
          <div
            key={target.id}
            className="border border-border rounded-lg p-3 bg-card/50"
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-foreground">{target.vital_name}</span>
                <span className={cn(
                  'px-1.5 py-0.5 rounded text-[10px] font-medium',
                  sourceColors[target.source] ?? sourceColors.guideline,
                )}>
                  {target.source === 'clinician' ? 'Clinician' :
                   target.source === 'ai_suggested' ? 'AI' :
                   target.source === 'care_plan' ? 'Care Plan' : 'Guideline'}
                </span>
              </div>
              <button
                onClick={() => editingId === target.id ? handleSave(target.id) : handleEdit(target)}
                className="text-[10px] text-primary-500 hover:text-primary-600 font-medium flex items-center gap-1"
              >
                <Settings2 className="w-3 h-3" />
                {editingId === target.id ? 'Save' : 'Edit'}
              </button>
            </div>

            {editingId === target.id ? (
              <div className="mt-2 flex items-center gap-2 text-xs">
                <span className="text-muted-foreground">Target:</span>
                <input
                  type="number"
                  value={editLow}
                  onChange={(e) => setEditLow(e.target.value)}
                  className="w-16 px-1.5 py-1 rounded border border-border bg-background text-foreground text-xs"
                  step="0.1"
                />
                <span className="text-muted-foreground">-</span>
                <input
                  type="number"
                  value={editHigh}
                  onChange={(e) => setEditHigh(e.target.value)}
                  className="w-16 px-1.5 py-1 rounded border border-border bg-background text-foreground text-xs"
                  step="0.1"
                />
                <span className="text-muted-foreground">{target.unit}</span>
                <button
                  onClick={() => setEditingId(null)}
                  className="text-[10px] text-muted-foreground hover:text-foreground ml-2"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <div className="mt-1.5 flex items-center gap-4 text-xs">
                <span className="text-muted-foreground">
                  Target: <span className="font-mono font-semibold text-foreground">{target.target_low}-{target.target_high}</span> {target.unit}
                </span>
                {target.adherence_rate != null && (
                  <span className="text-muted-foreground">
                    Adherence: <span className={cn(
                      'font-semibold',
                      target.adherence_rate >= 70 ? 'text-green-600 dark:text-green-400' :
                      target.adherence_rate >= 40 ? 'text-yellow-600 dark:text-yellow-400' :
                      'text-red-600 dark:text-red-400',
                    )}>{target.adherence_rate}%</span>
                    <span className="text-[10px] ml-1">({target.times_in_range}/{target.times_evaluated})</span>
                  </span>
                )}
              </div>
            )}

            {target.source_guideline && (
              <p className="mt-1 text-[10px] text-muted-foreground">{target.source_guideline}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function AgentsTab({ patientId, patientName, recommendations, refetchRecs }: {
  patientId: string
  patientName: string
  recommendations: ReturnType<typeof Array.prototype.slice>
  refetchRecs: () => void
}) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="clinical-card">
          <h3 className="text-sm font-bold text-foreground mb-4">Agent Control</h3>
          <AgentControlPanel patientId={patientId} patientName={patientName} onHITLDecision={refetchRecs} />
        </div>
        <div className="clinical-card">
          <h3 className="text-sm font-bold text-foreground mb-4">AI Recommendations</h3>
          <AIRecommendationPanel recommendations={recommendations} onDecision={refetchRecs} showHITL />
        </div>
      </div>
      {/* Care plans created from approved recommendations */}
      <CarePlansSection patientId={patientId} />
    </div>
  )
}

// ─── Demo Medications ─────────────────────────────────────────────────────────

function generateDemoMedications(patient: PatientSummary): Medication[] {
  const now = new Date()
  const conditions = patient.activeConditions?.map((c) => c.display.toLowerCase()) ?? []

  const allMeds: Medication[] = []
  let id = 0
  const add = (m: Partial<Medication>) =>
    allMeds.push({
      id: `demo-med-${++id}`,
      patientId: patient.id,
      name: '',
      dose: '',
      doseUnit: 'mg',
      frequency: 'once daily',
      route: 'oral',
      prescribedDate: subDays(now, 90 + Math.floor(Math.random() * 200)).toISOString(),
      startDate: subDays(now, 90 + Math.floor(Math.random() * 200)).toISOString(),
      status: 'active',
      adherenceStatus: (['adherent', 'adherent', 'partial', 'adherent'] as const)[id % 4],
      pdc: 0.75 + Math.random() * 0.2,
      lastFillDate: subDays(now, Math.floor(Math.random() * 25)).toISOString(),
      nextRefillDate: subDays(now, -Math.floor(Math.random() * 30)).toISOString(),
      refillsRemaining: Math.floor(Math.random() * 6) + 1,
      daysSupply: 90,
      ...m,
    } as Medication)

  // Diabetes-related
  if (conditions.some((c) => c.includes('diabet'))) {
    add({ name: 'Metformin 500mg', genericName: 'Metformin', dose: '500', frequency: 'twice daily', indication: 'Type 2 Diabetes' })
    add({ name: 'Empagliflozin 10mg', genericName: 'Empagliflozin', brandName: 'Jardiance', dose: '10', indication: 'Type 2 Diabetes', tierLevel: 2 })
  }

  // Hypertension-related
  if (conditions.some((c) => c.includes('hypertens') || c.includes('blood pressure'))) {
    add({ name: 'Lisinopril 10mg', genericName: 'Lisinopril', dose: '10', indication: 'Hypertension' })
    add({ name: 'Amlodipine 5mg', genericName: 'Amlodipine', dose: '5', indication: 'Hypertension' })
  }

  // Heart failure
  if (conditions.some((c) => c.includes('heart failure'))) {
    add({ name: 'Carvedilol 25mg', genericName: 'Carvedilol', dose: '25', frequency: 'twice daily', indication: 'Heart Failure' })
    add({ name: 'Furosemide 40mg', genericName: 'Furosemide', dose: '40', indication: 'Heart Failure' })
  }

  // CKD
  if (conditions.some((c) => c.includes('kidney') || c.includes('ckd') || c.includes('renal'))) {
    add({ name: 'Sodium Bicarbonate 650mg', genericName: 'Sodium Bicarbonate', dose: '650', frequency: 'three times daily', indication: 'CKD' })
  }

  // COPD / Asthma
  if (conditions.some((c) => c.includes('copd') || c.includes('asthma') || c.includes('pulmonary'))) {
    add({ name: 'Tiotropium 18mcg', genericName: 'Tiotropium', brandName: 'Spiriva', dose: '18', doseUnit: 'mcg', route: 'inhalation', indication: 'COPD' })
  }

  // Afib
  if (conditions.some((c) => c.includes('fibrillation') || c.includes('afib'))) {
    add({ name: 'Apixaban 5mg', genericName: 'Apixaban', brandName: 'Eliquis', dose: '5', frequency: 'twice daily', indication: 'Atrial Fibrillation', tierLevel: 3 })
  }

  // CAD / Cholesterol
  if (conditions.some((c) => c.includes('coronary') || c.includes('cholesterol') || c.includes('hyperlipid'))) {
    add({ name: 'Atorvastatin 40mg', genericName: 'Atorvastatin', dose: '40', indication: 'Hyperlipidemia' })
    add({ name: 'Aspirin 81mg', genericName: 'Aspirin', dose: '81', indication: 'CAD prophylaxis' })
  }

  // Default if no conditions matched
  if (allMeds.length === 0) {
    add({ name: 'Metformin 500mg', genericName: 'Metformin', dose: '500', frequency: 'twice daily', indication: 'Type 2 Diabetes' })
    add({ name: 'Lisinopril 10mg', genericName: 'Lisinopril', dose: '10', indication: 'Hypertension' })
    add({ name: 'Atorvastatin 20mg', genericName: 'Atorvastatin', dose: '20', indication: 'Hyperlipidemia' })
  }

  // Add a discontinued med for realism
  add({
    name: 'Glipizide 5mg',
    genericName: 'Glipizide',
    dose: '5',
    status: 'discontinued',
    indication: 'Type 2 Diabetes (switched therapy)',
    endDate: subDays(now, 45).toISOString(),
    adherenceStatus: undefined,
    pdc: undefined,
    nextRefillDate: undefined,
    refillsRemaining: undefined,
  })

  // Add one interaction example
  if (allMeds.length >= 2) {
    allMeds[0].interactions = [{
      id: 'demo-int-1',
      drug1: allMeds[0].name,
      drug2: allMeds[1].name,
      severity: 'moderate',
      description: 'May increase risk of hypoglycemia when used together',
      recommendation: 'Monitor blood glucose closely and adjust doses as needed',
      source: 'DrugBank',
    }]
  }

  return allMeds
}

function MedicationsTab({ medications, patient }: { medications: Medication[]; patient: PatientSummary }) {
  const meds = useMemo(() => {
    if (medications.length > 0) return medications
    return generateDemoMedications(patient)
  }, [medications, patient])

  return <MedicationList medications={meds} />
}

// ─── Research Tab ─────────────────────────────────────────────────────────────

interface TrialResult {
  id: string
  title: string
  abstract?: string
  source: string
  url?: string
  relevanceScore?: number
  trialStatus?: string
  phase?: string
}

function ResearchTab({ patient }: { patient: PatientSummary }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<TrialResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const conditions = patient.activeConditions?.map((c) => c.display) ?? []

  const searchTrials = useCallback(
    async (searchQuery: string) => {
      if (!searchQuery.trim()) return
      setLoading(true)
      setSearched(true)
      try {
        const res = await api.post('/research/search/', {
          query: searchQuery,
          type: 'trials',
        })
        setResults(res.data?.results ?? [])
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  const handleConditionClick = (condition: string) => {
    setQuery(condition)
    searchTrials(condition)
  }

  const statusColor = (s?: string) => {
    if (!s) return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
    const lower = s.toLowerCase()
    if (lower.includes('recruiting')) return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
    if (lower.includes('active')) return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
    if (lower.includes('completed')) return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
    return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
  }

  return (
    <div className="space-y-4">
      {/* Patient conditions as quick-search chips */}
      {conditions.length > 0 && (
        <div className="clinical-card">
          <p className="text-xs font-medium text-muted-foreground mb-2">
            Match trials for active conditions:
          </p>
          <div className="flex flex-wrap gap-2">
            {conditions.map((c) => (
              <button
                key={c}
                onClick={() => handleConditionClick(c)}
                className={cn(
                  'text-xs px-3 py-1.5 rounded-full border transition-colors',
                  query === c
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'bg-muted/50 text-foreground border-border hover:bg-muted',
                )}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search bar */}
      <div className="clinical-card">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            searchTrials(query)
          }}
          className="flex gap-2"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search clinical trials (e.g., diabetes, hypertension)..."
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-border bg-background focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
          </button>
        </form>
      </div>

      {/* Results */}
      {loading && (
        <div className="clinical-card text-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-primary mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">Searching ClinicalTrials.gov...</p>
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <div className="clinical-card text-center py-8">
          <FlaskConical className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No matching trials found. Try a different search term.</p>
        </div>
      )}

      {!loading && results.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground px-1">
            {results.length} trial{results.length !== 1 ? 's' : ''} found
          </p>
          {results.map((trial) => (
            <div
              key={trial.id}
              className="clinical-card cursor-pointer hover:ring-1 hover:ring-primary/20 transition-all"
              onClick={() => setExpandedId(expandedId === trial.id ? null : trial.id)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground leading-snug">{trial.title}</p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    {trial.trialStatus && (
                      <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-full', statusColor(trial.trialStatus))}>
                        {trial.trialStatus}
                      </span>
                    )}
                    {trial.phase && (
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                        {trial.phase}
                      </span>
                    )}
                    <span className="text-[10px] text-muted-foreground">{trial.source}</span>
                    {trial.relevanceScore != null && (
                      <span className="text-[10px] text-muted-foreground">
                        {Math.round(trial.relevanceScore * 100)}% match
                      </span>
                    )}
                  </div>
                </div>
                {trial.url && (
                  <a
                    href={trial.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="shrink-0 p-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                )}
              </div>
              {expandedId === trial.id && trial.abstract && (
                <p className="text-xs text-muted-foreground mt-3 pt-3 border-t border-border leading-relaxed">
                  {trial.abstract}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Empty state — no search yet */}
      {!searched && conditions.length === 0 && (
        <div className="clinical-card text-center py-10">
          <FlaskConical className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm font-medium text-foreground">Clinical Trial Matching</p>
          <p className="text-xs text-muted-foreground mt-1">
            Search for clinical trials relevant to this patient
          </p>
        </div>
      )}
    </div>
  )
}

function SDOHTab() {
  const { patientId } = useParams<{ patientId: string }>()
  const { data: assessments } = useQuery({
    queryKey: ['sdoh', patientId],
    queryFn: async () => {
      try {
        const res = await api.get(`/sdoh/`, { params: { patient: patientId } })
        return res.data?.results ?? res.data ?? []
      } catch { return null }
    },
    retry: false,
  })

  const domains = [
    { key: 'food_security', label: 'Food Security', desc: 'Access to nutritious food', icon: '🥗', risk: 'low' },
    { key: 'housing_stability', label: 'Housing Stability', desc: 'Safe and stable housing', icon: '🏠', risk: 'low' },
    { key: 'transportation', label: 'Transportation', desc: 'Access to medical appointments', icon: '🚗', risk: 'medium' },
    { key: 'financial_strain', label: 'Financial Strain', desc: 'Ability to afford care and medication', icon: '💰', risk: 'high' },
    { key: 'social_isolation', label: 'Social Isolation', desc: 'Social support network', icon: '👥', risk: 'medium' },
    { key: 'education_literacy', label: 'Health Literacy', desc: 'Understanding of health information', icon: '📚', risk: 'low' },
    { key: 'safety', label: 'Personal Safety', desc: 'Physical safety at home', icon: '🛡️', risk: 'low' },
    { key: 'substance_use', label: 'Substance Use', desc: 'Tobacco, alcohol, drug use', icon: '⚠️', risk: 'low' },
  ]

  const riskColors: Record<string, string> = {
    low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 border-green-200',
    medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 border-yellow-200',
    high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-200',
  }

  const sdohData = assessments && assessments.length > 0 ? assessments : null

  return (
    <div className="space-y-6">
      <div className="clinical-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-foreground">SDOH Assessment</h3>
          <button className="text-xs px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
            + New Assessment
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {domains.map((domain) => {
            const risk = sdohData?.[0]?.[domain.key]?.risk ?? domain.risk
            return (
              <div key={domain.key} className={`p-3 rounded-lg border ${riskColors[risk]}`}>
                <div className="flex items-start gap-3">
                  <span className="text-xl">{domain.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <p className="font-medium text-sm">{domain.label}</p>
                      <span className="text-xs font-medium capitalize">{risk} risk</span>
                    </div>
                    <p className="text-xs opacity-75 mt-0.5">{domain.desc}</p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
        {!sdohData && (
          <p className="text-xs text-muted-foreground mt-3 text-center italic">
            Showing default values. Click &quot;New Assessment&quot; to record actual SDOH data.
          </p>
        )}
      </div>
      <div className="clinical-card">
        <h3 className="text-sm font-bold text-foreground mb-3">Community Resources</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { name: 'Local Food Bank', type: 'Food Security', phone: '(555) 123-4567' },
            { name: 'Patient Transport Services', type: 'Transportation', phone: '(555) 234-5678' },
            { name: 'Financial Assistance Program', type: 'Financial', phone: '(555) 345-6789' },
          ].map(r => (
            <div key={r.name} className="p-3 bg-muted rounded-lg text-sm">
              <p className="font-medium">{r.name}</p>
              <p className="text-xs text-muted-foreground">{r.type}</p>
              <p className="text-xs text-primary-600 mt-1">{r.phone}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function DocumentsTab() {
  const { patientId } = useParams<{ patientId: string }>()
  const { data: docs } = useQuery({
    queryKey: ['patient-docs', patientId],
    queryFn: async () => {
      try {
        const res = await api.get(`/fhir/DocumentReference/`, { params: { patient: patientId, _count: 20 } })
        return res.data?.results ?? res.data?.entry ?? []
      } catch { return null }
    },
    retry: false,
  })

  const placeholderDocs = [
    { id: 'd1', title: 'Lab Report - Comprehensive Metabolic Panel', type: 'Lab Report', date: '2026-02-28', status: 'Final', author: 'Dr. Williams' },
    { id: 'd2', title: 'Discharge Summary - February Admission', type: 'Discharge Summary', date: '2026-02-15', status: 'Final', author: 'Dr. Patel' },
    { id: 'd3', title: 'Radiology Report - Chest X-Ray', type: 'Imaging Report', date: '2026-02-10', status: 'Final', author: 'Dr. Chen' },
    { id: 'd4', title: 'Care Plan - Diabetes Management', type: 'Care Plan', date: '2026-01-20', status: 'Active', author: 'Dr. Williams' },
    { id: 'd5', title: 'Consent Form - Research Study', type: 'Consent', date: '2026-01-15', status: 'Signed', author: 'Patient' },
  ]

  const docList = docs && docs.length > 0 ? docs : placeholderDocs

  return (
    <div className="space-y-4">
      <div className="clinical-card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-bold text-foreground">Patient Documents</h3>
          <button className="text-xs px-3 py-1.5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
            + Upload Document
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left p-3 font-medium text-muted-foreground">Document</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Type</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Date</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Status</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Author</th>
                <th className="text-left p-3 font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {docList.map((doc: Record<string, string>) => (
                <tr key={doc.id} className="hover:bg-muted/50 transition-colors">
                  <td className="p-3 font-medium flex items-center gap-2">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    {doc.title}
                  </td>
                  <td className="p-3 text-muted-foreground">{doc.type}</td>
                  <td className="p-3 text-muted-foreground">{doc.date}</td>
                  <td className="p-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      doc.status === 'Active' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300' :
                      doc.status === 'Signed' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300' :
                      'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300'
                    }`}>{doc.status}</span>
                  </td>
                  <td className="p-3 text-muted-foreground">{doc.author}</td>
                  <td className="p-3">
                    <button className="text-xs px-2 py-1 bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 rounded hover:bg-primary-200 transition-colors">
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
