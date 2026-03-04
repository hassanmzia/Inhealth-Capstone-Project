import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type {
  AgentId,
  AgentStatus,
  AgentExecution,
  AgentPipeline,
  HITLRequest,
  AgentMetrics,
} from '@/types/agent'
import { AGENT_DEFINITIONS } from '@/types/agent'

// ─── Agent Store State ────────────────────────────────────────────────────────

interface AgentStoreState {
  // Agent statuses (25 agents)
  agentStatuses: Record<string, AgentStatus>
  agentExecutionCounts: Record<string, number>
  agentLastRun: Record<string, string>
  agentErrorMessages: Record<string, string>

  // Execution log
  executions: AgentExecution[]
  totalExecutions: number
  isLoadingExecutions: boolean

  // Active pipelines
  activePipelines: AgentPipeline[]

  // HITL queue
  hitlRequests: HITLRequest[]
  pendingHITLCount: number

  // Metrics
  metrics: AgentMetrics[]

  // UI state
  selectedAgentId: AgentId | null
  executionLogFilter: ExecutionLogFilter

  // Actions
  setAgentStatuses: (statuses: Record<string, AgentStatus>) => void
  updateAgentStatus: (agentId: string, status: AgentStatus) => void
  incrementExecutionCount: (agentId: string) => void
  setAgentLastRun: (agentId: string, timestamp: string) => void
  setAgentError: (agentId: string, error: string | null) => void

  addExecution: (execution: AgentExecution) => void
  setExecutions: (executions: AgentExecution[], total: number) => void
  updateExecution: (executionId: string, updates: Partial<AgentExecution>) => void
  prependExecution: (execution: AgentExecution) => void

  setActivePipelines: (pipelines: AgentPipeline[]) => void
  updatePipeline: (pipelineId: string, updates: Partial<AgentPipeline>) => void

  setHITLRequests: (requests: HITLRequest[]) => void
  addHITLRequest: (request: HITLRequest) => void
  resolveHITLRequest: (requestId: string, decision: HITLRequest['decision']) => void

  setMetrics: (metrics: AgentMetrics[]) => void
  setSelectedAgent: (agentId: AgentId | null) => void
  setExecutionLogFilter: (filter: Partial<ExecutionLogFilter>) => void
}

// ─── Filter Types ─────────────────────────────────────────────────────────────

export interface ExecutionLogFilter {
  agentId: AgentId | null
  tier: string | null
  status: string | null
  patientId: string | null
  dateFrom: string | null
  dateTo: string | null
}

const DEFAULT_EXECUTION_FILTER: ExecutionLogFilter = {
  agentId: null,
  tier: null,
  status: null,
  patientId: null,
  dateFrom: null,
  dateTo: null,
}

// ─── Initial agent statuses ───────────────────────────────────────────────────

function buildInitialStatuses(): Record<string, AgentStatus> {
  return AGENT_DEFINITIONS.reduce(
    (acc, agent) => {
      acc[agent.id] = 'idle'
      return acc
    },
    {} as Record<string, AgentStatus>,
  )
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useAgentStore = create<AgentStoreState>()(
  subscribeWithSelector((set, get) => ({
    agentStatuses: buildInitialStatuses(),
    agentExecutionCounts: {},
    agentLastRun: {},
    agentErrorMessages: {},

    executions: [],
    totalExecutions: 0,
    isLoadingExecutions: false,

    activePipelines: [],

    hitlRequests: [],
    pendingHITLCount: 0,

    metrics: [],

    selectedAgentId: null,
    executionLogFilter: DEFAULT_EXECUTION_FILTER,

    // ── Agent Status Actions ─────────────────────────────────────────────────

    setAgentStatuses: (statuses) => {
      set({ agentStatuses: statuses })
    },

    updateAgentStatus: (agentId, status) => {
      set((state) => ({
        agentStatuses: { ...state.agentStatuses, [agentId]: status },
      }))
    },

    incrementExecutionCount: (agentId) => {
      set((state) => ({
        agentExecutionCounts: {
          ...state.agentExecutionCounts,
          [agentId]: (state.agentExecutionCounts[agentId] ?? 0) + 1,
        },
      }))
    },

    setAgentLastRun: (agentId, timestamp) => {
      set((state) => ({
        agentLastRun: { ...state.agentLastRun, [agentId]: timestamp },
      }))
    },

    setAgentError: (agentId, error) => {
      set((state) => {
        const msgs = { ...state.agentErrorMessages }
        if (error) {
          msgs[agentId] = error
        } else {
          delete msgs[agentId]
        }
        return { agentErrorMessages: msgs }
      })
    },

    // ── Execution Actions ────────────────────────────────────────────────────

    addExecution: (execution) => {
      set((state) => ({
        executions: [execution, ...state.executions].slice(0, 500),
        totalExecutions: state.totalExecutions + 1,
      }))
    },

    setExecutions: (executions, total) => {
      set({ executions, totalExecutions: total })
    },

    updateExecution: (executionId, updates) => {
      set((state) => ({
        executions: state.executions.map((e) =>
          e.id === executionId ? { ...e, ...updates } : e,
        ),
      }))
    },

    prependExecution: (execution) => {
      set((state) => ({
        executions: [execution, ...state.executions].slice(0, 500),
      }))
    },

    // ── Pipeline Actions ─────────────────────────────────────────────────────

    setActivePipelines: (pipelines) => {
      set({ activePipelines: pipelines })
    },

    updatePipeline: (pipelineId, updates) => {
      set((state) => ({
        activePipelines: state.activePipelines.map((p) =>
          p.id === pipelineId ? { ...p, ...updates } : p,
        ),
      }))
    },

    // ── HITL Actions ─────────────────────────────────────────────────────────

    setHITLRequests: (requests) => {
      set({
        hitlRequests: requests,
        pendingHITLCount: requests.filter((r) => !r.decision).length,
      })
    },

    addHITLRequest: (request) => {
      set((state) => ({
        hitlRequests: [request, ...state.hitlRequests],
        pendingHITLCount: state.pendingHITLCount + 1,
      }))
    },

    resolveHITLRequest: (requestId, decision) => {
      set((state) => ({
        hitlRequests: state.hitlRequests.map((r) =>
          r.id === requestId ? { ...r, decision } : r,
        ),
        pendingHITLCount: Math.max(0, state.pendingHITLCount - 1),
      }))
    },

    // ── Metric Actions ───────────────────────────────────────────────────────

    setMetrics: (metrics) => {
      set({ metrics })
    },

    // ── UI Actions ───────────────────────────────────────────────────────────

    setSelectedAgent: (agentId) => {
      set({ selectedAgentId: agentId })
    },

    setExecutionLogFilter: (filter) => {
      set((state) => ({
        executionLogFilter: { ...state.executionLogFilter, ...filter },
      }))
    },
  })),
)

// ─── Selectors ────────────────────────────────────────────────────────────────

export const selectRunningAgents = (state: AgentStoreState) =>
  Object.entries(state.agentStatuses)
    .filter(([, status]) => status === 'running')
    .map(([id]) => id)

export const selectErrorAgents = (state: AgentStoreState) =>
  Object.entries(state.agentStatuses)
    .filter(([, status]) => status === 'error')
    .map(([id]) => id)

export const selectTotalActiveAgents = (state: AgentStoreState) =>
  Object.values(state.agentStatuses).filter((s) => s === 'running' || s === 'active').length
