import { useEffect } from 'react'
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
} from 'lucide-react'
import { format, addDays } from 'date-fns'
import { useAuthStore } from '@/store/authStore'
import { useAlertStore } from '@/store/alertStore'
import { useAgentStore, selectTotalActiveAgents } from '@/store/agentStore'
import { getAllAgentStatuses, getRecommendations } from '@/services/agents'
import api from '@/services/api'
import AIRecommendationPanel from '@/components/clinical/AIRecommendationPanel'
import PopulationRiskPyramid from '@/components/charts/PopulationRiskPyramid'
import AgentActivityTimeline from '@/components/charts/AgentActivityTimeline'
import { cn } from '@/lib/utils'
import type { PatientSummary, ClinicalAlert } from '@/types/clinical'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.06 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

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

  // Fetch dashboard stats
  const { data: stats } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get('/dashboard/stats/').then((r) => r.data),
    refetchInterval: 30000,
    placeholderData: {
      totalPatients: 1284,
      criticalAlerts: 7,
      activeAgents: activeAgents,
      openCareGaps: 342,
      trends: { patients: 3.2, alerts: -12, careGaps: -8 },
      riskDistribution: { critical: 47, high: 183, medium: 521, low: 533, total: 1284 },
    },
  })

  // Fetch recent patients by risk
  const { data: riskPatients } = useQuery<PatientSummary[]>({
    queryKey: ['high-risk-patients'],
    queryFn: () => api.get('/patients/?risk_level=critical,high&limit=10').then((r) => r.data?.results ?? []),
    placeholderData: [],
  })

  // Fetch AI recommendations
  const { data: recommendations, refetch: refetchRecs } = useQuery({
    queryKey: ['recent-recommendations'],
    queryFn: () => getRecommendations(undefined, 'pending', 5),
    placeholderData: [],
  })

  // Fetch upcoming appointments
  const { data: appointments } = useQuery({
    queryKey: ['upcoming-appointments'],
    queryFn: () => api.get('/appointments/?status=booked&limit=5').then((r) => r.data?.results ?? []),
    placeholderData: [],
  })

  const criticalAlerts = alerts.filter((a) => a.severity === 'critical' && !a.isAcknowledged)

  const STAT_CARDS = [
    {
      label: 'Total Patients',
      value: stats?.totalPatients.toLocaleString() ?? '—',
      icon: Users,
      color: 'text-primary-600 dark:text-primary-400',
      bg: 'bg-primary-50 dark:bg-primary-900/20',
      trend: stats?.trends.patients,
      href: '/patients',
    },
    {
      label: 'Critical Alerts',
      value: criticalAlerts.length,
      icon: AlertTriangle,
      color: 'text-danger-600 dark:text-danger-400',
      bg: 'bg-danger-50 dark:bg-danger-900/20',
      trend: stats?.trends.alerts,
      href: '/alerts',
      pulse: criticalAlerts.length > 0,
    },
    {
      label: 'Active Agents',
      value: activeAgents,
      icon: BrainCircuit,
      color: 'text-secondary-600 dark:text-secondary-400',
      bg: 'bg-secondary-50 dark:bg-secondary-900/20',
      href: '/agents',
    },
    {
      label: 'Open Care Gaps',
      value: stats?.openCareGaps.toLocaleString() ?? '—',
      icon: ClipboardCheck,
      color: 'text-warning-600 dark:text-warning-400',
      bg: 'bg-warning-50 dark:bg-warning-900/20',
      trend: stats?.trends.careGaps,
    },
  ]

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-7xl">
      {/* Welcome header */}
      <motion.div variants={ITEM} className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Good {getGreeting()}, Dr. {user?.lastName}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {format(new Date(), 'EEEE, MMMM d, yyyy')} · {user?.specialty ?? 'Clinician Dashboard'}
          </p>
        </div>
        {criticalAlerts.length > 0 && (
          <button
            onClick={() => navigate('/alerts')}
            className="flex items-center gap-2 px-4 py-2 bg-danger-600 hover:bg-danger-700 text-white rounded-lg text-sm font-semibold animate-alert-pulse transition-colors"
          >
            <AlertTriangle className="w-4 h-4" />
            {criticalAlerts.length} Critical Alert{criticalAlerts.length !== 1 ? 's' : ''}
          </button>
        )}
      </motion.div>

      {/* Stat cards */}
      <motion.div variants={ITEM} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CARDS.map((card) => (
          <button
            key={card.label}
            onClick={() => card.href && navigate(card.href)}
            className={cn(
              'clinical-card text-left hover:shadow-card-hover transition-all duration-200',
              card.href && 'cursor-pointer',
              card.pulse && 'animate-alert-pulse',
            )}
          >
            <div className="flex items-center justify-between mb-3">
              <div className={cn('p-2 rounded-lg', card.bg)}>
                <card.icon className={cn('w-5 h-5', card.color)} />
              </div>
              {card.trend !== undefined && (
                <div className={cn('flex items-center gap-1 text-xs font-medium', card.trend < 0 ? 'text-secondary-600' : 'text-danger-600')}>
                  {card.trend < 0 ? <TrendingDown className="w-3.5 h-3.5" /> : <TrendingUp className="w-3.5 h-3.5" />}
                  {Math.abs(card.trend)}%
                </div>
              )}
            </div>
            <p className="text-2xl font-bold text-foreground font-mono tabular-nums">{card.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{card.label}</p>
          </button>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column: Risk table + Alerts */}
        <div className="lg:col-span-2 space-y-6">
          {/* High risk patients */}
          <motion.div variants={ITEM} className="clinical-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-foreground">High Risk Patients</h2>
              <button
                onClick={() => navigate('/patients?risk=critical,high')}
                className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
              >
                View all
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border">
                    {['Patient', 'Condition', 'Risk Score', 'Care Gaps', 'Last Contact', 'Status'].map((h) => (
                      <th key={h} className="pb-2 text-left font-medium text-muted-foreground whitespace-nowrap pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(riskPatients ?? []).length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-muted-foreground">
                        Loading patient data...
                      </td>
                    </tr>
                  ) : (
                    (riskPatients ?? []).map((patient) => (
                      <PatientRiskRow key={patient.id} patient={patient} />
                    ))
                  )}
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
                className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
              >
                View all
              </button>
            </div>
            <AlertFeed alerts={alerts.slice(0, 6)} />
          </motion.div>

          {/* Agent activity timeline */}
          <motion.div variants={ITEM} className="clinical-card">
            <h2 className="text-sm font-bold text-foreground mb-4">Agent Activity (24h)</h2>
            <AgentActivityTimeline executions={executions.slice(0, 100)} height={220} />
          </motion.div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
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
                <Sparkles className="w-4 h-4 text-primary-500" />
                <h2 className="text-sm font-bold text-foreground">AI Recommendations</h2>
              </div>
              <span className="text-[10px] font-medium text-purple-600 bg-purple-50 dark:bg-purple-900/20 px-1.5 py-0.5 rounded">
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
              <Calendar className="w-4 h-4 text-muted-foreground" />
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

  const riskColor = riskCategory === 'critical' ? 'text-danger-600' : riskCategory === 'high' ? 'text-orange-600' : riskCategory === 'medium' ? 'text-warning-600' : 'text-secondary-600'

  return (
    <tr
      className="hover:bg-accent/50 cursor-pointer transition-colors"
      onClick={() => navigate(`/patients/${patient.id}`)}
    >
      <td className="py-2 pr-4">
        <div>
          <p className="font-semibold text-foreground">{patient.firstName} {patient.lastName}</p>
          <p className="text-muted-foreground font-mono">{patient.mrn}</p>
        </div>
      </td>
      <td className="py-2 pr-4">
        <p className="text-foreground truncate max-w-[120px]">
          {patient.activeConditions[0]?.display ?? '—'}
        </p>
      </td>
      <td className="py-2 pr-4">
        <span className={cn('font-mono font-bold', riskColor)}>
          {Math.round(riskScore)}%
        </span>
      </td>
      <td className="py-2 pr-4">
        {patient.openCareGaps > 0 ? (
          <span className="font-semibold text-warning-600">{patient.openCareGaps}</span>
        ) : (
          <span className="text-secondary-600">0</span>
        )}
      </td>
      <td className="py-2 pr-4">
        <span className="text-muted-foreground">
          {patient.lastContactDate
            ? format(new Date(patient.lastContactDate), 'MMM d')
            : '—'}
        </span>
      </td>
      <td className="py-2">
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
    return <p className="text-sm text-muted-foreground text-center py-4">No recent alerts</p>
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={cn(
            'flex items-start gap-3 p-2.5 rounded-lg border text-xs',
            alert.severity === 'critical'
              ? 'border-danger-200 dark:border-danger-800 bg-danger-50/60 dark:bg-danger-900/10'
              : alert.severity === 'urgent'
              ? 'border-warning-200 dark:border-warning-800 bg-warning-50/60 dark:bg-warning-900/10'
              : 'border-border bg-card',
          )}
        >
          <AlertTriangle className={cn('w-3.5 h-3.5 flex-shrink-0 mt-0.5', alert.severity === 'critical' ? 'text-danger-500' : alert.severity === 'urgent' ? 'text-warning-500' : 'text-muted-foreground')} />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-foreground">{alert.title}</p>
            <p className="text-muted-foreground truncate">{alert.patientName} · {alert.description}</p>
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
  const today = new Date()
  const mockAppts = [
    { time: '09:00 AM', patient: 'Maria Garcia', type: 'Follow-up', virtual: false },
    { time: '10:30 AM', patient: 'James Wilson', type: 'Diabetes Mgmt', virtual: true },
    { time: '02:00 PM', patient: 'Sarah Chen', type: 'New Patient', virtual: false },
    { time: '03:30 PM', patient: 'Robert Kim', type: 'HbA1c Review', virtual: true },
  ]

  return (
    <div className="space-y-2">
      {mockAppts.map((appt, i) => (
        <div key={i} className="flex items-center gap-3 py-1.5">
          <div className="text-right w-16 flex-shrink-0">
            <p className="text-xs font-mono text-foreground">{appt.time}</p>
          </div>
          <div className="w-px h-8 bg-border flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-foreground">{appt.patient}</p>
            <p className="text-[10px] text-muted-foreground">{appt.type}</p>
          </div>
          {appt.virtual && (
            <span className="text-[10px] font-medium text-primary-600 bg-primary-50 dark:bg-primary-900/20 px-1.5 py-0.5 rounded">
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
