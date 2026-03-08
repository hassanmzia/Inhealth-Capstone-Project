import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Info,
  CheckCheck,
  Filter,
} from 'lucide-react'
import { formatDistanceToNow, format } from 'date-fns'
import { useAlertStore } from '@/store/alertStore'
import { useAuthStore } from '@/store/authStore'
import type { ClinicalAlert, AlertSeverity } from '@/types/clinical'
import { cn } from '@/lib/utils'

const SEVERITY_CONFIG: Record<AlertSeverity, {
  label: string
  icon: React.ElementType
  cardBg: string
  iconColor: string
  badge: string
}> = {
  critical: {
    label: 'Critical',
    icon: AlertTriangle,
    cardBg: 'border-l-4 border-l-danger-500 bg-danger-50/30 dark:bg-danger-900/10',
    iconColor: 'text-danger-500',
    badge: 'bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-400',
  },
  urgent: {
    label: 'Urgent',
    icon: AlertTriangle,
    cardBg: 'border-l-4 border-l-warning-500 bg-warning-50/30 dark:bg-warning-900/10',
    iconColor: 'text-warning-500',
    badge: 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400',
  },
  soon: {
    label: 'Soon',
    icon: Clock,
    cardBg: 'border-l-4 border-l-primary-400',
    iconColor: 'text-primary-400',
    badge: 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400',
  },
  routine: {
    label: 'Routine',
    icon: Info,
    cardBg: 'border-l-4 border-l-clinical-300',
    iconColor: 'text-muted-foreground',
    badge: 'bg-muted text-muted-foreground',
  },
}

