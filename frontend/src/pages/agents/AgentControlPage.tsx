import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  BrainCircuit,
  Activity,
  RefreshCw,
  Zap,
} from 'lucide-react'
import { getAllAgentStatuses, getAgentHistory, getPendingHITL } from '@/services/agents'
import { useAgentStore, selectTotalActiveAgents } from '@/store/agentStore'
import AgentStatusGrid from '@/components/agents/AgentStatusGrid'
import AgentExecutionLog from '@/components/agents/AgentExecutionLog'
import AgentControlPanel from '@/components/agents/AgentControlPanel'
import AgentActivityTimeline from '@/components/charts/AgentActivityTimeline'
import type { AgentId } from '@/types/agent'

export default function AgentControlPage() {
  const [selectedAgentId, setSelectedAgentId] = useState<AgentId | null>(null)
  const [activeView, setActiveView] = useState<'grid' | 'timeline'>('grid')
  const activeAgents = useAgentStore(selectTotalActiveAgents)
  const { setAgentStatuses, setExecutions, setHITLRequests } = useAgentStore()

  // Fetch agent statuses
  const { refetch: refetchStatuses } = useQuery({
    queryKey: ['agent-statuses'],
    queryFn: async () => {
      const statuses = await getAllAgentStatuses()
      const statusMap = statuses.reduce((acc, s) => ({ ...acc, [s.agentId]: s.status }), {} as Record<string, AgentId>)
      setAgentStatuses(statusMap as Record<string, import('@/types/agent').AgentStatus>)
      return statuses
    },
    refetchInterval: 10000,
  })

  // Fetch execution history
  const { data: executionData, isLoading: isLoadingExec, refetch: refetchExec } = useQuery({
    queryKey: ['agent-executions'],
    queryFn: async () => {
      const data = await getAgentHistory({ pageSize: 100 })
      setExecutions(data.results, data.count)
      return data
    },
    refetchInterval: 15000,
  })

  // Fetch HITL requests
  const { data: hitlRequests, refetch: refetchHITL } = useQuery({
    queryKey: ['hitl-requests'],
    queryFn: async () => {
      const requests = await getPendingHITL()
      setHITLRequests(requests)
      return requests
    },
    refetchInterval: 30000,
  })

  const executions = executionData?.results ?? []

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-primary-500" />
            AI Agent Control Center
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Monitor and control all 25 AI agents in real-time
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Active count */}
          <div className="flex items-center gap-2 px-3 py-2 bg-secondary-50 dark:bg-secondary-900/20 border border-secondary-200 dark:border-secondary-800 rounded-lg">
            <Activity className="w-4 h-4 text-secondary-500 animate-pulse" />
            <span className="text-sm font-semibold text-secondary-700 dark:text-secondary-400">
              {activeAgents} running
            </span>
          </div>
          <button
            onClick={() => { refetchStatuses(); refetchExec() }}
            className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-accent transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Agents', value: 25, color: 'text-foreground' },
          { label: 'Running Now', value: activeAgents, color: 'text-primary-600 dark:text-primary-400' },
          { label: 'Today\'s Executions', value: executions.length, color: 'text-foreground' },
          { label: 'Pending HITL', value: hitlRequests?.length ?? 0, color: hitlRequests?.length ? 'text-warning-600 dark:text-warning-400' : 'text-secondary-600' },
        ].map((stat) => (
          <div key={stat.label} className="clinical-card text-center">
            <p className={`text-2xl font-bold font-mono ${stat.color}`}>{stat.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{stat.label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="xl:col-span-2 space-y-6">
          {/* View toggle */}
          <div className="flex items-center gap-2">
            <div className="flex border border-border rounded-lg overflow-hidden">
              <button
                onClick={() => setActiveView('grid')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${activeView === 'grid' ? 'bg-primary-600 text-white' : 'text-muted-foreground hover:bg-accent'}`}
              >
                Agent Grid
              </button>
              <button
                onClick={() => setActiveView('timeline')}
                className={`px-4 py-2 text-sm font-medium transition-colors ${activeView === 'timeline' ? 'bg-primary-600 text-white' : 'text-muted-foreground hover:bg-accent'}`}
              >
                Activity Timeline
              </button>
            </div>
          </div>

          {/* Agent status grid */}
          {activeView === 'grid' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="clinical-card">
              <AgentStatusGrid
                onSelectAgent={setSelectedAgentId}
                selectedAgentId={selectedAgentId}
              />
            </motion.div>
          )}

          {/* Activity timeline */}
          {activeView === 'timeline' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="clinical-card">
              <h2 className="text-sm font-bold text-foreground mb-4">Agent Activity Timeline (24h)</h2>
              <AgentActivityTimeline executions={executions} height={400} />
            </motion.div>
          )}

          {/* Execution log */}
          <div className="clinical-card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-foreground">Execution Log</h2>
              <span className="text-xs text-muted-foreground">{executionData?.count ?? 0} total</span>
            </div>
            <AgentExecutionLog
              executions={executions}
              isLoading={isLoadingExec}
              onRefresh={refetchExec}
            />
          </div>
        </div>

        {/* Right panel: Agent control */}
        <div className="space-y-6">
          <div className="clinical-card">
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-4 h-4 text-primary-500" />
              <h2 className="text-sm font-bold text-foreground">Agent Control</h2>
            </div>
            <AgentControlPanel
              pendingHITL={hitlRequests ?? []}
              onHITLDecision={refetchHITL}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
