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
import { format } from 'date-fns'
import { useAuthStore } from '@/store/authStore'
import { useAlertStore } from '@/store/alertStore'
import { useAgentStore, selectTotalActiveAgents } from '@/store/agentStore'
import { getRecommendations } from '@/services/agents'
import api from '@/services/api'
import AIRecommendationPanel from '@/components/clinical/AIRecommendationPanel'
import PopulationRiskPyramid from '@/components/charts/PopulationRiskPyramid'
import AgentActivityTimeline from '@/components/charts/AgentActivityTimeline'
import { cn } from '@/lib/utils'
import type { PatientSummary, ClinicalAlert } from '@/types/clinical'

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
  const displayExecutions = useMemo(() => executions.slice(0, 100), [executions])

  const { data: statsRaw } = useQuery<DashboardStats>({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.get('/dashboard/stats/').then((r) => r.data),
    refetchInterval: 30000,
  })
  const stats = statsRaw ?? null

  const { data: patientList } = useQuery({
    queryKey: ['patients-list'],
    queryFn: () => api.get('/patients/').then((r) => r.data),
  })
  const patientCount = useMemo(() => {
    if (stats?.totalPatients) return stats.totalPatients
    if (Array.isArray(patientList)) return patientList.length
    if (patientList?.results) return patientList.results.length
    if (patientList?.count != null) return patientList.count
    return 0
  }, [stats, patientList])

  const { data: riskPatientsRaw = [] } = useQuery<PatientSummary[]>({
    queryKey: ['high-risk-patients'],
    queryFn: () => api.get('/patients/?risk_level=critical,high&limit=10').then((r) => r.data?.results ?? []),
  })
  const riskPatients = riskPatientsRaw

  const { data: recommendations, refetch: refetchRecs } = useQuery({
    queryKey: ['recent-recommendations'],
    queryFn: () => getRecommendations(undefined, 'pending', 5),
    placeholderData: [],
  })

  const criticalAlerts = alerts.filter((a) => a.severity === 'critical' && !a.isAcknowledged)

  const STAT_CARDS = [
    {
      label: 'Total Patients',
      value: patientCount > 0 ? patientCount.toLocaleString() : '—',
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
                  {riskPatients.length > 0 ? (
                    riskPatients.map((patient) => (
                      <PatientRiskRow key={patient.id} patient={patient} />
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-sm text-muted-foreground">
                        No high-risk patients found
                      </td>
                    </tr>
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
            {displayExecutions.length > 0 ? (
              <AgentActivityTimeline executions={displayExecutions} height={220} />
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">No agent activity recorded yet</p>
            )}
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

