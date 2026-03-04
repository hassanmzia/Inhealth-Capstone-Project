import { useState } from 'react'
import { motion } from 'framer-motion'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Play,
  Pause,
  RefreshCw,
  Zap,
  ChevronDown,
  CheckCircle2,
  XCircle,
  Edit3,
  AlertTriangle,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { useMutation } from '@tanstack/react-query'
import { triggerAgent, triggerFullPipeline, pauseMonitoring, resumeMonitoring, submitHITLDecision } from '@/services/agents'
import type { AgentId, HITLRequest } from '@/types/agent'
import { AGENT_DEFINITIONS } from '@/types/agent'
import { cn, getTierColor } from '@/lib/utils'

interface AgentControlPanelProps {
  patientId?: string
  patientName?: string
  pendingHITL?: HITLRequest[]
  onHITLDecision?: () => void
}

const triggerSchema = z.object({
  agentId: z.string().min(1, 'Select an agent'),
  priority: z.enum(['low', 'normal', 'high', 'critical']),
})

type TriggerForm = z.infer<typeof triggerSchema>

export default function AgentControlPanel({
  patientId,
  patientName,
  pendingHITL = [],
  onHITLDecision,
}: AgentControlPanelProps) {
  const [isMonitoringPaused, setIsMonitoringPaused] = useState(false)
  const [activeTab, setActiveTab] = useState<'trigger' | 'hitl'>('trigger')

  const { register, handleSubmit, reset, formState: { errors } } = useForm<TriggerForm>({
    resolver: zodResolver(triggerSchema),
    defaultValues: { priority: 'normal' },
  })

  // Trigger agent mutation
  const triggerMutation = useMutation({
    mutationFn: (data: TriggerForm) =>
      triggerAgent({
        agentId: data.agentId as AgentId,
        patientId,
        priority: data.priority,
      }),
    onSuccess: (execution) => {
      toast.success(`Agent triggered: ${execution.agentName}`)
      reset()
    },
    onError: () => {
      toast.error('Failed to trigger agent')
    },
  })

  // Full pipeline mutation
  const pipelineMutation = useMutation({
    mutationFn: () => {
      if (!patientId) throw new Error('Patient required for full pipeline')
      return triggerFullPipeline(patientId)
    },
    onSuccess: () => {
      toast.success('Full AI pipeline triggered successfully')
    },
    onError: () => {
      toast.error('Failed to trigger pipeline')
    },
  })

  // Monitoring toggle
  const monitoringMutation = useMutation({
    mutationFn: () => {
      if (!patientId) throw new Error('Patient required')
      return isMonitoringPaused ? resumeMonitoring(patientId) : pauseMonitoring(patientId)
    },
    onSuccess: () => {
      setIsMonitoringPaused((v) => !v)
      toast.success(isMonitoringPaused ? 'Monitoring resumed' : 'Monitoring paused')
    },
    onError: () => {
      toast.error('Failed to update monitoring')
    },
  })

  const onSubmit = (data: TriggerForm) => {
    triggerMutation.mutate(data)
  }

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex border border-border rounded-lg overflow-hidden">
        <button
          onClick={() => setActiveTab('trigger')}
          className={cn(
            'flex-1 py-2 text-sm font-medium transition-colors',
            activeTab === 'trigger'
              ? 'bg-primary-600 text-white'
              : 'bg-card text-muted-foreground hover:bg-accent',
          )}
        >
          Trigger Agent
        </button>
        <button
          onClick={() => setActiveTab('hitl')}
          className={cn(
            'flex-1 py-2 text-sm font-medium transition-colors relative',
            activeTab === 'hitl'
              ? 'bg-primary-600 text-white'
              : 'bg-card text-muted-foreground hover:bg-accent',
          )}
        >
          HITL Queue
          {pendingHITL.length > 0 && (
            <span className="absolute top-1 right-2 w-5 h-5 rounded-full bg-danger-500 text-white text-[10px] font-bold flex items-center justify-center">
              {pendingHITL.length}
            </span>
          )}
        </button>
      </div>

      {/* Trigger Agent Tab */}
      {activeTab === 'trigger' && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* Quick actions */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => pipelineMutation.mutate()}
              disabled={!patientId || pipelineMutation.isPending}
              className="flex items-center justify-center gap-2 px-3 py-2.5 bg-gradient-clinical text-white rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
            >
              {pipelineMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              Run Full Pipeline
            </button>

            <button
              onClick={() => monitoringMutation.mutate()}
              disabled={!patientId || monitoringMutation.isPending}
              className={cn(
                'flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed border',
                isMonitoringPaused
                  ? 'bg-secondary-50 dark:bg-secondary-900/20 text-secondary-700 dark:text-secondary-400 border-secondary-200 dark:border-secondary-800 hover:bg-secondary-100'
                  : 'bg-warning-50 dark:bg-warning-900/20 text-warning-700 dark:text-warning-400 border-warning-200 dark:border-warning-800 hover:bg-warning-100',
              )}
            >
              {monitoringMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : isMonitoringPaused ? (
                <Play className="w-4 h-4" />
              ) : (
                <Pause className="w-4 h-4" />
              )}
              {isMonitoringPaused ? 'Resume' : 'Pause'} Monitor
            </button>
          </div>

          {/* Individual agent trigger */}
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Select Agent
              </label>
              <select
                {...register('agentId')}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary-400"
              >
                <option value="">Choose an agent...</option>
                {['tier1_ingestion', 'tier2_analysis', 'tier3_clinical', 'tier4_coordination', 'tier5_engagement'].map((tier) => (
                  <optgroup key={tier} label={tier.replace('tier', 'Tier ').replace('_', ' ').replace(/(\w+)/, (m) => m.charAt(0).toUpperCase() + m.slice(1))}>
                    {AGENT_DEFINITIONS.filter((d) => d.tier === tier).map((def) => (
                      <option key={def.id} value={def.id}>
                        {def.name}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              {errors.agentId && (
                <p className="text-xs text-danger-500 mt-1">{errors.agentId.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-foreground mb-1">Priority</label>
              <div className="grid grid-cols-4 gap-1">
                {(['low', 'normal', 'high', 'critical'] as const).map((p) => (
                  <label key={p} className="relative">
                    <input type="radio" {...register('priority')} value={p} className="sr-only peer" />
                    <div className={cn(
                      'cursor-pointer text-center py-1.5 rounded border text-xs font-medium transition-colors',
                      'border-border text-muted-foreground hover:border-primary-300',
                      'peer-checked:border-primary-500 peer-checked:bg-primary-50 dark:peer-checked:bg-primary-900/20 peer-checked:text-primary-700 dark:peer-checked:text-primary-400',
                    )}>
                      {p.charAt(0).toUpperCase() + p.slice(1)}
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {patientId && (
              <div className="px-3 py-2 bg-accent rounded-lg">
                <p className="text-xs text-muted-foreground">
                  Target patient: <span className="font-semibold text-foreground">{patientName ?? patientId}</span>
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={triggerMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {triggerMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Trigger Agent
            </button>
          </form>
        </motion.div>
      )}

      {/* HITL Queue Tab */}
      {activeTab === 'hitl' && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-3"
        >
          {pendingHITL.length === 0 ? (
            <div className="py-8 text-center">
              <CheckCircle2 className="w-8 h-8 text-secondary-400 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No pending approvals</p>
            </div>
          ) : (
            pendingHITL.map((request) => (
              <HITLCard
                key={request.id}
                request={request}
                onDecision={() => onHITLDecision?.()}
              />
            ))
          )}
        </motion.div>
      )}
    </div>
  )
}

// ─── HITL Card ────────────────────────────────────────────────────────────────

function HITLCard({ request, onDecision }: { request: HITLRequest; onDecision: () => void }) {
  const [expanded, setExpanded] = useState(false)
  const [modifiedText, setModifiedText] = useState('')
  const [showModify, setShowModify] = useState(false)

  const decisionMutation = useMutation({
    mutationFn: ({ decision, note }: { decision: 'approved' | 'rejected' | 'modified'; note?: string }) =>
      submitHITLDecision(request.id, decision, note, decision === 'modified' ? modifiedText : undefined),
    onSuccess: () => {
      toast.success('Decision recorded')
      onDecision()
    },
    onError: () => toast.error('Failed to record decision'),
  })

  const urgencyColors: Record<string, string> = {
    critical: 'text-danger-600 dark:text-danger-400 bg-danger-50 dark:bg-danger-900/20 border-danger-200',
    urgent: 'text-warning-600 dark:text-warning-400 bg-warning-50 dark:bg-warning-900/20 border-warning-200',
    soon: 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 border-primary-200',
    routine: 'text-muted-foreground bg-muted border-border',
  }

  return (
    <div className="border border-border rounded-xl overflow-hidden bg-card">
      {/* Header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-accent/30 transition-colors"
      >
        <AlertTriangle className="w-4 h-4 text-warning-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-foreground">{request.title}</p>
            <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded border capitalize', urgencyColors[request.urgency] ?? urgencyColors.routine)}>
              {request.urgency}
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">{request.agentName} · {request.patientName}</p>
        </div>
        <ChevronDown className={cn('w-4 h-4 text-muted-foreground flex-shrink-0 transition-transform', expanded && 'rotate-180')} />
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-border space-y-3">
          {/* Recommendation */}
          <div className="mt-3">
            <p className="text-xs font-medium text-foreground mb-1">Recommendation:</p>
            <p className="text-sm text-foreground bg-accent/50 rounded-lg p-3 leading-relaxed">
              {request.recommendation}
            </p>
          </div>

          {/* Metadata */}
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>Evidence: <strong className="text-foreground">{request.evidenceLevel}</strong></span>
            <span>Confidence: <strong className="text-foreground font-mono">{request.confidence}%</strong></span>
            {request.sourceGuideline && (
              <span>Source: <strong className="text-foreground">{request.sourceGuideline}</strong></span>
            )}
          </div>

          {/* Feature importance */}
          {request.featureImportance && request.featureImportance.length > 0 && (
            <div>
              <p className="text-xs font-medium text-foreground mb-2">Key Factors:</p>
              <div className="space-y-1.5">
                {request.featureImportance.slice(0, 4).map((f, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className="w-20 truncate text-[11px] text-muted-foreground">{f.feature}</div>
                    <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn('h-full rounded-full', f.direction === 'positive' ? 'bg-danger-400' : 'bg-secondary-400')}
                        style={{ width: `${Math.abs(f.value) * 100}%` }}
                      />
                    </div>
                    <div className={cn('text-[11px] font-mono', f.direction === 'positive' ? 'text-danger-600' : 'text-secondary-600')}>
                      {f.direction === 'positive' ? '+' : '-'}{(Math.abs(f.value) * 100).toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Modify recommendation */}
          {showModify && (
            <div>
              <label className="block text-xs font-medium text-foreground mb-1">
                Modified Recommendation:
              </label>
              <textarea
                value={modifiedText}
                onChange={(e) => setModifiedText(e.target.value)}
                placeholder="Enter your modified recommendation..."
                rows={3}
                className="w-full text-sm border border-border rounded-lg px-3 py-2 bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary-400 resize-none"
              />
            </div>
          )}

          {/* Decision buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => decisionMutation.mutate({ decision: 'approved' })}
              disabled={decisionMutation.isPending}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-secondary-600 hover:bg-secondary-700 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Approve
            </button>

            <button
              onClick={() => {
                if (!showModify) { setShowModify(true); return }
                if (modifiedText.trim()) decisionMutation.mutate({ decision: 'modified' })
              }}
              disabled={decisionMutation.isPending}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400 border border-primary-200 dark:border-primary-800 rounded-lg text-xs font-semibold hover:bg-primary-100 transition-colors disabled:opacity-50"
            >
              <Edit3 className="w-3.5 h-3.5" />
              Modify
            </button>

            <button
              onClick={() => decisionMutation.mutate({ decision: 'rejected' })}
              disabled={decisionMutation.isPending}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-danger-50 dark:bg-danger-900/20 text-danger-700 dark:text-danger-400 border border-danger-200 dark:border-danger-800 rounded-lg text-xs font-semibold hover:bg-danger-100 transition-colors disabled:opacity-50"
            >
              <XCircle className="w-3.5 h-3.5" />
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
