import { useState, useMemo } from 'react'
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
} from 'lucide-react'
import { format, subDays, subHours, subMinutes } from 'date-fns'
import api from '@/services/api'
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
          <MedicationList medications={medications ?? []} />
        )}
        {activeTab === 'clinical' && (
          <ClinicalTab careGaps={careGaps ?? []} patientId={patientId!} />
        )}
        {activeTab === 'agents' && (
          <AgentsTab patientId={patientId!} patientName={`${patient.firstName} ${patient.lastName}`} recommendations={recommendations ?? []} refetchRecs={refetchRecs} />
        )}
        {activeTab === 'research' && (
          <ResearchTabSimple />
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

function ClinicalTab({ careGaps, patientId }: { careGaps: CareGap[]; patientId: string }) {
  return (
    <div className="clinical-card">
      <h3 className="text-sm font-bold text-foreground mb-4">Care Gaps & Quality Measures</h3>
      <CareGapList careGaps={careGaps} patientId={patientId} />
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
  )
}

function ResearchTabSimple() {
  return (
    <div className="clinical-card text-center py-12">
      <FlaskConical className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
      <p className="text-sm font-medium text-foreground">Clinical Trial Matching</p>
      <p className="text-xs text-muted-foreground mt-1">
        Visit the Research page to find clinical trials for this patient
      </p>
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
