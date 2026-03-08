import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { subMinutes, subHours } from 'date-fns'
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

// ─── Demo Alerts (shown when no real alerts arrive) ──────────────────────────

const _now = new Date()

const DEMO_ALERTS: ClinicalAlert[] = sortAlertsByPriority([
  {
    id: 'demo-a1', patientId: 'demo-p1', patientName: 'James Morrison', severity: 'critical', category: 'vital_sign',
    title: 'Blood Glucose Critical High', description: 'Blood glucose reading of 342 mg/dL detected via CGM device', value: '342 mg/dL', normalRange: '70-140 mg/dL',
    timestamp: subMinutes(_now, 23).toISOString(), isRead: false, isAcknowledged: false, escalationCount: 1,
  },
  {
    id: 'demo-a2', patientId: 'demo-p5', patientName: 'William Jackson', severity: 'critical', category: 'lab_result',
    title: 'eGFR Declining Rapidly', description: 'eGFR dropped to 22 mL/min — CKD Stage 4 progression detected by renal function monitor', value: '22 mL/min',
    timestamp: subHours(_now, 1).toISOString(), isRead: false, isAcknowledged: false, escalationCount: 0,
  },
  {
    id: 'demo-a3', patientId: 'demo-p2', patientName: 'Maria Gonzalez', severity: 'urgent', category: 'vital_sign',
    title: 'Blood Pressure Elevated', description: 'BP reading 168/98 mmHg — above target for HF patient. Consider medication adjustment.', value: '168/98 mmHg', normalRange: '<130/80 mmHg',
    timestamp: subHours(_now, 3).toISOString(), isRead: false, isAcknowledged: false, escalationCount: 0,
  },
  {
    id: 'demo-a4', patientId: 'demo-p3', patientName: 'Robert Chen', severity: 'urgent', category: 'medication',
    title: 'Medication Non-Adherence Detected', description: 'Missed 3 consecutive doses of Metformin 500mg — PDC dropped to 62%. Patient outreach recommended.',
    timestamp: subHours(_now, 5).toISOString(), isRead: true, isAcknowledged: false, escalationCount: 0,
  },
  {
    id: 'demo-a5', patientId: 'demo-p4', patientName: 'Dorothy Williams', severity: 'soon', category: 'vital_sign',
    title: 'SpO2 Below Threshold', description: 'Oxygen saturation at 91% — monitor for COPD exacerbation. Consider pulmonology consult.', value: '91%', normalRange: '95-100%',
    timestamp: subHours(_now, 8).toISOString(), isRead: true, isAcknowledged: false, escalationCount: 0,
  },
  {
    id: 'demo-a6', patientId: 'demo-p6', patientName: 'Linda Nguyen', severity: 'routine', category: 'lab_result',
    title: 'HbA1c Result Available', description: 'New HbA1c result: 7.8% — improved from 8.4%. Continue current therapy.', value: '7.8%',
    timestamp: subHours(_now, 12).toISOString(), isRead: true, isAcknowledged: false, escalationCount: 0,
  },
  {
    id: 'demo-a7', patientId: 'demo-p1', patientName: 'James Morrison', severity: 'urgent', category: 'lab_result',
    title: 'Potassium Level Elevated', description: 'Serum potassium 5.8 mEq/L — above normal range. Review current medications (ACE inhibitors).', value: '5.8 mEq/L', normalRange: '3.5-5.0 mEq/L',
    timestamp: subHours(_now, 6).toISOString(), isRead: false, isAcknowledged: false, escalationCount: 0,
  },
  {
    id: 'demo-a8', patientId: 'demo-p5', patientName: 'William Jackson', severity: 'soon', category: 'medication',
    title: 'Prescription Refill Due', description: 'Sodium Bicarbonate 650mg — 5 days of supply remaining. Auto-refill not enabled.',
    timestamp: subHours(_now, 14).toISOString(), isRead: true, isAcknowledged: false, escalationCount: 0,
  },
])

// ─── Store ────────────────────────────────────────────────────────────────────

export const useAlertStore = create<AlertStoreState>()(
  subscribeWithSelector((set, get) => ({
    alerts: DEMO_ALERTS,
    unreadCount: DEMO_ALERTS.filter((a) => !a.isRead).length,
    criticalCount: DEMO_ALERTS.filter((a) => a.severity === 'critical' && !a.isAcknowledged).length,
    urgentCount: DEMO_ALERTS.filter((a) => a.severity === 'urgent' && !a.isAcknowledged).length,
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
