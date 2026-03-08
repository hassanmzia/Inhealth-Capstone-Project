import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Sparkles,
  CheckCircle2,
  XCircle,
  ExternalLink,
  BarChart2,
  Clock,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  Send,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { formatDistanceToNow } from 'date-fns'
import {
  approveRecommendation,
  rejectRecommendation,
  submitRecommendationFeedback,
  type AIRecommendation,
} from '@/services/agents'
import { cn, getTierColor } from '@/lib/utils'
import type { AgentTier } from '@/types/agent'

interface AIRecommendationPanelProps {
  recommendations: AIRecommendation[]
  onDecision?: () => void
  showHITL?: boolean
  maxItems?: number
}

const EVIDENCE_CONFIG = {
  A: { label: 'Level A', color: 'text-secondary-600 dark:text-secondary-400', bg: 'bg-secondary-50 dark:bg-secondary-900/20', desc: 'Strong evidence' },
  B: { label: 'Level B', color: 'text-primary-600 dark:text-primary-400', bg: 'bg-primary-50 dark:bg-primary-900/20', desc: 'Moderate evidence' },
  C: { label: 'Level C', color: 'text-warning-600 dark:text-warning-400', bg: 'bg-warning-50 dark:bg-warning-900/20', desc: 'Expert consensus' },
  D: { label: 'Level D', color: 'text-muted-foreground', bg: 'bg-muted', desc: 'Expert opinion' },
}

const PRIORITY_CONFIG = {
  critical: { label: 'Critical', color: 'text-danger-600 dark:text-danger-400', bg: 'bg-danger-50 dark:bg-danger-900/20', border: 'border-danger-200 dark:border-danger-800' },
  urgent: { label: 'Urgent', color: 'text-warning-600 dark:text-warning-400', bg: 'bg-warning-50 dark:bg-warning-900/20', border: 'border-warning-200 dark:border-warning-800' },
  soon: { label: 'Soon', color: 'text-primary-600 dark:text-primary-400', bg: 'bg-primary-50 dark:bg-primary-900/20', border: 'border-primary-200 dark:border-primary-800' },
  routine: { label: 'Routine', color: 'text-muted-foreground', bg: 'bg-muted', border: 'border-border' },
}

