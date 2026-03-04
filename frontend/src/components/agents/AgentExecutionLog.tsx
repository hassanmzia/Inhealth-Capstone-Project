import { useState } from 'react'
import { formatDistanceToNow, format } from 'date-fns'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronDown,
  ChevronRight,
  Filter,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  AlertCircle,
  User,
  Eye,
} from 'lucide-react'
import type { AgentExecution } from '@/types/agent'
import { AGENT_DEFINITIONS } from '@/types/agent'
import { cn, getTierColor } from '@/lib/utils'

interface AgentExecutionLogProps {
  executions: AgentExecution[]
  isLoading?: boolean
  onRefresh?: () => void
  showFilters?: boolean
  maxHeight?: number
}

const STATUS_CONFIG: Record<string, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  completed: { icon: CheckCircle2, color: 'text-secondary-600 dark:text-secondary-400', bg: 'bg-secondary-50 dark:bg-secondary-900/20', label: 'Completed' },
  running: { icon: Loader2, color: 'text-primary-600 dark:text-primary-400', bg: 'bg-primary-50 dark:bg-primary-900/20', label: 'Running' },
  failed: { icon: XCircle, color: 'text-danger-600 dark:text-danger-400', bg: 'bg-danger-50 dark:bg-danger-900/20', label: 'Failed' },
  queued: { icon: Clock, color: 'text-warning-600 dark:text-warning-400', bg: 'bg-warning-50 dark:bg-warning-900/20', label: 'Queued' },
  pending_hitl: { icon: AlertCircle, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-50 dark:bg-purple-900/20', label: 'Pending HITL' },
  cancelled: { icon: XCircle, color: 'text-muted-foreground', bg: 'bg-muted', label: 'Cancelled' },
}

export default function AgentExecutionLog({
  executions,
  isLoading = false,
  onRefresh,
  showFilters = true,
  maxHeight = 480,
}: AgentExecutionLogProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterTier, setFilterTier] = useState<string>('all')

  const filteredExecutions = executions.filter((e) => {
    if (filterStatus !== 'all' && e.status !== filterStatus) return false
    if (filterTier !== 'all' && e.tier !== filterTier) return false
    return true
  })

  return (
    <div className="flex flex-col">
      {/* Header */}
      {showFilters && (
        <div className="flex items-center gap-3 mb-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground font-medium">Filter:</span>
          </div>

          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="text-xs border border-border rounded-md px-2 py-1 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary-400"
          >
            <option value="all">All statuses</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="failed">Failed</option>
            <option value="pending_hitl">Pending HITL</option>
            <option value="queued">Queued</option>
          </select>

          <select
            value={filterTier}
            onChange={(e) => setFilterTier(e.target.value)}
            className="text-xs border border-border rounded-md px-2 py-1 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary-400"
          >
            <option value="all">All tiers</option>
            <option value="tier1_ingestion">Tier 1 - Ingestion</option>
            <option value="tier2_analysis">Tier 2 - Analysis</option>
            <option value="tier3_clinical">Tier 3 - Clinical</option>
            <option value="tier4_coordination">Tier 4 - Coordination</option>
            <option value="tier5_engagement">Tier 5 - Engagement</option>
          </select>

          <span className="text-xs text-muted-foreground ml-auto">
            {filteredExecutions.length} records
          </span>

          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
            >
              <RefreshCw className={cn('w-3.5 h-3.5', isLoading && 'animate-spin')} />
            </button>
          )}
        </div>
      )}

      {/* Log list */}
      <div
        className="overflow-y-auto divide-y divide-border border border-border rounded-lg bg-card"
        style={{ maxHeight }}
      >
        {isLoading && filteredExecutions.length === 0 ? (
          <div className="py-12 text-center">
            <Loader2 className="w-6 h-6 text-primary-400 animate-spin mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">Loading executions...</p>
          </div>
        ) : filteredExecutions.length === 0 ? (
          <div className="py-12 text-center">
            <Clock className="w-6 h-6 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No executions found</p>
          </div>
        ) : (
          filteredExecutions.map((execution) => (
            <ExecutionRow
              key={execution.id}
              execution={execution}
              expanded={expandedId === execution.id}
              onToggle={() => setExpandedId(expandedId === execution.id ? null : execution.id)}
            />
          ))
        )}
      </div>
    </div>
  )
}

