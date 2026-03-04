import { io, Socket } from 'socket.io-client'
import { useAuthStore } from '@/store/authStore'
import { useAlertStore } from '@/store/alertStore'
import { useAgentStore } from '@/store/agentStore'
import type { ClinicalAlert } from '@/types/clinical'
import type { AgentExecution, AgentStatusInfo } from '@/types/agent'

const WS_URL = import.meta.env.VITE_WS_URL || ''

// ─── Event Types ──────────────────────────────────────────────────────────────

export interface VitalUpdate {
  patientId: string
  type: string
  value: number
  unit: string
  timestamp: string
  status: 'normal' | 'warning' | 'critical'
}

export interface AgentStatusUpdate {
  agentId: string
  status: AgentStatusInfo['status']
  executionId?: string
  message?: string
  timestamp: string
}

export interface AgentExecutionUpdate {
  executionId: string
  agentId: string
  status: AgentExecution['status']
  output?: Record<string, unknown>
  error?: string
  timestamp: string
}

export interface NotificationEvent {
  id: string
  type: string
  severity: ClinicalAlert['severity']
  title: string
  message: string
  patientId?: string
  patientName?: string
  timestamp: string
}

// ─── Socket Manager ───────────────────────────────────────────────────────────

class WebSocketManager {
  private sockets: Map<string, Socket> = new Map()
  private vitalCallbacks: Map<string, ((data: VitalUpdate) => void)[]> = new Map()
  private reconnectTimers: Map<string, ReturnType<typeof setTimeout>> = new Map()

  private createSocket(namespace: string): Socket {
    const token = useAuthStore.getState().token

    const socket = io(`${WS_URL}${namespace}`, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
    })

    socket.on('connect', () => {
      console.info(`[WS] Connected to ${namespace}`)
      // Clear any pending reconnect timer
      const timer = this.reconnectTimers.get(namespace)
      if (timer) clearTimeout(timer)
    })

    socket.on('disconnect', (reason: string) => {
      console.warn(`[WS] Disconnected from ${namespace}: ${reason}`)
    })

    socket.on('connect_error', (err: Error) => {
      console.error(`[WS] Connection error on ${namespace}:`, err.message)
    })

    return socket
  }

  // ── Vitals WebSocket ────────────────────────────────────────────────────────

  subscribeToVitals(
    patientId: string,
    onVitalUpdate: (data: VitalUpdate) => void,
  ): () => void {
    const namespace = `/ws/vitals`
    let socket = this.sockets.get(namespace)

    if (!socket) {
      socket = this.createSocket(namespace)
      this.sockets.set(namespace, socket)
    }

    // Join patient room
    socket.emit('join', { patient_id: patientId })

    // Register callback
    const callbacks = this.vitalCallbacks.get(patientId) ?? []
    callbacks.push(onVitalUpdate)
    this.vitalCallbacks.set(patientId, callbacks)

    // Listen for vitals
    const handler = (data: VitalUpdate) => {
      if (data.patientId === patientId) {
        onVitalUpdate(data)
      }
    }

    socket.on('vital_update', handler)
    socket.on(`vital_update:${patientId}`, onVitalUpdate)

    // Return unsubscribe
    return () => {
      socket!.off('vital_update', handler)
      socket!.off(`vital_update:${patientId}`, onVitalUpdate)
      socket!.emit('leave', { patient_id: patientId })

      const cbs = this.vitalCallbacks.get(patientId) ?? []
      const filtered = cbs.filter((cb) => cb !== onVitalUpdate)
      this.vitalCallbacks.set(patientId, filtered)
    }
  }

  // ── Agents WebSocket ────────────────────────────────────────────────────────

  connectAgentsSocket(): () => void {
    const namespace = '/ws/agents'
    let socket = this.sockets.get(namespace)

    if (!socket) {
      socket = this.createSocket(namespace)
      this.sockets.set(namespace, socket)
    }

    const { updateAgentStatus, addExecution, updateExecution } = useAgentStore.getState()

    socket.on('agent_status', (data: AgentStatusUpdate) => {
      updateAgentStatus(data.agentId, data.status)
    })

    socket.on('execution_started', (data: AgentExecutionUpdate) => {
      addExecution({
        id: data.executionId,
        agentId: data.agentId as AgentExecution['agentId'],
        agentName: data.agentId,
        tier: 'tier1_ingestion',
        status: 'running',
        triggeredBy: 'system',
        triggeredAt: data.timestamp,
        startedAt: data.timestamp,
        queueDepth: 0,
      } as AgentExecution)
    })

    socket.on('execution_completed', (data: AgentExecutionUpdate) => {
      updateExecution(data.executionId, {
        status: data.status,
        output: data.output,
        completedAt: data.timestamp,
      })
    })

    socket.on('execution_failed', (data: AgentExecutionUpdate) => {
      updateExecution(data.executionId, {
        status: 'failed',
        error: data.error,
        completedAt: data.timestamp,
      })
    })

    return () => {
      socket!.off('agent_status')
      socket!.off('execution_started')
      socket!.off('execution_completed')
      socket!.off('execution_failed')
    }
  }

  // ── Notifications WebSocket ─────────────────────────────────────────────────

  connectNotificationsSocket(): () => void {
    const namespace = '/ws/notifications'
    let socket = this.sockets.get(namespace)

    if (!socket) {
      socket = this.createSocket(namespace)
      this.sockets.set(namespace, socket)
    }

    const { addAlert } = useAlertStore.getState()

    socket.on('alert', (data: NotificationEvent) => {
      const alert: ClinicalAlert = {
        id: data.id,
        patientId: data.patientId ?? '',
        patientName: data.patientName ?? '',
        severity: data.severity,
        category: 'vital_sign',
        title: data.title,
        description: data.message,
        timestamp: data.timestamp,
        isRead: false,
        isAcknowledged: false,
        escalationCount: 0,
      }
      addAlert(alert)

      // Browser notification
      if (
        'Notification' in window &&
        Notification.permission === 'granted' &&
        (data.severity === 'critical' || data.severity === 'urgent')
      ) {
        new Notification(`InHealth Alert: ${data.title}`, {
          body: data.message,
          icon: '/favicon.svg',
          tag: data.id,
          requireInteraction: data.severity === 'critical',
        })
      }
    })

    socket.on('critical_alert', (data: NotificationEvent) => {
      // Critical alerts also trigger audio
      try {
        const audio = new Audio('/sounds/critical-alert.mp3')
        audio.volume = 0.5
        audio.play().catch(() => {/* silent fail */})
      } catch {
        // Audio not available
      }
    })

    return () => {
      socket!.off('alert')
      socket!.off('critical_alert')
    }
  }

  // ── Disconnect All ──────────────────────────────────────────────────────────

  disconnectAll(): void {
    this.sockets.forEach((socket, namespace) => {
      socket.disconnect()
      console.info(`[WS] Disconnected ${namespace}`)
    })
    this.sockets.clear()
    this.vitalCallbacks.clear()
    this.reconnectTimers.forEach((timer) => clearTimeout(timer))
    this.reconnectTimers.clear()
  }

  getSocket(namespace: string): Socket | undefined {
    return this.sockets.get(namespace)
  }

  isConnected(namespace: string): boolean {
    return this.sockets.get(namespace)?.connected ?? false
  }
}

// Singleton instance
export const wsManager = new WebSocketManager()

export default wsManager
