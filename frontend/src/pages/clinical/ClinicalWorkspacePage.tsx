/**
 * Clinical Workspace — redirects to Patient List with clinical context.
 * Serves as the main workflow hub for physicians and nurses, combining
 * patient search with quick-access clinical tools.
 */
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  Stethoscope,
  Users,
  ClipboardCheck,
  AlertTriangle,
  Calendar,
  BrainCircuit,
  ArrowRight,
  Loader2,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useAlertStore } from '@/store/alertStore'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

export default function ClinicalWorkspacePage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { alerts } = useAlertStore()

  const criticalAlerts = alerts.filter((a) => a.severity === 'critical' && !a.isAcknowledged)

  const { data: stats, isLoading } = useQuery({
    queryKey: ['clinical-workspace-stats'],
    queryFn: () => api.get('/dashboard/stats/').then((r) => r.data),
    refetchInterval: 60000,
    placeholderData: {
      totalPatients: 0,
      openCareGaps: 0,
      todaysAppointments: 0,
      criticalAlerts: 0,
      riskDistribution: { critical: 0, high: 0, medium: 0, low: 0, total: 0 },
    },
  })

  const QUICK_ACTIONS = [
    {
      label: 'Patient Roster',
      desc: 'Search and manage all patients',
      icon: Users,
      color: 'text-primary-600 dark:text-primary-400',
      bg: 'bg-primary-50 dark:bg-primary-900/20',
      href: '/patients',
    },
    {
      label: 'Care Gaps',
      desc: 'Review open clinical quality measures',
      icon: ClipboardCheck,
      color: 'text-warning-600 dark:text-warning-400',
      bg: 'bg-warning-50 dark:bg-warning-900/20',
      href: '/patients?filter=care_gaps',
    },
    {
      label: 'Critical Alerts',
      desc: 'Patients needing immediate attention',
      icon: AlertTriangle,
      color: 'text-danger-600 dark:text-danger-400',
      bg: 'bg-danger-50 dark:bg-danger-900/20',
      href: '/alerts',
      badge: criticalAlerts.length,
    },
    {
      label: 'Appointments',
      desc: 'Today\'s schedule and upcoming visits',
      icon: Calendar,
      color: 'text-secondary-600 dark:text-secondary-400',
      bg: 'bg-secondary-50 dark:bg-secondary-900/20',
      href: '/telemedicine',
    },
    {
      label: 'AI Agents',
      desc: 'Monitor running agents and recommendations',
      icon: BrainCircuit,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50 dark:bg-purple-900/20',
      href: '/agents',
    },
    {
      label: 'High Risk Patients',
      desc: 'Critical & high risk patients',
      icon: Stethoscope,
      color: 'text-orange-600 dark:text-orange-400',
      bg: 'bg-orange-50 dark:bg-orange-900/20',
      href: '/patients?risk_level=critical,high',
    },
  ]

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-5xl">
      {/* Header */}
      <motion.div variants={ITEM}>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <Stethoscope className="w-6 h-6 text-primary-500" />
          Clinical Workspace
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Your clinical workflow hub — {user?.specialty || 'Clinician'}
        </p>
      </motion.div>

      {/* Stats strip */}
      <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Patients', value: stats?.totalPatients ?? 0, color: 'text-primary-600' },
          { label: 'Critical Alerts', value: criticalAlerts.length, color: 'text-danger-600' },
          { label: 'Open Care Gaps', value: stats?.openCareGaps ?? 0, color: 'text-warning-600' },
          { label: "Today's Appointments", value: stats?.todaysAppointments ?? 0, color: 'text-secondary-600' },
        ].map((stat) => (
          <div key={stat.label} className="clinical-card">
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            ) : (
              <p className={cn('text-2xl font-bold font-mono tabular-nums', stat.color)}>
                {stat.value.toLocaleString()}
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
          </div>
        ))}
      </motion.div>

      {/* Quick actions grid */}
      <motion.div variants={ITEM} className="clinical-card">
        <h2 className="text-sm font-bold text-foreground mb-4">Quick Access</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => navigate(action.href)}
              className="flex items-start gap-3 p-3 rounded-lg border border-border bg-card hover:bg-accent hover:border-primary-300 dark:hover:border-primary-700 transition-all text-left group"
            >
              <div className={cn('p-2 rounded-lg flex-shrink-0', action.bg)}>
                <action.icon className={cn('w-5 h-5', action.color)} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-foreground">{action.label}</p>
                  {action.badge !== undefined && action.badge > 0 && (
                    <span className="text-[10px] font-bold text-white bg-danger-500 rounded-full px-1.5 py-0.5">
                      {action.badge}
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{action.desc}</p>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors flex-shrink-0 mt-0.5" />
            </button>
          ))}
        </div>
      </motion.div>

      {/* Risk distribution */}
      {stats?.riskDistribution && (stats.riskDistribution.total ?? 0) > 0 && (
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4">Risk Distribution</h2>
          <div className="space-y-2">
            {[
              { label: 'Critical', key: 'critical', color: 'bg-danger-500' },
              { label: 'High', key: 'high', color: 'bg-orange-500' },
              { label: 'Medium', key: 'medium', color: 'bg-warning-500' },
              { label: 'Low', key: 'low', color: 'bg-secondary-500' },
            ].map(({ label, key, color }) => {
              const count = (stats.riskDistribution as Record<string, number>)[key] ?? 0
              const total = stats.riskDistribution.total || 1
              const pct = Math.round((count / total) * 100)
              return (
                <div key={key} className="flex items-center gap-3">
                  <span className="text-xs font-medium text-muted-foreground w-14">{label}</span>
                  <div className="flex-1 bg-accent rounded-full h-2">
                    <div
                      className={cn('h-2 rounded-full transition-all', color)}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs font-mono text-foreground w-10 text-right">
                    {count.toLocaleString()}
                  </span>
                </div>
              )
            })}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
