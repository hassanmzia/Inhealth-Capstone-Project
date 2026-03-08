import api from './api'
import type {
  AgentId,
  AgentStatusInfo,
  AgentExecution,
  AgentMetrics,
  HITLRequest,
  HITLDecision,
  AgentPipeline,
  LangfuseTrace,
  A2AMessage,
} from '@/types/agent'

// ─── Agent Status ─────────────────────────────────────────────────────────────

export async function getAllAgentStatuses(): Promise<AgentStatusInfo[]> {
  const response = await api.get<AgentStatusInfo[]>('/agents/status/')
  return response.data
}

export async function getAgentStatus(agentId: AgentId): Promise<AgentStatusInfo> {
  const response = await api.get<AgentStatusInfo>(`/agents/${agentId}/status/`)
  return response.data
}

// ─── Agent Trigger ────────────────────────────────────────────────────────────

export interface TriggerAgentParams {
  agentId: AgentId
  patientId?: string
  input?: Record<string, unknown>
  priority?: 'low' | 'normal' | 'high' | 'critical'
}

export async function triggerAgent(params: TriggerAgentParams): Promise<AgentExecution> {
  const response = await api.post<AgentExecution>(`/agents/${params.agentId}/trigger/`, {
    patient_id: params.patientId,
    input: params.input,
    priority: params.priority ?? 'normal',
  })
  return response.data
}

export async function triggerPipeline(
  pipelineId: string,
  patientId?: string,
  input?: Record<string, unknown>,
): Promise<AgentPipeline> {
  const response = await api.post<AgentPipeline>(`/agents/pipelines/${pipelineId}/run/`, {
    patient_id: patientId,
    input,
  })
  return response.data
}

export async function triggerFullPipeline(patientId: string): Promise<AgentPipeline> {
  const response = await api.post<AgentPipeline>('/agents/pipelines/full/run/', {
    patient_id: patientId,
  })
  return response.data
}

// ─── Agent Execution History ──────────────────────────────────────────────────

export interface ExecutionListParams {
  agentId?: AgentId
  patientId?: string
  status?: string
  tier?: string
  dateFrom?: string
  dateTo?: string
  page?: number
  pageSize?: number
}

export interface PaginatedExecutions {
  count: number
  next?: string
  previous?: string
  results: AgentExecution[]
}

export async function getAgentHistory(params?: ExecutionListParams): Promise<PaginatedExecutions> {
  const response = await api.get<PaginatedExecutions>('/agents/executions/', {
    params: {
      agent_id: params?.agentId,
      patient_id: params?.patientId,
      status: params?.status,
      tier: params?.tier,
      date_from: params?.dateFrom,
      date_to: params?.dateTo,
      page: params?.page ?? 1,
      page_size: params?.pageSize ?? 50,
    },
  })
  return response.data
}

export async function getExecution(executionId: string): Promise<AgentExecution> {
  const response = await api.get<AgentExecution>(`/agents/executions/${executionId}/`)
  return response.data
}

export async function cancelExecution(executionId: string): Promise<void> {
  await api.post(`/agents/executions/${executionId}/cancel/`)
}

// ─── Monitoring Controls ──────────────────────────────────────────────────────

export async function pauseMonitoring(patientId: string): Promise<void> {
  await api.post('/agents/monitoring/pause/', { patient_id: patientId })
}

export async function resumeMonitoring(patientId: string): Promise<void> {
  await api.post('/agents/monitoring/resume/', { patient_id: patientId })
}

export async function pauseAgent(agentId: AgentId): Promise<void> {
  await api.post(`/agents/${agentId}/pause/`)
}

export async function resumeAgent(agentId: AgentId): Promise<void> {
  await api.post(`/agents/${agentId}/resume/`)
}

// ─── HITL (Human-in-the-Loop) ─────────────────────────────────────────────────

export interface HITLListParams {
  status?: 'pending' | 'decided'
  urgency?: string
  agentId?: AgentId
  patientId?: string
  page?: number
}

export async function getPendingHITL(params?: HITLListParams): Promise<HITLRequest[]> {
  const response = await api.get<HITLRequest[]>('/agents/hitl/', {
    params: {
      status: params?.status ?? 'pending',
      urgency: params?.urgency,
      agent_id: params?.agentId,
      patient_id: params?.patientId,
      page: params?.page,
    },
  })
  return response.data
}

