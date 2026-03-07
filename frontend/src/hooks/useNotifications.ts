import { useEffect, useRef, useCallback, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAlertStore } from '@/store/alertStore'
import { useAuthStore } from '@/store/authStore'
import { wsManager } from '@/services/websocket'
import api from '@/services/api'
import type { ClinicalAlert } from '@/types/clinical'

// ─── Types ────────────────────────────────────────────────────────────────────

export type NotificationPermission = 'default' | 'granted' | 'denied'

interface UseNotificationsOptions {
  enableWebSocket?: boolean
  enableBrowserNotifications?: boolean
  enableSound?: boolean
  pollInterval?: number
}

interface UseNotificationsReturn {
  alerts: ClinicalAlert[]
  unreadCount: number
  criticalCount: number
  urgentCount: number
  permissionState: NotificationPermission
  isConnected: boolean
  requestPermission: () => Promise<NotificationPermission>
  markRead: (alertId: string) => void
  markAllRead: () => void
  acknowledge: (alertId: string) => void
  acknowledgeAll: () => void
  getAlertsByTab: (tab: string) => ClinicalAlert[]
  dismissBrowserNotification: (alertId: string) => void
}

// ─── Audio singleton ───────────────────────────────────────────────────────────

let audioCtx: AudioContext | null = null

function playAlertTone(severity: 'critical' | 'urgent' | 'routine') {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
    }

    const oscillator = audioCtx.createOscillator()
    const gainNode = audioCtx.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(audioCtx.destination)

    // Different tones per severity
    if (severity === 'critical') {
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime)
      oscillator.frequency.setValueAtTime(660, audioCtx.currentTime + 0.15)
      oscillator.frequency.setValueAtTime(880, audioCtx.currentTime + 0.3)
      gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.6)
      oscillator.start(audioCtx.currentTime)
      oscillator.stop(audioCtx.currentTime + 0.6)
    } else if (severity === 'urgent') {
      oscillator.frequency.setValueAtTime(660, audioCtx.currentTime)
      oscillator.frequency.setValueAtTime(440, audioCtx.currentTime + 0.2)
      gainNode.gain.setValueAtTime(0.2, audioCtx.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.4)
      oscillator.start(audioCtx.currentTime)
      oscillator.stop(audioCtx.currentTime + 0.4)
    } else {
      oscillator.frequency.setValueAtTime(440, audioCtx.currentTime)
      gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3)
      oscillator.start(audioCtx.currentTime)
      oscillator.stop(audioCtx.currentTime + 0.3)
    }
  } catch {
    // AudioContext not available or blocked by browser policy
  }
}

// ─── Main hook ─────────────────────────────────────────────────────────────────