// ─── Execution Row ────────────────────────────────────────────────────────────

function ExecutionRow({
  execution,
  expanded,
  onToggle,
}: {
  execution: AgentExecution
  expanded: boolean
  onToggle: () => void
}) {
  const statusConfig = STATUS_CONFIG[execution.status] ?? STATUS_CONFIG.cancelled
  const StatusIcon = statusConfig.icon
  const tierColors = getTierColor(execution.tier)
  const agentDef = AGENT_DEFINITIONS.find((d) => d.id === execution.agentId)

  const runtime = execution.runtimeSeconds
    ? execution.runtimeSeconds < 60
      ? `${execution.runtimeSeconds}s`
      : `${Math.round(execution.runtimeSeconds / 60)}m`
    : null

  return (
    <div>
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-accent/50 transition-colors text-left group"
      >
        {/* Status icon */}
        <div className={cn('p-1 rounded', statusConfig.bg)}>
          <StatusIcon
            className={cn(
              'w-3.5 h-3.5',
              statusConfig.color,
              execution.status === 'running' && 'animate-spin',
            )}
          />
        </div>

        {/* Agent info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-foreground truncate">
              {execution.agentName}
            </span>
            <span
              className={cn(
                'px-1.5 py-0.5 rounded text-[10px] font-medium',
                tierColors.bg,
                tierColors.text,
              )}
            >
              {execution.tier.replace('tier', 'T').replace('_', ' ')}
            </span>
            {execution.patientName && (
              <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <User className="w-3 h-3" />
                {execution.patientName}
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 mt-0.5">
            <span className="text-[10px] text-muted-foreground">
              {formatDistanceToNow(new Date(execution.triggeredAt), { addSuffix: true })}
            </span>
            {runtime && (
              <span className="text-[10px] text-muted-foreground font-mono">
                {runtime}
              </span>
            )}
            {execution.tokensUsed && (
              <span className="text-[10px] text-muted-foreground">
                {execution.tokensUsed.toLocaleString()} tokens
              </span>
            )}
          </div>
        </div>

        {/* Triggered by */}
        <div className="text-right hidden sm:block">
          <p className="text-[10px] text-muted-foreground capitalize">{execution.triggeredBy}</p>
        </div>

        {/* Expand icon */}
        <div className="text-muted-foreground">
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4 group-hover:text-foreground transition-colors" />
          )}
        </div>
      </button>

      {/* Expanded details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 bg-accent/30 border-t border-border space-y-3">
              {/* Metadata grid */}
              <div className="grid grid-cols-2 gap-x-6 gap-y-1 pt-2.5 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground w-20">Execution ID:</span>
                  <span className="font-mono text-foreground">{execution.id.slice(0, 12)}...</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground w-20">Started:</span>
                  <span className="font-mono text-foreground">
                    {execution.startedAt ? format(new Date(execution.startedAt), 'HH:mm:ss') : '—'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground w-20">Completed:</span>
                  <span className="font-mono text-foreground">
                    {execution.completedAt ? format(new Date(execution.completedAt), 'HH:mm:ss') : '—'}
                  </span>
                </div>
                {execution.traceId && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground w-20">Trace ID:</span>
                    <span className="font-mono text-foreground flex items-center gap-1">
                      {execution.traceId.slice(0, 10)}...
                      <Eye className="w-3 h-3 text-primary-400" />
                    </span>
                  </div>
                )}
              </div>

              {/* Error message */}
              {execution.error && (
                <div className="p-2 bg-danger-50 dark:bg-danger-900/20 rounded border border-danger-200 dark:border-danger-800">
                  <p className="text-xs text-danger-700 dark:text-danger-300 font-mono">
                    {execution.error}
                  </p>
                </div>
              )}

              {/* Output preview */}
              {execution.output && (
                <div>
                  <p className="text-xs font-medium text-foreground mb-1">Output:</p>
                  <pre className="text-[10px] font-mono bg-muted rounded p-2 overflow-x-auto max-h-32 text-foreground">
                    {JSON.stringify(execution.output, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