export async function getHITLRequest(hitlId: string): Promise<HITLRequest> {
  const response = await api.get<HITLRequest>(`/agents/hitl/${hitlId}/`)
  return response.data
}

export async function submitHITLDecision(
  hitlId: string,
  decision: HITLDecision,
  note?: string,
  modifiedRecommendation?: string,
): Promise<HITLRequest> {
  const response = await api.post<HITLRequest>(`/agents/hitl/${hitlId}/decide/`, {
    decision,
    note,
    modified_recommendation: modifiedRecommendation,
  })
  return response.data
}

// ─── Agent Metrics ────────────────────────────────────────────────────────────

export async function getAgentMetrics(
  agentId?: AgentId,
  period: 'day' | 'week' | 'month' = 'day',
): Promise<AgentMetrics[]> {
  const response = await api.get<AgentMetrics[]>('/agents/metrics/', {
    params: { agent_id: agentId, period },
  })
  return response.data
}

// ─── LangGraph Pipeline ───────────────────────────────────────────────────────

export async function getPipelines(): Promise<AgentPipeline[]> {
  const response = await api.get<AgentPipeline[]>('/agents/pipelines/')
  return response.data
}

export async function getPipeline(pipelineId: string): Promise<AgentPipeline> {
  const response = await api.get<AgentPipeline>(`/agents/pipelines/${pipelineId}/`)
  return response.data
}

export async function getActivePipelines(): Promise<AgentPipeline[]> {
  const response = await api.get<AgentPipeline[]>('/agents/pipelines/', {
    params: { status: 'running' },
  })
  return response.data
}

// ─── Langfuse Traces ──────────────────────────────────────────────────────────

export async function getTraces(executionId?: string, limit = 20): Promise<LangfuseTrace[]> {
  const response = await api.get<LangfuseTrace[]>('/agents/traces/', {
    params: { execution_id: executionId, limit },
  })
  return response.data
}

export async function getTrace(traceId: string): Promise<LangfuseTrace> {
  const response = await api.get<LangfuseTrace>(`/agents/traces/${traceId}/`)
  return response.data
}

// ─── A2A Messages ─────────────────────────────────────────────────────────────

export async function getA2AMessages(limit = 50): Promise<A2AMessage[]> {
  const response = await api.get<A2AMessage[]>('/agents/messages/', {
    params: { limit },
  })
  return response.data
}

// ─── AI Recommendations ───────────────────────────────────────────────────────

export interface AIRecommendation {
  id: string
  agentId: AgentId
  agentName: string
  patientId: string
  patientName: string
  title: string
  recommendation: string
  evidenceLevel: 'A' | 'B' | 'C' | 'D'
  confidence: number
  sourceGuideline?: string
  sourceUrl?: string
  category: string
  priority: 'routine' | 'soon' | 'urgent' | 'critical'
  status: 'pending' | 'approved' | 'rejected' | 'modified' | 'expired'
  createdAt: string
  expiresAt?: string
  featureImportance?: Array<{
    feature: string
    value: number
    direction: 'positive' | 'negative'
  }>
  hitlRequestId?: string
  feedbackRating?: 1 | 2 | null
  feedbackComment?: string
}

export async function getRecommendations(
  patientId?: string,
  status?: string,
  limit = 20,
): Promise<AIRecommendation[]> {
  const response = await api.get<AIRecommendation[]>('/agents/recommendations/', {
    params: { patient_id: patientId, status, limit },
  })
  return response.data
}

export async function approveRecommendation(
  recommendationId: string,
  note?: string,
): Promise<AIRecommendation> {
  const response = await api.post<AIRecommendation>(
    `/agents/recommendations/${recommendationId}/approve/`,
    { note },
  )
  return response.data
}

export async function rejectRecommendation(
  recommendationId: string,
  reason: string,
): Promise<AIRecommendation> {
  const response = await api.post<AIRecommendation>(
    `/agents/recommendations/${recommendationId}/reject/`,
    { reason },
  )
  return response.data
}

export async function submitRecommendationFeedback(
  recommendationId: string,
  rating: 1 | 2,
  comment?: string,
): Promise<{ id: string; feedback_rating: number; feedback_comment: string }> {
  const response = await api.post(
    `/agents/recommendations/${recommendationId}/feedback/`,
    { rating, comment },
  )
  return response.data
}
