import { formatDistanceToNow } from 'date-fns'
import { motion } from 'framer-motion'
import {
  Database, RefreshCw, FlaskConical, Activity, TrendingUp,
  BarChart3, BrainCircuit, FileText, AlertTriangle, Globe,
  BookOpen, Stethoscope, Target, ClipboardCheck, Pill,
  ClipboardList, Calendar, ArrowRightLeft, Users, Receipt,
  GraduationCap, Heart, Bell, Video, Microscope,
} from 'lucide-react'
import type { AgentId, AgentTier } from '@/types/agent'
import { AGENT_DEFINITIONS } from '@/types/agent'
import { useAgentStore } from '@/store/agentStore'
import { cn, getTierColor } from '@/lib/utils'

// Icon map
const ICON_MAP: Record<string, React.ElementType> = {
  Database, RefreshCw, FlaskConical, Activity, TrendingUp,
  BarChart3, BrainCircuit, FileText, AlertTriangle, Globe,
  BookOpen, Stethoscope, Target, ClipboardCheck, Pill,
  ClipboardList, Calendar, ArrowRightLeft, Users, Receipt,
  GraduationCap, Heart, Bell, Video, Microscope,
}

const TIER_LABELS: Record<AgentTier, string> = {
  tier1_ingestion: 'Ingestion',
  tier2_analysis: 'Analysis',
  tier3_clinical: 'Clinical',
  tier4_coordination: 'Coordination',
  tier5_engagement: 'Engagement',
}

interface AgentStatusGridProps {
  onSelectAgent?: (agentId: AgentId) => void
  selectedAgentId?: AgentId | null
}

export default function AgentStatusGrid({ onSelectAgent, selectedAgentId }: AgentStatusGridProps) {
  const { agentStatuses, agentExecutionCounts, agentLastRun, agentErrorMessages } = useAgentStore()

  // Group agents by tier
  const tierGroups = AGENT_DEFINITIONS.reduce(
    (acc, def) => {
      if (!acc[def.tier]) acc[def.tier] = []
      acc[def.tier].push(def)
      return acc
    },
    {} as Record<AgentTier, typeof AGENT_DEFINITIONS>,
  )

  const tiers: AgentTier[] = [
    'tier1_ingestion',
    'tier2_analysis',
    'tier3_clinical',
    'tier4_coordination',
    'tier5_engagement',
  ]

  return (
    <div className="space-y-6">
      {tiers.map((tier) => {
        const agents = tierGroups[tier] ?? []
        const tierColors = getTierColor(tier)

        return (
          <div key={tier}>
            {/* Tier header */}
            <div className="flex items-center gap-2 mb-3">
              <span
                className={cn(
                  'px-2 py-0.5 rounded text-xs font-semibold border',
                  tierColors.bg,
                  tierColors.text,
                  tierColors.border,
                )}
              >
                {TIER_LABELS[tier]}
              </span>
              <div className="flex-1 h-px bg-border" />
              <span className="text-xs text-muted-foreground">
                {agents.filter((a) => agentStatuses[a.id] === 'running').length} running
              </span>
            </div>

            {/* Agent cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {agents.map((def) => {
                const status = agentStatuses[def.id] ?? 'idle'
                const execCount = agentExecutionCounts[def.id] ?? 0
                const lastRun = agentLastRun[def.id]
                const errorMsg = agentErrorMessages[def.id]
                const Icon = ICON_MAP[def.icon] ?? Activity
                const isSelected = selectedAgentId === def.id

                return (
                  <motion.button
                    key={def.id}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => onSelectAgent?.(def.id as AgentId)}
                    className={cn(
                      'relative flex flex-col gap-2 p-3 rounded-xl border text-left transition-all duration-150 cursor-pointer',
                      isSelected
                        ? 'border-primary-400 dark:border-primary-600 bg-primary-50 dark:bg-primary-900/20 shadow-clinical'
                        : 'border-border bg-card hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-card',
                      status === 'error' && !isSelected && 'border-danger-300 dark:border-danger-700 bg-danger-50/50 dark:bg-danger-900/10',
                    )}
                  >
                    {/* Status indicator dot */}
                    <div className="absolute top-2.5 right-2.5">
                      <StatusDot status={status} />
                    </div>

                    {/* Icon */}
                    <div
                      className={cn(
                        'w-8 h-8 rounded-lg flex items-center justify-center',
                        tierColors.bg,
                      )}
                    >
                      <Icon className={cn('w-4 h-4', tierColors.text)} />
                    </div>

                    {/* Name */}
                    <div>
                      <p className="text-xs font-semibold text-foreground leading-tight line-clamp-2 pr-4">
                        {def.name.replace(' Agent', '')}
                      </p>
                    </div>

                    {/* Stats */}
                    <div className="mt-auto space-y-0.5">
                      <p className="text-[10px] text-muted-foreground">
                        {execCount} runs today
                      </p>
                      {lastRun && (
                        <p className="text-[10px] text-muted-foreground truncate">
                          {formatDistanceToNow(new Date(lastRun), { addSuffix: true })}
                        </p>
                      )}
                      {status === 'running' && (
                        <p className="text-[10px] text-primary-600 dark:text-primary-400 font-medium animate-pulse">
                          Running...
                        </p>
                      )}
                      {status === 'error' && errorMsg && (
                        <p className="text-[10px] text-danger-600 dark:text-danger-400 truncate" title={errorMsg}>
                          {errorMsg}
                        </p>
                      )}
                    </div>

                    {/* HITL badge */}
                    {def.requiresHITL && (
                      <div className="absolute bottom-2.5 right-2.5">
                        <span className="text-[9px] font-bold text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-900/30 rounded px-1">
                          HITL
                        </span>
                      </div>
                    )}
                  </motion.button>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Status Dot ───────────────────────────────────────────────────────────────

function StatusDot({ status }: { status: string }) {
  switch (status) {
    case 'running':
      return <span className="status-dot-running" title="Running" />
    case 'active':
      return <span className="status-dot-active" title="Active" />
    case 'error':
      return <span className="status-dot-error" title="Error" />
    case 'paused':
      return <span className="w-2.5 h-2.5 rounded-full bg-warning-400 flex-shrink-0" title="Paused" />
    default:
      return <span className="status-dot-idle" title="Idle" />
  }
}
