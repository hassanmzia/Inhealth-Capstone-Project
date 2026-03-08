import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Users,
  AlertTriangle,
  BrainCircuit,
  ClipboardCheck,
  TrendingUp,
  TrendingDown,
  Calendar,
  Sparkles,
  ArrowRight,
} from 'lucide-react'
import { format, subDays, subHours, subMinutes } from 'date-fns'
import { useAuthStore } from '@/store/authStore'
import { useAlertStore } from '@/store/alertStore'
import { useAgentStore, selectTotalActiveAgents } from '@/store/agentStore'
import { getRecommendations } from '@/services/agents'
import api from '@/services/api'
import AIRecommendationPanel from '@/components/clinical/AIRecommendationPanel'
import PopulationRiskPyramid from '@/components/charts/PopulationRiskPyramid'
import AgentActivityTimeline from '@/components/charts/AgentActivityTimeline'
import { cn } from '@/lib/utils'
import type { PatientSummary, ClinicalAlert, RiskCategory } from '@/types/clinical'
import type { AgentExecution } from '@/types/agent'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } }
const ITEM = { hidden: { opacity: 0, y: 16 }, show: { opacity: 1, y: 0, transition: { ease: [0.4, 0, 0.2, 1] } } }

interface DashboardStats {
  totalPatients: number
  criticalAlerts: number
  activeAgents: number
  openCareGaps: number
  trends: {
    patients: number
    alerts: number
    careGaps: number
  }
  riskDistribution: { critical: number; high: number; medium: number; low: number; total: number }
}

