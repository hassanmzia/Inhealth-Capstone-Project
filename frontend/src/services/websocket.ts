import { useAuthStore } from '@/store/authStore'
import { useAlertStore } from '@/store/alertStore'
import { useAgentStore } from '@/store/agentStore'
import type { ClinicalAlert } from '@/types/clinical'
import type { AgentExecution, AgentStatusInfo } from '@/types/agent'

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

// ─── Reconnecting WebSocket ───────────────────────────────────────────────────

type MessageHandler = (data: Record<string, unknown>) => void

class ReconnectingWS {
  private ws: WebSocket | null = null
  private url: string
  private handlers: MessageHandler[] = []
  private reconnectDelay = 2000
  private maxDelay = 30000
  private stopped = false
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  constructor(url: string) {
    this.url = url
  }

  connect(): void {
    if (this.stopped) return

    const token = useAuthStore.getState().token
    const wsUrl = this.url + (token ? `?token=${encodeURIComponent(token)}` : '')

    try {
      this.ws = new WebSocket(wsUrl)
    } catch {
      this.scheduleReconnect()
      return
    }

    this.ws.onopen = () => {
      console.info(`[WS] Connected: ${this.url}`)
      this.reconnectDelay = 2000
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>
        this.handlers.forEach((h) => h(data))
      } catch {
        // ignore non-JSON frames
      }
    }

    this.ws.onclose = (event) => {
      if (!this.stopped) {
        console.warn(`[WS] Closed (${event.code}): ${this.url}`)
        this.scheduleReconnect()
      }
    }

    this.ws.onerror = () => {
      // onerror is always followed by onclose — reconnect handled there
    }
  }

  private scheduleReconnect(): void {
    if (this.stopped) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxDelay)
      this.connect()
    }, this.reconnectDelay)
  }

  addHandler(handler: MessageHandler): void {
    this.handlers.push(handler)
  }

  removeHandler(handler: MessageHandler): void {
    this.handlers = this.handlers.filter((h) => h !== handler)
  }

  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }

  disconnect(): void {
    this.stopped = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// ─── Build WebSocket URL ──────────────────────────────────────────────────────

function wsUrl(path: string): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${window.location.host}${path}`
}

// ─── Socket Manager ───────────────────────────────────────────────────────────

class WebSocketManager {
  private sockets: Map<string, ReconnectingWS> = new Map()
  private vitalCallbacks: Map<string, ((data: VitalUpdate) => void)[]> = new Map()

  // ── Vitals WebSocket ────────────────────────────────────────────────────────

  subscribeToVitals(
    patientId: string,
    onVitalUpdate: (data: VitalUpdate) => void,
  ): () => void {
    const path = `/ws/vitals/${patientId}/`
    let sock = this.sockets.get(path)

    if (!sock) {
      sock = new ReconnectingWS(wsUrl(path))
      sock.connect()
      this.sockets.set(path, sock)
    }

    const handler: MessageHandler = (data) => {
      if (data.event === 'vital_update') {
        onVitalUpdate(data.payload as VitalUpdate)
      }
    }
    sock.addHandler(handler)

    const callbacks = this.vitalCallbacks.get(patientId) ?? []
    callbacks.push(onVitalUpdate)
    this.vitalCallbacks.set(patientId, callbacks)

    return () => {
      sock!.removeHandler(handler)
      const cbs = this.vitalCallbacks.get(patientId) ?? []
      this.vitalCallbacks.set(patientId, cbs.filter((cb) => cb !== onVitalUpdate))
    }
  }

  // ── Agents WebSocket (FastAPI /agents/ws) ───────────────────────────────────

  connectAgentsSocket(): () => void {
    const path = '/agents/ws'
    let sock = this.sockets.get(path)

    if (!sock) {
      sock = new ReconnectingWS(wsUrl(path))
      sock.connect()
      this.sockets.set(path, sock)
    }

    const { updateAgentStatus, addExecution, updateExecution } = useAgentStore.getState()

    const handler: MessageHandler = (data) => {
      const event = data.event as string

      if (event === 'agent_status') {
        const payload = data as unknown as AgentStatusUpdate
        updateAgentStatus(payload.agentId, payload.status)
      } else if (event === 'execution_started') {
        const payload = data as unknown as AgentExecutionUpdate
        addExecution({
          id: payload.executionId,
          agentId: payload.agentId as AgentExecution['agentId'],
          agentName: payload.agentId,
          tier: 'tier1_ingestion',
          status: 'running',
          triggeredBy: 'system',
          triggeredAt: payload.timestamp,
          startedAt: payload.timestamp,
          queueDepth: 0,
        } as AgentExecution)
      } else if (event === 'execution_completed') {
        const payload = data as unknown as AgentExecutionUpdate
        updateExecution(payload.executionId, {
          status: payload.status,
          output: payload.output,
          completedAt: payload.timestamp,
        })
      } else if (event === 'execution_failed') {
        const payload = data as unknown as AgentExecutionUpdate
        updateExecution(payload.executionId, {
          status: 'failed',
          error: payload.error,
          completedAt: payload.timestamp,
        })
      }
    }

    sock.addHandler(handler)

    return () => {
      sock!.removeHandler(handler)
    }
  }

  // ── Notifications WebSocket (Django Channels /ws/alerts/) ───────────────────

  connectNotificationsSocket(): () => void {
    const path = '/ws/alerts/'
    let sock = this.sockets.get(path)

    if (!sock) {
      sock = new ReconnectingWS(wsUrl(path))
      sock.connect()
      this.sockets.set(path, sock)
    }

    const { addAlert } = useAlertStore.getState()

    const handler: MessageHandler = (data) => {
      const event = data.event as string
      if (event !== 'alert' && event !== 'critical_alert') return

      const payload = data.payload as NotificationEvent | undefined
      if (!payload) return

      const alert: ClinicalAlert = {
        id: payload.id,
        patientId: payload.patientId ?? '',
        patientName: payload.patientName ?? '',
        severity: payload.severity,
        category: 'vital_sign',
        title: payload.title,
        description: payload.message,
        timestamp: payload.timestamp,
        isRead: false,
        isAcknowledged: false,
        escalationCount: 0,
      }
      addAlert(alert)

      if (
        'Notification' in window &&
        Notification.permission === 'granted' &&
        (payload.severity === 'critical' || payload.severity === 'urgent')
      ) {
        new Notification(`InHealth Alert: ${payload.title}`, {
          body: payload.message,
          icon: '/favicon.svg',
          tag: payload.id,
          requireInteraction: payload.severity === 'critical',
        })
      }

      if (event === 'critical_alert') {
        try {
          const audio = new Audio('/sounds/critical-alert.mp3')
          audio.volume = 0.5
          audio.play().catch(() => {/* silent fail */})
        } catch {
          // Audio not available
        }
      }
    }

    sock.addHandler(handler)

    return () => {
      sock!.removeHandler(handler)
    }
  }

  // ── Disconnect All ──────────────────────────────────────────────────────────

  disconnectAll(): void {
    this.sockets.forEach((sock, path) => {
      sock.disconnect()
      console.info(`[WS] Disconnected: ${path}`)
    })
    this.sockets.clear()
    this.vitalCallbacks.clear()
  }

  isConnected(path: string): boolean {
    return this.sockets.get(path)?.connected ?? false
  }
}

// Singleton instance
export const wsManager = new WebSocketManager()

export default wsManager
