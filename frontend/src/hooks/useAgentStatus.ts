import { useEffect, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAllAgentStatuses, getAgentHistory } from '@/services/agents'
import { useAgentStore } from '@/store/agentStore'
import { wsManager } from '@/services/websocket'
import type { AgentId, AgentStatus } from '@/types/agent'

interface UseAgentStatusOptions {
  pollInterval?: number   // milliseconds
  enableWebSocket?: boolean
}

interface UseAgentStatusReturn {
  agentStatuses: Record<string, AgentStatus>
  activeCount: number
  errorCount: number
  isLoading: boolean
  refetch: () => void
  getStatus: (agentId: AgentId) => AgentStatus
}

export function useAgentStatus({
  pollInterval = 15000,
  enableWebSocket = true,
}: UseAgentStatusOptions = {}): UseAgentStatusReturn {
  const {
    agentStatuses,
    setAgentStatuses,
    updateAgentStatus,
  } = useAgentStore()

  const cleanupRef = useRef<(() => void) | null>(null)

  // Poll agent statuses
  const { isLoading, refetch } = useQuery({
    queryKey: ['agent-statuses'],
    queryFn: async () => {
      const statuses = await getAllAgentStatuses()
      const statusMap: Record<string, AgentStatus> = {}
      statuses.forEach((s) => {
        statusMap[s.agentId] = s.status
      })
      setAgentStatuses(statusMap)
      return statuses
    },
    refetchInterval: pollInterval,
    staleTime: pollInterval / 2,
  })

  // WebSocket for real-time updates
  useEffect(() => {
    if (!enableWebSocket) return

    const cleanup = wsManager.connectAgentsSocket()
    cleanupRef.current = cleanup

    return () => {
      cleanup()
      cleanupRef.current = null
    }
  }, [enableWebSocket])

  const getStatus = useCallback(
    (agentId: AgentId): AgentStatus => {
      return agentStatuses[agentId] ?? 'idle'
    },
    [agentStatuses],
  )

  const activeCount = Object.values(agentStatuses).filter(
    (s) => s === 'running' || s === 'active',
  ).length

  const errorCount = Object.values(agentStatuses).filter(
    (s) => s === 'error',
  ).length

  return {
    agentStatuses,
    activeCount,
    errorCount,
    isLoading,
    refetch,
    getStatus,
  }
}

// ─── Single agent status hook ──────────────────────────────────────────────────

export function useSingleAgentStatus(agentId: AgentId) {
  const { agentStatuses, agentLastRun, agentErrorMessages } = useAgentStore()

  return {
    status: agentStatuses[agentId] ?? 'idle',
    lastRun: agentLastRun[agentId],
    errorMessage: agentErrorMessages[agentId],
  }
}

// ─── Agent execution stream hook ──────────────────────────────────────────────

export function useAgentExecutionStream(agentId?: AgentId) {
  const { executions, updateExecution, addExecution } = useAgentStore()

  const agentExecutions = agentId
    ? executions.filter((e) => e.agentId === agentId)
    : executions

  const runningExecution = agentExecutions.find((e) => e.status === 'running')
  const latestExecution = agentExecutions[0]

  return {
    executions: agentExecutions,
    runningExecution,
    latestExecution,
    isRunning: !!runningExecution,
  }
}