export function useNotifications({
  enableWebSocket = true,
  enableBrowserNotifications = true,
  enableSound = true,
  pollInterval = 30000,
}: UseNotificationsOptions = {}): UseNotificationsReturn {
  const queryClient = useQueryClient()
  const { alerts, unreadCount, criticalCount, urgentCount, addAlert, markRead, markAllRead, acknowledge, acknowledgeAll, getAlertsByTab } =
    useAlertStore()
  const { isAuthenticated, user } = useAuthStore()

  const [permissionState, setPermissionState] = useState<NotificationPermission>(
    () => (typeof Notification !== 'undefined' ? Notification.permission : 'default'),
  )
  const [isConnected, setIsConnected] = useState(false)

  // Track active browser notifications so we can close them programmatically
  const browserNotificationsRef = useRef<Map<string, Notification>>(new Map())
  const wsCleanupRef = useRef<(() => void) | null>(null)
  const seenAlertIds = useRef<Set<string>>(new Set())

  // ─── Request browser notification permission ────────────────────────────────

  const requestPermission = useCallback(async (): Promise<NotificationPermission> => {
    if (typeof Notification === 'undefined') return 'denied'

    const result = await Notification.requestPermission()
    setPermissionState(result)
    return result
  }, [])

  // ─── Show browser notification ──────────────────────────────────────────────

  const showBrowserNotification = useCallback(
    (alert: ClinicalAlert) => {
      if (
        !enableBrowserNotifications ||
        permissionState !== 'granted' ||
        typeof Notification === 'undefined'
      ) {
        return
      }

      // Avoid duplicate browser notifications
      if (seenAlertIds.current.has(alert.id)) return
      seenAlertIds.current.add(alert.id)

      const iconMap: Record<string, string> = {
        critical: '/icons/alert-critical.png',
        urgent: '/icons/alert-urgent.png',
        soon: '/icons/alert-soon.png',
        routine: '/icons/alert-routine.png',
      }

      const notification = new Notification(
        alert.title,
        {
          body: alert.message,
          icon: iconMap[alert.severity] ?? '/icons/alert-routine.png',
          badge: '/icons/badge.png',
          tag: alert.id,
          requireInteraction: alert.severity === 'critical',
          silent: true, // We handle sound ourselves
        },
      )

      notification.onclick = () => {
        window.focus()
        notification.close()
        browserNotificationsRef.current.delete(alert.id)
        // Navigate to alerts page
        window.location.hash = `/alerts`
      }

      notification.onclose = () => {
        browserNotificationsRef.current.delete(alert.id)
      }

      browserNotificationsRef.current.set(alert.id, notification)

      // Auto-close non-critical notifications after 8 seconds
      if (alert.severity !== 'critical') {
        setTimeout(() => {
          notification.close()
          browserNotificationsRef.current.delete(alert.id)
        }, 8000)
      }
    },
    [enableBrowserNotifications, permissionState],
  )

  // ─── Handle incoming alert ─────────────────────────────────────────────────

  const handleIncomingAlert = useCallback(
    (alert: ClinicalAlert) => {
      addAlert(alert)

      // Show in-app toast
      const toastOptions = { duration: alert.severity === 'critical' ? 8000 : 5000 }
      if (alert.severity === 'critical') {
        toast.error(`CRITICAL: ${alert.title}`, toastOptions)
      } else if (alert.severity === 'urgent') {
        toast(`${alert.title}`, { ...toastOptions, icon: '⚠️' })
      }

      // Play sound
      if (enableSound) {
        const soundSeverity =
          alert.severity === 'critical' || alert.severity === 'urgent'
            ? alert.severity
            : 'routine'
        playAlertTone(soundSeverity)
      }

      // Show browser notification
      showBrowserNotification(alert)

      // Invalidate related queries
      if (alert.patientId) {
        queryClient.invalidateQueries({ queryKey: ['fhir', 'patient', alert.patientId] })
      }
    },
    [addAlert, enableSound, showBrowserNotification, queryClient],
  )

  // ─── Poll notifications from API ──────────────────────────────────────────

  useQuery({
    queryKey: ['notifications', 'poll'],
    queryFn: async () => {
      const { data } = await api.get<{ results: ClinicalAlert[] }>('/notifications/', {
        params: { unread: true, limit: 50 },
      })
      // Add new alerts without duplicates (addAlert deduplicates internally)
      data.results.forEach((alert) => addAlert(alert))
      return data
    },
    enabled: isAuthenticated,
    refetchInterval: pollInterval,
    staleTime: pollInterval / 2,
  })

  // ─── WebSocket connection ─────────────────────────────────────────────────

  useEffect(() => {
    if (!enableWebSocket || !isAuthenticated) return

    // Connect and subscribe to notifications namespace.
    // wsManager.connectNotificationsSocket() routes events to alertStore and
    // handles reconnection internally — no need for additional socket listeners.
    const cleanup = wsManager.connectNotificationsSocket()
    wsCleanupRef.current = cleanup
    setIsConnected(wsManager.isConnected('/ws/alerts/'))

    // Poll connection status periodically (WS reconnects are async)
    const connCheck = setInterval(() => {
      setIsConnected(wsManager.isConnected('/ws/alerts/'))
    }, 5000)

    return () => {
      clearInterval(connCheck)
      if (wsCleanupRef.current) {
        wsCleanupRef.current()
        wsCleanupRef.current = null
      }
      setIsConnected(false)
    }
  }, [enableWebSocket, isAuthenticated])

  // ─── Auto-request permission on mount if enabled ──────────────────────────

  useEffect(() => {
    if (
      enableBrowserNotifications &&
      typeof Notification !== 'undefined' &&
      Notification.permission === 'default' &&
      isAuthenticated
    ) {
      // Request after a short delay so it doesn't fire on first load
      const timer = setTimeout(requestPermission, 3000)
      return () => clearTimeout(timer)
    }
  }, [enableBrowserNotifications, isAuthenticated, requestPermission])

  // ─── Sync permission state if changed externally ──────────────────────────

  useEffect(() => {
    if (typeof Notification === 'undefined') return
    const interval = setInterval(() => {
      if (Notification.permission !== permissionState) {
        setPermissionState(Notification.permission)
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [permissionState])

  // ─── Mark read (with server sync) ─────────────────────────────────────────

  const markReadMutation = useMutation({
    mutationFn: (alertId: string) => api.patch(`/notifications/${alertId}/read/`),
    onSuccess: (_, alertId) => markRead(alertId),
  })

  const markAllReadMutation = useMutation({
    mutationFn: () => api.post('/notifications/mark-all-read/'),
    onSuccess: () => markAllRead(),
  })

  // ─── Acknowledge (with server sync) ───────────────────────────────────────

  const acknowledgeMutation = useMutation({
    mutationFn: (alertId: string) => api.patch(`/notifications/${alertId}/acknowledge/`),
    onSuccess: (_, alertId) => acknowledge(alertId),
  })

  const acknowledgeAllMutation = useMutation({
    mutationFn: () => api.post('/notifications/acknowledge-all/'),
    onSuccess: () => acknowledgeAll(),
  })

  // ─── Dismiss browser notification ─────────────────────────────────────────

  const dismissBrowserNotification = useCallback((alertId: string) => {
    const notification = browserNotificationsRef.current.get(alertId)
    if (notification) {
      notification.close()
      browserNotificationsRef.current.delete(alertId)
    }
  }, [])

  // ─── Cleanup browser notifications on unmount ──────────────────────────────

  useEffect(() => {
    return () => {
      browserNotificationsRef.current.forEach((n) => n.close())
      browserNotificationsRef.current.clear()
    }
  }, [])

  return {
    alerts,
    unreadCount,
    criticalCount,
    urgentCount,
    permissionState,
    isConnected,
    requestPermission,
    markRead: (id) => markReadMutation.mutate(id),
    markAllRead: () => markAllReadMutation.mutate(),
    acknowledge: (id) => acknowledgeMutation.mutate(id),
    acknowledgeAll: () => acknowledgeAllMutation.mutate(),
    getAlertsByTab,
    dismissBrowserNotification,
  }
}

// ─── Lightweight unread count hook ────────────────────────────────────────────

/** Subscribes only to unread/critical counts — avoids re-rendering full alert list. */
export function useNotificationCounts() {
  const { unreadCount, criticalCount, urgentCount } = useAlertStore()
  return { unreadCount, criticalCount, urgentCount }
}

// ─── Per-patient alert hook ────────────────────────────────────────────────────

/** Returns alerts for a specific patient, sorted by severity then timestamp. */
export function usePatientAlerts(patientId: string | undefined) {
  const { alerts } = useAlertStore()

  const patientAlerts = alerts.filter(
    (a) => a.patientId === patientId && !a.acknowledged,
  )

  const hasCritical = patientAlerts.some((a) => a.severity === 'critical')
  const hasUrgent = patientAlerts.some((a) => a.severity === 'urgent')

  return {
    alerts: patientAlerts,
    count: patientAlerts.length,
    hasCritical,
    hasUrgent,
  }
}

// ─── Notification preference hook ─────────────────────────────────────────────

interface NotificationPreferences {
  criticalAlerts: boolean
  urgentAlerts: boolean
  careGapReminders: boolean
  agentNotifications: boolean
  browserNotifications: boolean
  soundAlerts: boolean
}

export function useNotificationPreferences() {
  const { user, updatePreferences } = useAuthStore()

  const preferences: NotificationPreferences = {
    criticalAlerts: (user?.preferences?.criticalAlerts as boolean) ?? true,
    urgentAlerts: (user?.preferences?.urgentAlerts as boolean) ?? true,
    careGapReminders: (user?.preferences?.careGapReminders as boolean) ?? true,
    agentNotifications: (user?.preferences?.agentNotifications as boolean) ?? false,
    browserNotifications: (user?.preferences?.browserNotifications as boolean) ?? true,
    soundAlerts: (user?.preferences?.soundAlerts as boolean) ?? true,
  }

  const updateNotificationPref = useCallback(
    (key: keyof NotificationPreferences, value: boolean) => {
      updatePreferences({ [key]: value })
      // Sync to server
      api.patch('/auth/preferences/', { [key]: value }).catch(() => {
        // Silently fail; Zustand state is already updated optimistically
      })
    },
    [updatePreferences],
  )

  return { preferences, updateNotificationPref }
}
