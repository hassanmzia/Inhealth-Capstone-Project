import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type { ClinicalAlert, AlertSeverity } from '@/types/clinical'

// ─── Alert Store State ────────────────────────────────────────────────────────

interface AlertStoreState {
  alerts: ClinicalAlert[]
  unreadCount: number
  criticalCount: number
  urgentCount: number

  // Filters
  activeTab: AlertSeverity | 'all'
  showAcknowledged: boolean

  // Actions
  addAlert: (alert: ClinicalAlert) => void
  setAlerts: (alerts: ClinicalAlert[]) => void
  markRead: (alertId: string) => void
  markAllRead: () => void
  acknowledge: (alertId: string, acknowledgedBy: string) => void
  acknowledgeAll: (acknowledgedBy: string) => void
  removeAlert: (alertId: string) => void
  clearAll: () => void
  setActiveTab: (tab: AlertSeverity | 'all') => void
  setShowAcknowledged: (show: boolean) => void

  // Selectors
  getAlertsByTab: (tab: AlertSeverity | 'all') => ClinicalAlert[]
}

// ─── Priority Sort ────────────────────────────────────────────────────────────

const SEVERITY_PRIORITY: Record<AlertSeverity, number> = {
  critical: 0,
  urgent: 1,
  soon: 2,
  routine: 3,
}

function sortAlertsByPriority(alerts: ClinicalAlert[]): ClinicalAlert[] {
  return [...alerts].sort((a, b) => {
    // Unacknowledged first
    if (a.isAcknowledged !== b.isAcknowledged) {
      return a.isAcknowledged ? 1 : -1
    }
    // Then by severity
    const severityDiff = SEVERITY_PRIORITY[a.severity] - SEVERITY_PRIORITY[b.severity]
    if (severityDiff !== 0) return severityDiff
    // Then by timestamp (newest first)
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  })
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useAlertStore = create<AlertStoreState>()(
  subscribeWithSelector((set, get) => ({
    alerts: [],
    unreadCount: 0,
    criticalCount: 0,
    urgentCount: 0,
    activeTab: 'all',
    showAcknowledged: false,

    addAlert: (alert) => {
      set((state) => {
        // Deduplicate
        const exists = state.alerts.some((a) => a.id === alert.id)
        if (exists) return state

        const newAlerts = sortAlertsByPriority([alert, ...state.alerts])

        // Cap at 500 alerts
        const capped = newAlerts.slice(0, 500)

        return {
          alerts: capped,
          unreadCount: capped.filter((a) => !a.isRead).length,
          criticalCount: capped.filter((a) => a.severity === 'critical' && !a.isAcknowledged).length,
          urgentCount: capped.filter((a) => a.severity === 'urgent' && !a.isAcknowledged).length,
        }
      })
    },

    setAlerts: (alerts) => {
      const sorted = sortAlertsByPriority(alerts)
      set({
        alerts: sorted,
        unreadCount: sorted.filter((a) => !a.isRead).length,
        criticalCount: sorted.filter((a) => a.severity === 'critical' && !a.isAcknowledged).length,
        urgentCount: sorted.filter((a) => a.severity === 'urgent' && !a.isAcknowledged).length,
      })
    },

    markRead: (alertId) => {
      set((state) => {
        const alerts = state.alerts.map((a) =>
          a.id === alertId ? { ...a, isRead: true } : a,
        )
        return {
          alerts,
          unreadCount: alerts.filter((a) => !a.isRead).length,
        }
      })
    },

    markAllRead: () => {
      set((state) => ({
        alerts: state.alerts.map((a) => ({ ...a, isRead: true })),
        unreadCount: 0,
      }))
    },

    acknowledge: (alertId, acknowledgedBy) => {
      const now = new Date().toISOString()
      set((state) => {
        const alerts = state.alerts.map((a) =>
          a.id === alertId
            ? { ...a, isAcknowledged: true, isRead: true, acknowledgedBy, acknowledgedAt: now }
            : a,
        )
        return {
          alerts,
          unreadCount: alerts.filter((a) => !a.isRead).length,
          criticalCount: alerts.filter((a) => a.severity === 'critical' && !a.isAcknowledged).length,
          urgentCount: alerts.filter((a) => a.severity === 'urgent' && !a.isAcknowledged).length,
        }
      })
    },

    acknowledgeAll: (acknowledgedBy) => {
      const now = new Date().toISOString()
      set((state) => ({
        alerts: state.alerts.map((a) => ({
          ...a,
          isAcknowledged: true,
          isRead: true,
          acknowledgedBy,
          acknowledgedAt: now,
        })),
        unreadCount: 0,
        criticalCount: 0,
        urgentCount: 0,
      }))
    },

    removeAlert: (alertId) => {
      set((state) => {
        const alerts = state.alerts.filter((a) => a.id !== alertId)
        return {
          alerts,
          unreadCount: alerts.filter((a) => !a.isRead).length,
          criticalCount: alerts.filter((a) => a.severity === 'critical' && !a.isAcknowledged).length,
        }
      })
    },

    clearAll: () => {
      set({ alerts: [], unreadCount: 0, criticalCount: 0, urgentCount: 0 })
    },

    setActiveTab: (tab) => set({ activeTab: tab }),
    setShowAcknowledged: (show) => set({ showAcknowledged: show }),

    getAlertsByTab: (tab) => {
      const { alerts, showAcknowledged } = get()
      let filtered = showAcknowledged ? alerts : alerts.filter((a) => !a.isAcknowledged)
      if (tab !== 'all') {
        filtered = filtered.filter((a) => a.severity === tab)
      }
      return filtered
    },
  })),
)

// ─── Selectors ────────────────────────────────────────────────────────────────

export const selectCriticalAlerts = (state: AlertStoreState) =>
  state.alerts.filter((a) => a.severity === 'critical' && !a.isAcknowledged)

export const selectAlertsByPatient = (patientId: string) => (state: AlertStoreState) =>
  state.alerts.filter((a) => a.patientId === patientId)

export const selectHasUnreadAlerts = (state: AlertStoreState) => state.unreadCount > 0
