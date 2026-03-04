import { useEffect, useRef, useCallback, useState } from 'react'
import { io, Socket } from 'socket.io-client'
import { useAuthStore } from '@/store/authStore'

const WS_URL = import.meta.env.VITE_WS_URL ?? ''

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error'

interface UseWebSocketOptions {
  namespace: string
  onConnect?: () => void
  onDisconnect?: (reason: string) => void
  onError?: (error: Error) => void
  autoConnect?: boolean
  reconnectionAttempts?: number
}

interface UseWebSocketReturn {
  socket: Socket | null
  connectionState: ConnectionState
  connect: () => void
  disconnect: () => void
  emit: (event: string, data?: unknown) => void
  on: (event: string, handler: (...args: unknown[]) => void) => void
  off: (event: string, handler?: (...args: unknown[]) => void) => void
}

export function useWebSocket({
  namespace,
  onConnect,
  onDisconnect,
  onError,
  autoConnect = true,
  reconnectionAttempts = 10,
}: UseWebSocketOptions): UseWebSocketReturn {
  const socketRef = useRef<Socket | null>(null)
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected')
  const { token } = useAuthStore()

  const connect = useCallback(() => {
    if (socketRef.current?.connected) return

    setConnectionState('connecting')

    const socket = io(`${WS_URL}${namespace}`, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 10000,
    })

    socket.on('connect', () => {
      setConnectionState('connected')
      onConnect?.()
    })

    socket.on('disconnect', (reason) => {
      setConnectionState('disconnected')
      onDisconnect?.(reason)
    })

    socket.on('connect_error', (error) => {
      setConnectionState('error')
      onError?.(error)
    })

    socket.on('reconnecting', () => {
      setConnectionState('connecting')
    })

    socketRef.current = socket
  }, [namespace, token, reconnectionAttempts, onConnect, onDisconnect, onError])

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect()
      socketRef.current = null
      setConnectionState('disconnected')
    }
  }, [])

  const emit = useCallback((event: string, data?: unknown) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data)
    }
  }, [])

  const on = useCallback((event: string, handler: (...args: unknown[]) => void) => {
    socketRef.current?.on(event, handler)
  }, [])

  const off = useCallback((event: string, handler?: (...args: unknown[]) => void) => {
    if (handler) {
      socketRef.current?.off(event, handler)
    } else {
      socketRef.current?.off(event)
    }
  }, [])

  useEffect(() => {
    if (autoConnect && token) {
      connect()
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect()
        socketRef.current = null
      }
    }
  }, [autoConnect, token])

  return {
    socket: socketRef.current,
    connectionState,
    connect,
    disconnect,
    emit,
    on,
    off,
  }
}

// ─── Specialized vitals hook ──────────────────────────────────────────────────

export function useVitalsSocket(
  patientId: string | undefined,
  onVitalUpdate: (data: unknown) => void,
) {
  const { socket, connectionState, emit } = useWebSocket({
    namespace: '/ws/vitals',
    autoConnect: !!patientId,
  })

  useEffect(() => {
    if (!socket || !patientId) return

    emit('join', { patient_id: patientId })
    socket.on('vital_update', onVitalUpdate)
    socket.on(`vital_update:${patientId}`, onVitalUpdate)

    return () => {
      socket.off('vital_update', onVitalUpdate)
      socket.off(`vital_update:${patientId}`, onVitalUpdate)
      emit('leave', { patient_id: patientId })
    }
  }, [socket, patientId, onVitalUpdate, emit])

  return { connectionState }
}
