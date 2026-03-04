import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  ClipboardCheck,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronRight,
  Sparkles,
} from 'lucide-react'
import { format, isAfter, isPast } from 'date-fns'
import toast from 'react-hot-toast'
import type { CareGap, CareGapPriority, CareGapCategory } from '@/types/clinical'
import api from '@/services/api'
import { cn } from '@/lib/utils'

interface CareGapListProps {
  careGaps: CareGap[]
  patientId: string
  onGapUpdated?: () => void
}

const PRIORITY_CONFIG: Record<CareGapPriority, { label: string; bg: string; text: string; border: string }> = {
  critical: { label: 'Critical', bg: 'bg-danger-50 dark:bg-danger-900/20', text: 'text-danger-700 dark:text-danger-400', border: 'border-danger-200 dark:border-danger-800' },
  high: { label: 'High', bg: 'bg-orange-50 dark:bg-orange-900/20', text: 'text-orange-700 dark:text-orange-400', border: 'border-orange-200 dark:border-orange-800' },
  medium: { label: 'Medium', bg: 'bg-warning-50 dark:bg-warning-900/20', text: 'text-warning-700 dark:text-warning-400', border: 'border-warning-200 dark:border-warning-800' },
  low: { label: 'Low', bg: 'bg-clinical-50 dark:bg-clinical-800', text: 'text-clinical-600 dark:text-clinical-400', border: 'border-clinical-200 dark:border-clinical-700' },
}

const CATEGORY_ICONS: Record<CareGapCategory, React.ElementType> = {
  preventive: ClipboardCheck,
  chronic_management: AlertTriangle,
  medication: ClipboardCheck,
  referral: ChevronRight,
  follow_up: Clock,
  immunization: ClipboardCheck,
  screening: ClipboardCheck,
}

const CATEGORY_LABELS: Record<CareGapCategory, string> = {
  preventive: 'Preventive',
  chronic_management: 'Chronic Mgmt',
  medication: 'Medication',
  referral: 'Referral',
  follow_up: 'Follow-up',
  immunization: 'Immunization',
  screening: 'Screening',
}

export default function CareGapList({ careGaps, patientId, onGapUpdated }: CareGapListProps) {
  const [filter, setFilter] = useState<'all' | CareGapPriority>('all')
  const queryClient = useQueryClient()

  const closeGapMutation = useMutation({
    mutationFn: (gapId: string) =>
      api.post(`/clinical/care-gaps/${gapId}/close/`, { patient_id: patientId }),
    onSuccess: () => {
      toast.success('Care gap closed')
      queryClient.invalidateQueries({ queryKey: ['care-gaps', patientId] })
      onGapUpdated?.()
    },
    onError: () => toast.error('Failed to close care gap'),
  })

  const deferGapMutation = useMutation({
    mutationFn: (gapId: string) =>
      api.post(`/clinical/care-gaps/${gapId}/defer/`, {
        patient_id: patientId,
        defer_days: 90,
      }),
    onSuccess: () => {
      toast.success('Care gap deferred 90 days')
      queryClient.invalidateQueries({ queryKey: ['care-gaps', patientId] })
      onGapUpdated?.()
    },
    onError: () => toast.error('Failed to defer care gap'),
  })

  const openGaps = careGaps.filter((g) => g.status === 'open')
  const filtered = filter === 'all' ? openGaps : openGaps.filter((g) => g.priority === filter)

  // Sort: critical → high → due date → title
  const sorted = [...filtered].sort((a, b) => {
    const priority = ['critical', 'high', 'medium', 'low']
    const pa = priority.indexOf(a.priority)
    const pb = priority.indexOf(b.priority)
    if (pa !== pb) return pa - pb
    if (a.dueDate && b.dueDate) {
      return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime()
    }
    return 0
  })

  return (
    <div className="space-y-3">
      {/* Filter tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {(['all', 'critical', 'high', 'medium', 'low'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              'px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors',
              filter === f
                ? 'bg-primary-600 text-white'
                : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground',
            )}
          >
            {f === 'all' ? `All (${openGaps.length})` : `${PRIORITY_CONFIG[f].label} (${openGaps.filter((g) => g.priority === f).length})`}
          </button>
        ))}
      </div>

      {/* Gap list */}
      <div className="space-y-2">
        {sorted.length === 0 ? (
          <div className="py-8 text-center">
            <CheckCircle2 className="w-8 h-8 text-secondary-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-foreground">No open care gaps</p>
            <p className="text-xs text-muted-foreground mt-1">
              {filter !== 'all' ? 'Try changing the filter' : 'Excellent care compliance!'}
            </p>
          </div>
        ) : (
          sorted.map((gap) => (
            <CareGapCard
              key={gap.id}
              gap={gap}
              onClose={() => closeGapMutation.mutate(gap.id)}
              onDefer={() => deferGapMutation.mutate(gap.id)}
              isClosing={closeGapMutation.isPending}
              isDeferring={deferGapMutation.isPending}
            />
          ))
        )}
      </div>
    </div>
  )
}