export default function AlertsPage() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const {
    alerts,
    unreadCount,
    activeTab,
    showAcknowledged,
    setActiveTab,
    setShowAcknowledged,
    markAllRead,
    acknowledgeAll,
    acknowledge,
    markRead,
    getAlertsByTab,
  } = useAlertStore()

  const displayedAlerts = getAlertsByTab(activeTab)

  const counts = {
    all: alerts.filter((a) => showAcknowledged || !a.isAcknowledged).length,
    critical: alerts.filter((a) => a.severity === 'critical' && (showAcknowledged || !a.isAcknowledged)).length,
    urgent: alerts.filter((a) => a.severity === 'urgent' && (showAcknowledged || !a.isAcknowledged)).length,
    soon: alerts.filter((a) => a.severity === 'soon' && (showAcknowledged || !a.isAcknowledged)).length,
    routine: alerts.filter((a) => a.severity === 'routine' && (showAcknowledged || !a.isAcknowledged)).length,
  }

  return (
    <div className="space-y-4 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary-500" />
            Notification Center
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {unreadCount > 0 ? `${unreadCount} unread alerts` : 'All caught up'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={markAllRead}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium border border-border rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            >
              <CheckCheck className="w-3.5 h-3.5" />
              Mark all read
            </button>
          )}
          <button
            onClick={() => acknowledgeAll(user?.id ?? 'physician')}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Acknowledge All
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto">
        {[
          { id: 'all', label: 'All', count: counts.all },
          { id: 'critical', label: 'Critical', count: counts.critical },
          { id: 'urgent', label: 'Urgent', count: counts.urgent },
          { id: 'soon', label: 'Soon', count: counts.soon },
          { id: 'routine', label: 'Routine', count: counts.routine },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as AlertSeverity | 'all')}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
              activeTab === tab.id
                ? 'bg-primary-600 text-white'
                : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground',
            )}
          >
            {tab.label}
            {tab.count > 0 && (
              <span className={cn(
                'rounded-full text-[10px] font-bold px-1.5 py-0.5 leading-none',
                activeTab === tab.id ? 'bg-white/20 text-white' : 'bg-background text-foreground',
              )}>
                {tab.count}
              </span>
            )}
          </button>
        ))}

        {/* Filter toggle */}
        <button
          onClick={() => setShowAcknowledged(!showAcknowledged)}
          className={cn(
            'ml-auto flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors border',
            showAcknowledged
              ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-200 text-primary-700 dark:text-primary-400'
              : 'border-border text-muted-foreground hover:bg-accent',
          )}
        >
          <Filter className="w-3.5 h-3.5" />
          {showAcknowledged ? 'Hide' : 'Show'} Acknowledged
        </button>
      </div>

      {/* Alert list */}
      <div className="space-y-2">
        <AnimatePresence mode="sync">
          {displayedAlerts.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center py-16"
            >
              <CheckCircle2 className="w-12 h-12 text-secondary-400 mx-auto mb-3" />
              <p className="text-sm font-medium text-foreground">No {activeTab !== 'all' ? activeTab : ''} alerts</p>
              <p className="text-xs text-muted-foreground mt-1">
                {showAcknowledged ? 'No alerts in this category' : 'All clear! No unacknowledged alerts.'}
              </p>
            </motion.div>
          ) : (
            displayedAlerts.map((alert) => (
              <AlertCard
                key={alert.id}
                alert={alert}
                onAcknowledge={() => acknowledge(alert.id, user?.id ?? 'physician')}
                onRead={() => markRead(alert.id)}
                onPatientClick={() => alert.patientId && navigate(`/patients/${alert.patientId}`)}
              />
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

// ─── Alert Card ───────────────────────────────────────────────────────────────

function AlertCard({
  alert,
  onAcknowledge,
  onRead,
  onPatientClick,
}: {
  alert: ClinicalAlert
  onAcknowledge: () => void
  onRead: () => void
  onPatientClick: () => void
}) {
  const config = SEVERITY_CONFIG[alert.severity]
  const Icon = config.icon

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 10 }}
      className={cn(
        'border border-border rounded-xl overflow-hidden bg-card transition-all',
        config.cardBg,
        !alert.isRead && 'ring-1 ring-primary-200 dark:ring-primary-900',
        alert.isAcknowledged && 'opacity-60',
      )}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className="flex-shrink-0 mt-0.5">
            <Icon className={cn('w-5 h-5', config.iconColor, alert.severity === 'critical' && 'animate-alert-pulse')} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded', config.badge)}>
                    {config.label}
                  </span>
                  {!alert.isRead && (
                    <span className="w-2 h-2 rounded-full bg-primary-500" />
                  )}
                  {alert.isAcknowledged && (
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3" />
                      Acknowledged by {alert.acknowledgedBy}
                    </span>
                  )}
                </div>
                <h3 className="text-sm font-semibold text-foreground mt-1">{alert.title}</h3>
              </div>
              <span className="text-xs text-muted-foreground flex-shrink-0">
                {formatDistanceToNow(new Date(alert.timestamp), { addSuffix: true })}
              </span>
            </div>

            <p className="text-sm text-foreground/80 mt-1 leading-relaxed">{alert.description}</p>

            {/* Patient + metadata */}
            <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
              {alert.patientName && (
                <button
                  onClick={onPatientClick}
                  className="font-semibold text-primary-600 dark:text-primary-400 hover:underline"
                >
                  {alert.patientName}
                </button>
              )}
              {alert.value && (
                <span className="font-mono font-bold text-foreground">{alert.value}</span>
              )}
              {alert.normalRange && (
                <span>Normal: {alert.normalRange}</span>
              )}
              <span>{format(new Date(alert.timestamp), 'MMM d, yyyy HH:mm')}</span>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 mt-3">
              {!alert.isAcknowledged && (
                <button
                  onClick={onAcknowledge}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-secondary-600 hover:bg-secondary-700 text-white rounded-lg transition-colors"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Acknowledge
                </button>
              )}
              {!alert.isRead && (
                <button
                  onClick={onRead}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  Mark Read
                </button>
              )}
              {alert.patientId && (
                <button
                  onClick={onPatientClick}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border border-border rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                >
                  View Patient
                </button>
              )}
              {alert.actionUrl && (
                <a
                  href={alert.actionUrl}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-primary-600 dark:text-primary-400 hover:underline"
                >
                  Take Action →
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