export default function AIRecommendationPanel({
  recommendations,
  onDecision,
  showHITL = true,
  maxItems = 10,
}: AIRecommendationPanelProps) {
  const displayed = recommendations.slice(0, maxItems)

  if (displayed.length === 0) {
    return (
      <div className="py-8 text-center">
        <Sparkles className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
        <p className="text-sm text-muted-foreground">No AI recommendations</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {displayed.map((rec) => (
        <RecommendationCard
          key={rec.id}
          recommendation={rec}
          onDecision={onDecision}
          showHITL={showHITL}
        />
      ))}
    </div>
  )
}

// ─── Recommendation Card ──────────────────────────────────────────────────────

function RecommendationCard({
  recommendation: rec,
  onDecision,
  showHITL,
}: {
  recommendation: AIRecommendation
  onDecision?: () => void
  showHITL: boolean
}) {
  const queryClient = useQueryClient()
  const tierColors = getTierColor(rec.agentId.split('_').slice(0, -1).join('_') as AgentTier || 'tier3_clinical')
  const evidenceConfig = EVIDENCE_CONFIG[rec.evidenceLevel] ?? EVIDENCE_CONFIG.D
  const priorityConfig = PRIORITY_CONFIG[rec.priority] ?? PRIORITY_CONFIG.routine

  // Feedback state
  const [localRating, setLocalRating] = useState<1 | 2 | null>(rec.feedbackRating ?? null)
  const [showCommentBox, setShowCommentBox] = useState(false)
  const [comment, setComment] = useState(rec.feedbackComment ?? '')

  const approveMutation = useMutation({
    mutationFn: () => approveRecommendation(rec.id),
    onSuccess: () => {
      toast.success('Recommendation approved — care plan created')
      queryClient.invalidateQueries({ queryKey: ['fhir', 'care-plans'] })
      queryClient.invalidateQueries({ queryKey: ['care-gaps'] })
      onDecision?.()
    },
    onError: () => toast.error('Failed to approve'),
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectRecommendation(rec.id, 'Rejected by clinician'),
    onSuccess: () => {
      toast.success('Recommendation rejected')
      onDecision?.()
    },
    onError: () => toast.error('Failed to reject'),
  })

  const feedbackMutation = useMutation({
    mutationFn: ({ rating, feedbackComment }: { rating: 1 | 2; feedbackComment?: string }) =>
      submitRecommendationFeedback(rec.id, rating, feedbackComment),
    onSuccess: (_data, variables) => {
      setLocalRating(variables.rating)
      setShowCommentBox(false)
      toast.success(variables.rating === 2 ? 'Marked as helpful' : 'Marked as not helpful')
    },
    onError: () => toast.error('Failed to submit feedback'),
  })

  const isPending = rec.status === 'pending'
  const isApproved = rec.status === 'approved'
  const isRejected = rec.status === 'rejected'
  const isDecided = isApproved || isRejected
  const hasFeedback = localRating !== null

  return (
    <motion.div
      layout
      className={cn(
        'border rounded-xl overflow-hidden bg-card transition-all',
        isPending && showHITL
          ? 'border-purple-300 dark:border-purple-700 shadow-sm'
          : 'border-border',
        isApproved && 'border-secondary-300 dark:border-secondary-700',
        isRejected && 'border-danger-300 dark:border-danger-700 opacity-75',
      )}
    >
      <div className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Agent badge */}
            <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border', tierColors.bg, tierColors.text, tierColors.border)}>
              <Sparkles className="w-2.5 h-2.5" />
              {rec.agentName}
            </span>

            {/* Priority */}
            <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded border', priorityConfig.bg, priorityConfig.color, priorityConfig.border)}>
              {priorityConfig.label}
            </span>

            {/* Status */}
            {isApproved && (
              <span className="text-[10px] font-semibold text-secondary-600 bg-secondary-50 dark:bg-secondary-900/20 px-1.5 py-0.5 rounded border border-secondary-200">
                Approved
              </span>
            )}
            {isRejected && (
              <span className="text-[10px] font-semibold text-danger-600 bg-danger-50 dark:bg-danger-900/20 px-1.5 py-0.5 rounded border border-danger-200">
                Rejected
              </span>
            )}
            {isPending && showHITL && (
              <span className="text-[10px] font-semibold text-purple-600 bg-purple-50 dark:bg-purple-900/20 px-1.5 py-0.5 rounded border border-purple-200 flex items-center gap-1">
                <Clock className="w-2.5 h-2.5" />
                Pending Review
              </span>
            )}
          </div>

          {/* Evidence level */}
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded', evidenceConfig.bg, evidenceConfig.color)}>
              {evidenceConfig.label}
            </span>
            <span className="text-[10px] text-muted-foreground font-mono bg-muted rounded px-1.5 py-0.5">
              {rec.confidence}%
            </span>
          </div>
        </div>

        {/* Title */}
        <p className="text-sm font-semibold text-foreground">{rec.title}</p>

        {/* Recommendation text */}
        <p className="text-sm text-foreground/80 leading-relaxed">{rec.recommendation}</p>

        {/* Feature attribution chart */}
        {rec.featureImportance && rec.featureImportance.length > 0 && (
          <div className="p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center gap-1.5 mb-2">
              <BarChart2 className="w-3 h-3 text-muted-foreground" />
              <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Key Factors</p>
            </div>
            <div className="space-y-1.5">
              {rec.featureImportance.slice(0, 5).map((f, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="w-24 truncate text-[11px] text-muted-foreground" title={f.feature}>
                    {f.feature}
                  </div>
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn('h-full rounded-full transition-all duration-500', f.direction === 'positive' ? 'bg-danger-400' : 'bg-secondary-400')}
                      style={{ width: `${Math.abs(f.value) * 100}%` }}
                    />
                  </div>
                  <div className={cn('text-[11px] font-mono w-10 text-right', f.direction === 'positive' ? 'text-danger-600' : 'text-secondary-600')}>
                    {f.direction === 'positive' ? '+' : '-'}{(Math.abs(f.value) * 100).toFixed(0)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Source */}
        {rec.sourceGuideline && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>Source: {rec.sourceGuideline}</span>
            {rec.sourceUrl && (
              <a
                href={rec.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline flex items-center gap-1"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        )}

        {/* Timestamp */}
        <p className="text-[10px] text-muted-foreground">
          {formatDistanceToNow(new Date(rec.createdAt), { addSuffix: true })}
          {rec.expiresAt && ` · expires ${formatDistanceToNow(new Date(rec.expiresAt))}`}
        </p>

        {/* HITL Actions */}
        {showHITL && isPending && (
          <div className="flex items-center gap-2 pt-1 border-t border-border">
            <button
              onClick={() => approveMutation.mutate()}
              disabled={approveMutation.isPending || rejectMutation.isPending}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold bg-secondary-600 hover:bg-secondary-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Approve
            </button>
            <button
              onClick={() => rejectMutation.mutate()}
              disabled={approveMutation.isPending || rejectMutation.isPending}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold border border-border text-danger-600 dark:text-danger-400 hover:bg-danger-50 dark:hover:bg-danger-900/20 rounded-lg transition-colors disabled:opacity-50"
            >
              <XCircle className="w-3.5 h-3.5" />
              Reject
            </button>
          </div>
        )}

        {/* Clinician Feedback — shown after approve/reject */}
        {isDecided && (
          <div className="pt-2 border-t border-border">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Was this recommendation helpful?
              </span>
              <div className="flex items-center gap-1">
                {/* Thumbs Up */}
                <button
                  onClick={() => {
                    if (localRating !== 2) {
                      feedbackMutation.mutate({ rating: 2, feedbackComment: comment || undefined })
                    }
                  }}
                  disabled={feedbackMutation.isPending}
                  className={cn(
                    'p-1.5 rounded-lg transition-colors',
                    localRating === 2
                      ? 'bg-secondary-100 dark:bg-secondary-900/30 text-secondary-600'
                      : 'text-muted-foreground hover:text-secondary-600 hover:bg-secondary-50 dark:hover:bg-secondary-900/20',
                  )}
                  title="Helpful"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>

                {/* Thumbs Down */}
                <button
                  onClick={() => {
                    if (localRating !== 1) {
                      feedbackMutation.mutate({ rating: 1, feedbackComment: comment || undefined })
                    }
                  }}
                  disabled={feedbackMutation.isPending}
                  className={cn(
                    'p-1.5 rounded-lg transition-colors',
                    localRating === 1
                      ? 'bg-danger-100 dark:bg-danger-900/30 text-danger-600'
                      : 'text-muted-foreground hover:text-danger-600 hover:bg-danger-50 dark:hover:bg-danger-900/20',
                  )}
                  title="Not helpful"
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                </button>

                {/* Comment toggle */}
                <button
                  onClick={() => setShowCommentBox(!showCommentBox)}
                  className={cn(
                    'p-1.5 rounded-lg transition-colors',
                    showCommentBox
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600'
                      : 'text-muted-foreground hover:text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20',
                  )}
                  title="Add comment"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* Feedback badge */}
            {hasFeedback && !showCommentBox && (
              <p className="text-[10px] text-muted-foreground mt-1">
                {localRating === 2 ? 'Marked as helpful' : 'Marked as not helpful'}
                {rec.feedbackComment && ` — "${rec.feedbackComment}"`}
              </p>
            )}

            {/* Comment input */}
            {showCommentBox && (
              <div className="mt-2 flex items-center gap-2">
                <input
                  type="text"
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Add a comment on this recommendation..."
                  className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-border bg-muted/50 text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary-400"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && comment.trim()) {
                      feedbackMutation.mutate({
                        rating: localRating ?? 2,
                        feedbackComment: comment.trim(),
                      })
                    }
                  }}
                />
                <button
                  onClick={() => {
                    if (comment.trim()) {
                      feedbackMutation.mutate({
                        rating: localRating ?? 2,
                        feedbackComment: comment.trim(),
                      })
                    }
                  }}
                  disabled={!comment.trim() || feedbackMutation.isPending}
                  className="p-1.5 rounded-lg bg-primary-600 text-white hover:bg-primary-700 transition-colors disabled:opacity-50"
                  title="Submit feedback"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