// ─── Care Gap Card ────────────────────────────────────────────────────────────

function CareGapCard({
  gap,
  onClose,
  onDefer,
  isClosing,
  isDeferring,
}: {
  gap: CareGap
  onClose: () => void
  onDefer: () => void
  isClosing: boolean
  isDeferring: boolean
}) {
  const [showActions, setShowActions] = useState(false)
  const priorityConfig = PRIORITY_CONFIG[gap.priority]
  const CategoryIcon = CATEGORY_ICONS[gap.category] ?? ClipboardCheck

  const isOverdue = gap.dueDate && isPast(new Date(gap.dueDate))
  const isDueSoon = gap.dueDate && !isOverdue && isAfter(new Date(gap.dueDate), new Date()) &&
    new Date(gap.dueDate).getTime() - Date.now() < 30 * 24 * 60 * 60 * 1000

  return (
    <motion.div
      layout
      className={cn(
        'border rounded-xl overflow-hidden bg-card transition-all',
        isOverdue ? 'border-danger-300 dark:border-danger-700' : priorityConfig.border,
      )}
    >
      {/* Main row */}
      <div className="flex items-start gap-3 px-4 py-3">
        {/* Icon */}
        <div className={cn('p-1.5 rounded-lg flex-shrink-0', priorityConfig.bg)}>
          <CategoryIcon className={cn('w-4 h-4', priorityConfig.text)} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-foreground">{gap.title}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{gap.description}</p>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded border capitalize', priorityConfig.bg, priorityConfig.text, priorityConfig.border)}>
                {priorityConfig.label}
              </span>
              <span className="text-[10px] font-medium text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                {CATEGORY_LABELS[gap.category]}
              </span>
            </div>
          </div>

          {/* Due date */}
          {gap.dueDate && (
            <div className={cn('flex items-center gap-1.5 mt-1.5 text-xs', isOverdue ? 'text-danger-600 dark:text-danger-400' : isDueSoon ? 'text-warning-600 dark:text-warning-400' : 'text-muted-foreground')}>
              <Clock className="w-3 h-3" />
              <span>
                {isOverdue ? 'Overdue · ' : isDueSoon ? 'Due soon · ' : ''}
                {format(new Date(gap.dueDate), 'MMM d, yyyy')}
              </span>
            </div>
          )}

          {/* AI recommendation */}
          {gap.aiRecommendation && (
            <div className="mt-2 flex items-start gap-1.5 p-2 bg-primary-50/60 dark:bg-primary-900/10 rounded-lg">
              <Sparkles className="w-3.5 h-3.5 text-primary-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-primary-700 dark:text-primary-300 leading-relaxed">
                {gap.aiRecommendation}
              </p>
            </div>
          )}

          {/* Measure badge */}
          {gap.measure && (
            <p className="text-[10px] text-muted-foreground mt-1.5 font-mono">{gap.measure}</p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 pb-3 flex items-center gap-2">
        <button
          onClick={onClose}
          disabled={isClosing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold bg-secondary-600 hover:bg-secondary-700 text-white rounded-lg transition-colors disabled:opacity-50"
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          Close Gap
        </button>
        <button
          onClick={onDefer}
          disabled={isDeferring}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold border border-border text-muted-foreground hover:bg-accent hover:text-foreground rounded-lg transition-colors disabled:opacity-50"
        >
          <Clock className="w-3.5 h-3.5" />
          Defer 90d
        </button>
      </div>
    </motion.div>
  )
}