export default function ClinicianDashboard() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { alerts } = useAlertStore()
  const activeAgents = useAgentStore(selectTotalActiveAgents)
  const { executions } = useAgentStore()
  const displayExecutions = useMemo(() => {
    if (executions.length > 0) return executions.slice(0, 100)
    return DEMO_EXECUTIONS
  }, [executions])

  const { data: statsRaw } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get('/dashboard/stats/').then((r) => r.data),
    refetchInterval: 30000,
    placeholderData: DEMO_STATS,
  })
  const stats = useMemo(() => {
    if (!statsRaw || (statsRaw.totalPatients === 0 && statsRaw.riskDistribution?.total === 0)) {
      return DEMO_STATS
    }
    return statsRaw
  }, [statsRaw])

  const { data: riskPatientsRaw } = useQuery<PatientSummary[]>({
    queryKey: ['high-risk-patients'],
    queryFn: () => api.get('/patients/?risk_level=critical,high&limit=10').then((r) => r.data?.results ?? []),
    placeholderData: [],
  })
  const riskPatients = useMemo(() => {
    if (riskPatientsRaw && riskPatientsRaw.length > 0) return riskPatientsRaw
    return DEMO_HIGH_RISK_PATIENTS
  }, [riskPatientsRaw])

  const { data: recommendations, refetch: refetchRecs } = useQuery({
    queryKey: ['recent-recommendations'],
    queryFn: () => getRecommendations(undefined, 'pending', 5),
    placeholderData: [],
  })

  const criticalAlerts = alerts.filter((a) => a.severity === 'critical' && !a.isAcknowledged)

  const STAT_CARDS = [
    {
      label: 'Total Patients',
      value: stats?.totalPatients.toLocaleString() ?? '—',
      icon: Users,
      gradient: 'from-primary-500 to-primary-700',
      trend: stats?.trends.patients,
      href: '/patients',
    },
    {
      label: 'Critical Alerts',
      value: criticalAlerts.length,
      icon: AlertTriangle,
      gradient: 'from-danger-500 to-danger-700',
      trend: stats?.trends.alerts,
      href: '/alerts',
      pulse: criticalAlerts.length > 0,
    },
    {
      label: 'Active Agents',
      value: activeAgents,
      icon: BrainCircuit,
      gradient: 'from-secondary-500 to-secondary-700',
      href: '/agents',
    },
    {
      label: 'Open Care Gaps',
      value: stats?.openCareGaps.toLocaleString() ?? '—',
      icon: ClipboardCheck,
      gradient: 'from-warning-500 to-warning-700',
      trend: stats?.trends.careGaps,
    },
  ]

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-[1600px] mx-auto">
      {/* Welcome header */}
      <motion.div variants={ITEM} className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">
            Good {getGreeting()}, Dr. {user?.lastName}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {format(new Date(), 'EEEE, MMMM d, yyyy')} · {user?.specialty ?? 'Clinician Dashboard'}
          </p>
        </div>
        {criticalAlerts.length > 0 && (
          <button
            onClick={() => navigate('/alerts')}
            className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-danger-600 to-danger-700 hover:from-danger-700 hover:to-danger-800 text-white rounded-xl text-sm font-semibold shadow-lg shadow-danger-500/20 transition-all hover:shadow-xl hover:shadow-danger-500/25 active:scale-[0.98]"
          >
            <AlertTriangle className="w-4 h-4" />
            {criticalAlerts.length} Critical Alert{criticalAlerts.length !== 1 ? 's' : ''}
          </button>
        )}
      </motion.div>

      {/* Stat cards — vibrant gradient */}
      <motion.div variants={ITEM} className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {STAT_CARDS.map((card) => (
          <button
            key={card.label}
            onClick={() => card.href && navigate(card.href)}
            className={cn(
              'relative overflow-hidden rounded-2xl p-4 sm:p-5 text-left text-white transition-all duration-300 bg-gradient-to-br',
              card.gradient,
              card.href && 'cursor-pointer hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0 active:shadow-md',
              card.pulse && 'animate-alert-pulse',
            )}
          >
            {/* Decorative circles */}
            <div className="absolute -right-4 -top-4 w-24 h-24 rounded-full bg-white/10" />
            <div className="absolute -right-2 -bottom-6 w-16 h-16 rounded-full bg-white/5" />

            <div className="relative">
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 rounded-xl bg-white/20">
                  <card.icon className="w-4 h-4 sm:w-5 sm:h-5" />
                </div>
                {card.trend !== undefined && (
                  <div className="flex items-center gap-0.5 text-[11px] font-semibold rounded-full px-2 py-0.5 bg-white/20">
                    {card.trend < 0 ? <TrendingDown className="w-3 h-3" /> : <TrendingUp className="w-3 h-3" />}
                    {Math.abs(card.trend)}%
                  </div>
                )}
              </div>
              <p className="text-2xl sm:text-3xl font-bold font-mono tabular-nums tracking-tight">{card.value}</p>
              <p className="text-xs sm:text-sm text-white/80 mt-1 font-medium">{card.label}</p>
            </div>
          </button>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-4 sm:space-y-6">
          {/* High risk patients */}
          <motion.div variants={ITEM} className="clinical-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-foreground">High Risk Patients</h2>
              <button
                onClick={() => navigate('/patients?risk=critical,high')}
                className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium transition-colors"
              >
                View all <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="overflow-x-auto -mx-5 px-5">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border/60">
                    {['Patient', 'Condition', 'Risk Score', 'Care Gaps', 'Last Contact', 'Status'].map((h) => (
                      <th key={h} className="pb-3 text-left font-semibold text-muted-foreground whitespace-nowrap pr-4 text-[11px] uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {riskPatients.map((patient) => (
                    <PatientRiskRow key={patient.id} patient={patient} />
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>

          {/* Alert feed */}
          <motion.div variants={ITEM} className="clinical-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-foreground">Recent Alerts</h2>
              <button
                onClick={() => navigate('/alerts')}
                className="flex items-center gap-1 text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 font-medium transition-colors"
              >
                View all <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <AlertFeed alerts={alerts.slice(0, 6)} />
          </motion.div>

          {/* Agent activity */}
          <motion.div variants={ITEM} className="clinical-card">
            <h2 className="text-sm font-bold text-foreground mb-4">Agent Activity (24h)</h2>
            <AgentActivityTimeline executions={displayExecutions} height={220} />
          </motion.div>
        </div>

        {/* Right column */}
        <div className="space-y-4 sm:space-y-6">
          {/* Population risk */}
          <motion.div variants={ITEM} className="clinical-card">
            <h2 className="text-sm font-bold text-foreground mb-4">Population Risk Distribution</h2>
            <PopulationRiskPyramid
              data={stats?.riskDistribution ?? { critical: 0, high: 0, medium: 0, low: 0, total: 0 }}
            />
          </motion.div>

          {/* AI Recommendations */}
          <motion.div variants={ITEM} className="clinical-card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-gradient-to-br from-primary-500/20 to-purple-500/20">
                  <Sparkles className="w-4 h-4 text-primary-500" />
                </div>
                <h2 className="text-sm font-bold text-foreground">AI Recommendations</h2>
              </div>
              <span className="text-[10px] font-bold text-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-purple-400 px-2 py-0.5 rounded-full border border-purple-200/50 dark:border-purple-800/50">
                Pending Review
              </span>
            </div>
            <AIRecommendationPanel
              recommendations={recommendations ?? []}
              onDecision={() => refetchRecs()}
              showHITL
              maxItems={5}
            />
          </motion.div>

          {/* Upcoming appointments */}
          <motion.div variants={ITEM} className="clinical-card">
            <div className="flex items-center gap-2 mb-4">
              <div className="p-1.5 rounded-lg bg-primary-50 dark:bg-primary-900/20">
                <Calendar className="w-4 h-4 text-primary-500" />
              </div>
              <h2 className="text-sm font-bold text-foreground">Today's Appointments</h2>
            </div>
            <UpcomingAppointments />
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}

// ─── Helper Components ────────────────────────────────────────────────────────

function PatientRiskRow({ patient }: { patient: PatientSummary }) {
  const navigate = useNavigate()
  const riskScore = patient.riskScore?.score ?? 0
  const riskCategory = patient.riskScore?.category ?? 'low'

  const riskColor = riskCategory === 'critical' ? 'text-danger-600 dark:text-danger-400' : riskCategory === 'high' ? 'text-orange-600 dark:text-orange-400' : riskCategory === 'medium' ? 'text-warning-600 dark:text-warning-400' : 'text-secondary-600 dark:text-secondary-400'

  return (
    <tr
      className="hover:bg-accent/50 cursor-pointer transition-colors group"
      onClick={() => navigate(`/patients/${patient.id}`)}
    >
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white text-[10px] font-bold flex-shrink-0">
            {patient.firstName?.[0]}{patient.lastName?.[0]}
          </div>
          <div>
            <p className="font-semibold text-foreground group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">{patient.firstName} {patient.lastName}</p>
            <p className="text-muted-foreground font-mono text-[10px]">{patient.mrn}</p>
          </div>
        </div>
      </td>
      <td className="py-3 pr-4">
        <p className="text-foreground truncate max-w-[120px]">
          {patient.activeConditions[0]?.display ?? '—'}
        </p>
      </td>
      <td className="py-3 pr-4">
        <span className={cn('font-mono font-bold', riskColor)}>
          {Math.round(riskScore)}%
        </span>
      </td>
      <td className="py-3 pr-4">
        {patient.openCareGaps > 0 ? (
          <span className="font-semibold text-warning-600 dark:text-warning-400">{patient.openCareGaps}</span>
        ) : (
          <span className="text-secondary-600 dark:text-secondary-400">0</span>
        )}
      </td>
      <td className="py-3 pr-4">
        <span className="text-muted-foreground">
          {patient.lastContactDate
            ? format(new Date(patient.lastContactDate), 'MMM d')
            : '—'}
        </span>
      </td>
      <td className="py-3">
        <AlertStatusBadge status={patient.alertStatus} />
      </td>
    </tr>
  )
}

function AlertStatusBadge({ status }: { status: string }) {
  switch (status) {
    case 'critical':
      return <span className="risk-badge-critical">{status}</span>
    case 'warning':
      return <span className="risk-badge-medium">{status}</span>
    default:
      return <span className="risk-badge-low">stable</span>
  }
}

function AlertFeed({ alerts }: { alerts: ClinicalAlert[] }) {
  if (!alerts.length) {
    return <p className="text-sm text-muted-foreground text-center py-6">No recent alerts</p>
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={cn(
            'flex items-start gap-3 p-3 rounded-xl border text-xs transition-colors',
            alert.severity === 'critical'
              ? 'border-danger-200/60 dark:border-danger-800/60 bg-danger-50/40 dark:bg-danger-900/10'
              : alert.severity === 'urgent'
              ? 'border-warning-200/60 dark:border-warning-800/60 bg-warning-50/40 dark:bg-warning-900/10'
              : 'border-border/40 bg-card',
          )}
        >
          <div className={cn(
            'p-1.5 rounded-lg flex-shrink-0',
            alert.severity === 'critical' ? 'bg-danger-100 dark:bg-danger-900/30' : alert.severity === 'urgent' ? 'bg-warning-100 dark:bg-warning-900/30' : 'bg-muted',
          )}>
            <AlertTriangle className={cn('w-3 h-3', alert.severity === 'critical' ? 'text-danger-500' : alert.severity === 'urgent' ? 'text-warning-500' : 'text-muted-foreground')} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-foreground">{alert.title}</p>
            <p className="text-muted-foreground truncate mt-0.5">{alert.patientName} · {alert.description}</p>
          </div>
          {!alert.isRead && (
            <span className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0 mt-1" />
          )}
        </div>
      ))}
    </div>
  )
}

function UpcomingAppointments() {
  const mockAppts = [
    { time: '09:00 AM', patient: 'Maria Garcia', type: 'Follow-up', virtual: false },
    { time: '10:30 AM', patient: 'James Wilson', type: 'Diabetes Mgmt', virtual: true },
    { time: '02:00 PM', patient: 'Sarah Chen', type: 'New Patient', virtual: false },
    { time: '03:30 PM', patient: 'Robert Kim', type: 'HbA1c Review', virtual: true },
  ]

  return (
    <div className="space-y-1">
      {mockAppts.map((appt, i) => (
        <div key={i} className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-accent/50 transition-colors cursor-pointer group">
          <div className="text-right w-16 flex-shrink-0">
            <p className="text-xs font-mono font-semibold text-foreground">{appt.time}</p>
          </div>
          <div className="w-px h-8 bg-border/60 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-foreground group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">{appt.patient}</p>
            <p className="text-[10px] text-muted-foreground">{appt.type}</p>
          </div>
          {appt.virtual && (
            <span className="text-[10px] font-bold text-primary-600 bg-primary-50 dark:bg-primary-900/20 dark:text-primary-400 px-2 py-0.5 rounded-full border border-primary-200/50 dark:border-primary-800/50">
              Virtual
            </span>
          )}
        </div>
      ))}
    </div>
  )
}

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'morning'
  if (hour < 17) return 'afternoon'
  return 'evening'
}

// ─── Demo Data ────────────────────────────────────────────────────────────────

const DEMO_STATS: DashboardStats = {
  totalPatients: 1284,
  criticalAlerts: 7,
  activeAgents: 3,
  openCareGaps: 342,
  trends: { patients: 3.2, alerts: -12, careGaps: -8 },
  riskDistribution: { critical: 47, high: 183, medium: 521, low: 533, total: 1284 },
}

const now = new Date()

const DEMO_HIGH_RISK_PATIENTS: PatientSummary[] = [
  {
    id: 'demo-p1', mrn: 'MRN001', firstName: 'James', lastName: 'Morrison', dateOfBirth: '1958-03-15', age: 67, gender: 'male',
    activeConditions: [{ code: 'E11', display: 'Type 2 Diabetes' }, { code: 'I10', display: 'Hypertension' }, { code: 'N18.3', display: 'CKD Stage 3' }],
    riskScore: { id: 'rs1', patientId: 'demo-p1', type: 'composite', score: 89, category: 'critical' as RiskCategory, calculatedAt: now.toISOString(), model: 'InHealth-Risk-v2', modelVersion: '2.1', confidence: 92 },
    openCareGaps: 4, lastContactDate: subDays(now, 3).toISOString(), alertStatus: 'critical', alertCount: 2, isActive: true, tenantId: 'demo', createdAt: now.toISOString(), updatedAt: now.toISOString(),
  },
  {
    id: 'demo-p2', mrn: 'MRN002', firstName: 'Maria', lastName: 'Gonzalez', dateOfBirth: '1965-07-22', age: 60, gender: 'female',
    activeConditions: [{ code: 'I50', display: 'Heart Failure' }, { code: 'I10', display: 'Hypertension' }],
    riskScore: { id: 'rs2', patientId: 'demo-p2', type: 'composite', score: 82, category: 'critical' as RiskCategory, calculatedAt: now.toISOString(), model: 'InHealth-Risk-v2', modelVersion: '2.1', confidence: 88 },
    openCareGaps: 3, lastContactDate: subDays(now, 7).toISOString(), alertStatus: 'warning', alertCount: 1, isActive: true, tenantId: 'demo', createdAt: now.toISOString(), updatedAt: now.toISOString(),
  },
  {
    id: 'demo-p3', mrn: 'MRN003', firstName: 'Robert', lastName: 'Chen', dateOfBirth: '1952-11-08', age: 73, gender: 'male',
    activeConditions: [{ code: 'E11', display: 'Type 2 Diabetes' }, { code: 'I25', display: 'Coronary Artery Disease' }],
    riskScore: { id: 'rs3', patientId: 'demo-p3', type: 'composite', score: 76, category: 'high' as RiskCategory, calculatedAt: now.toISOString(), model: 'InHealth-Risk-v2', modelVersion: '2.1', confidence: 85 },
    openCareGaps: 2, lastContactDate: subDays(now, 14).toISOString(), alertStatus: 'warning', alertCount: 1, isActive: true, tenantId: 'demo', createdAt: now.toISOString(), updatedAt: now.toISOString(),
  },
  {
    id: 'demo-p4', mrn: 'MRN004', firstName: 'Dorothy', lastName: 'Williams', dateOfBirth: '1960-04-19', age: 65, gender: 'female',
    activeConditions: [{ code: 'J44', display: 'COPD' }, { code: 'I48', display: 'Atrial Fibrillation' }],
    riskScore: { id: 'rs4', patientId: 'demo-p4', type: 'composite', score: 71, category: 'high' as RiskCategory, calculatedAt: now.toISOString(), model: 'InHealth-Risk-v2', modelVersion: '2.1', confidence: 81 },
    openCareGaps: 3, lastContactDate: subDays(now, 5).toISOString(), alertStatus: 'normal', alertCount: 0, isActive: true, tenantId: 'demo', createdAt: now.toISOString(), updatedAt: now.toISOString(),
  },
  {
    id: 'demo-p5', mrn: 'MRN005', firstName: 'William', lastName: 'Jackson', dateOfBirth: '1955-09-30', age: 70, gender: 'male',
    activeConditions: [{ code: 'E11', display: 'Type 2 Diabetes' }, { code: 'N18.4', display: 'CKD Stage 4' }],
    riskScore: { id: 'rs5', patientId: 'demo-p5', type: 'composite', score: 85, category: 'critical' as RiskCategory, calculatedAt: now.toISOString(), model: 'InHealth-Risk-v2', modelVersion: '2.1', confidence: 90 },
    openCareGaps: 5, lastContactDate: subDays(now, 10).toISOString(), alertStatus: 'critical', alertCount: 3, isActive: true, tenantId: 'demo', createdAt: now.toISOString(), updatedAt: now.toISOString(),
  },
  {
    id: 'demo-p6', mrn: 'MRN006', firstName: 'Linda', lastName: 'Nguyen', dateOfBirth: '1963-01-12', age: 63, gender: 'female',
    activeConditions: [{ code: 'I50', display: 'Heart Failure' }, { code: 'E11', display: 'Type 2 Diabetes' }],
    riskScore: { id: 'rs6', patientId: 'demo-p6', type: 'composite', score: 68, category: 'high' as RiskCategory, calculatedAt: now.toISOString(), model: 'InHealth-Risk-v2', modelVersion: '2.1', confidence: 79 },
    openCareGaps: 2, lastContactDate: subDays(now, 2).toISOString(), alertStatus: 'normal', alertCount: 0, isActive: true, tenantId: 'demo', createdAt: now.toISOString(), updatedAt: now.toISOString(),
  },
]

const DEMO_EXECUTIONS: AgentExecution[] = [
  { id: 'demo-e1', agentId: 'vital_signs_agent', agentName: 'Vital Sign Monitor', tier: 'tier1_ingestion', status: 'completed', patientId: 'demo-p1', patientName: 'James Morrison', triggeredBy: 'system', triggeredAt: subMinutes(now, 15).toISOString(), startedAt: subMinutes(now, 15).toISOString(), completedAt: subMinutes(now, 14).toISOString(), runtimeSeconds: 4.2 },
  { id: 'demo-e2', agentId: 'risk_stratification_agent', agentName: 'Risk Stratification', tier: 'tier2_analysis', status: 'completed', triggeredBy: 'scheduler', triggeredAt: subMinutes(now, 45).toISOString(), startedAt: subMinutes(now, 45).toISOString(), completedAt: subMinutes(now, 43).toISOString(), runtimeSeconds: 12.8 },
  { id: 'demo-e3', agentId: 'care_gap_detection_agent', agentName: 'Care Gap Detector', tier: 'tier3_clinical', status: 'completed', patientId: 'demo-p5', patientName: 'William Jackson', triggeredBy: 'system', triggeredAt: subHours(now, 1).toISOString(), startedAt: subHours(now, 1).toISOString(), completedAt: subMinutes(subHours(now, 1), -2).toISOString(), runtimeSeconds: 8.1 },
  { id: 'demo-e4', agentId: 'medication_adherence_agent', agentName: 'Medication Adherence', tier: 'tier3_clinical', status: 'completed', patientId: 'demo-p3', patientName: 'Robert Chen', triggeredBy: 'system', triggeredAt: subHours(now, 2).toISOString(), startedAt: subHours(now, 2).toISOString(), completedAt: subMinutes(subHours(now, 2), -1).toISOString(), runtimeSeconds: 5.3 },
  { id: 'demo-e5', agentId: 'fhir_ingestion_agent', agentName: 'FHIR Data Ingestion', tier: 'tier1_ingestion', status: 'completed', triggeredBy: 'scheduler', triggeredAt: subHours(now, 3).toISOString(), startedAt: subHours(now, 3).toISOString(), completedAt: subMinutes(subHours(now, 3), -5).toISOString(), runtimeSeconds: 31.4 },
  { id: 'demo-e6', agentId: 'notification_agent', agentName: 'Patient Outreach', tier: 'tier5_engagement', status: 'pending_hitl', patientId: 'demo-p2', patientName: 'Maria Gonzalez', triggeredBy: 'care_gap_detection_agent', triggeredAt: subHours(now, 4).toISOString(), startedAt: subHours(now, 4).toISOString(), runtimeSeconds: 2.1 },
  { id: 'demo-e7', agentId: 'ehr_sync_agent', agentName: 'EHR Sync', tier: 'tier1_ingestion', status: 'completed', triggeredBy: 'scheduler', triggeredAt: subHours(now, 6).toISOString(), startedAt: subHours(now, 6).toISOString(), completedAt: subMinutes(subHours(now, 6), -3).toISOString(), runtimeSeconds: 18.7 },
  { id: 'demo-e8', agentId: 'predictive_analytics_agent', agentName: 'Readmission Predictor', tier: 'tier2_analysis', status: 'completed', patientId: 'demo-p1', patientName: 'James Morrison', triggeredBy: 'risk_stratification_agent', triggeredAt: subHours(now, 8).toISOString(), startedAt: subHours(now, 8).toISOString(), completedAt: subMinutes(subHours(now, 8), -1).toISOString(), runtimeSeconds: 6.9 },
  { id: 'demo-e9', agentId: 'population_health_agent', agentName: 'HEDIS Quality Measure', tier: 'tier2_analysis', status: 'failed', triggeredBy: 'scheduler', triggeredAt: subHours(now, 10).toISOString(), startedAt: subHours(now, 10).toISOString(), completedAt: subMinutes(subHours(now, 10), -1).toISOString(), runtimeSeconds: 3.2, error: 'Timeout fetching external measure definitions' },
  { id: 'demo-e10', agentId: 'vital_signs_agent', agentName: 'Vital Sign Monitor', tier: 'tier1_ingestion', status: 'running', patientId: 'demo-p4', patientName: 'Dorothy Williams', triggeredBy: 'system', triggeredAt: subMinutes(now, 2).toISOString(), startedAt: subMinutes(now, 2).toISOString() },
]
