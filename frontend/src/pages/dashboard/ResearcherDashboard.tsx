import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  FlaskConical,
  BookOpen,
  Search,
  Activity,
  CheckCircle2,
  Clock,
  ExternalLink,
  Loader2,
  Sparkles,
  BarChart3,
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.07 } } }
const ITEM = { hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0 } }

interface ResearcherStats {
  totalMyQueries: number
  activeTrials: number
  evidenceCount: number
  tenantQueriesThisMonth: number
  recentQueries: Array<{
    id: string
    query_text: string
    query_type: string
    status: string
    created_at: string
  }>
  recentEvidence: Array<{
    id: string
    title: string
    journal: string
    year: number
    evidence_level: string
    citation_count: number
  }>
}

const QUERY_STATUS_COLORS: Record<string, string> = {
  completed: 'text-secondary-600 bg-secondary-50 dark:bg-secondary-900/20',
  pending: 'text-warning-600 bg-warning-50 dark:bg-warning-900/20',
  processing: 'text-primary-600 bg-primary-50 dark:bg-primary-900/20',
  failed: 'text-danger-600 bg-danger-50 dark:bg-danger-900/20',
}

const EVIDENCE_LEVEL_COLORS: Record<string, string> = {
  'A': 'text-secondary-700 bg-secondary-100 dark:bg-secondary-900/30',
  'B': 'text-primary-700 bg-primary-100 dark:bg-primary-900/30',
  'C': 'text-warning-700 bg-warning-100 dark:bg-warning-900/30',
  'D': 'text-muted-foreground bg-accent',
}

function getGreeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'morning'
  if (h < 17) return 'afternoon'
  return 'evening'
}

export default function ResearcherDashboard() {
  const navigate = useNavigate()
  const { user } = useAuthStore()

  const { data: stats, isLoading } = useQuery<ResearcherStats>({
    queryKey: ['researcher-dashboard'],
    queryFn: () => api.get('/dashboard/researcher/').then((r) => r.data),
    refetchInterval: 60000,
    placeholderData: {
      totalMyQueries: 0,
      activeTrials: 0,
      evidenceCount: 0,
      tenantQueriesThisMonth: 0,
      recentQueries: [],
      recentEvidence: [],
    },
  })

  const STAT_CARDS = [
    {
      label: 'My Research Queries',
      value: stats?.totalMyQueries ?? 0,
      icon: Search,
      color: 'text-primary-600 dark:text-primary-400',
      bg: 'bg-primary-50 dark:bg-primary-900/20',
      href: '/research',
    },
    {
      label: 'Active Clinical Trials',
      value: stats?.activeTrials ?? 0,
      icon: FlaskConical,
      color: 'text-secondary-600 dark:text-secondary-400',
      bg: 'bg-secondary-50 dark:bg-secondary-900/20',
      href: '/research',
    },
    {
      label: 'Evidence Database',
      value: (stats?.evidenceCount ?? 0).toLocaleString(),
      icon: BookOpen,
      color: 'text-warning-600 dark:text-warning-400',
      bg: 'bg-warning-50 dark:bg-warning-900/20',
    },
    {
      label: 'Queries This Month',
      value: stats?.tenantQueriesThisMonth ?? 0,
      icon: BarChart3,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50 dark:bg-purple-900/20',
    },
  ]

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-6xl">
      {/* Header */}
      <motion.div variants={ITEM} className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Good {getGreeting()}, {user?.firstName}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {format(new Date(), 'EEEE, MMMM d, yyyy')} · Research & Evidence Dashboard
          </p>
        </div>
        <button
          onClick={() => navigate('/research')}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-clinical text-white rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity"
        >
          <Sparkles className="w-4 h-4" />
          New Query
        </button>
      </motion.div>

      {/* Stat cards */}
      <motion.div variants={ITEM} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {STAT_CARDS.map((card) => (
          <button
            key={card.label}
            onClick={() => card.href && navigate(card.href)}
            className={cn(
              'clinical-card text-left hover:shadow-card-hover transition-all duration-200',
              card.href && 'cursor-pointer',
            )}
          >
            <div className="flex items-center justify-between mb-3">
              <div className={cn('p-2 rounded-lg', card.bg)}>
                <card.icon className={cn('w-5 h-5', card.color)} />
              </div>
            </div>
            <p className="text-2xl font-bold text-foreground font-mono tabular-nums">{card.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{card.label}</p>
          </button>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Research Queries */}
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Search className="w-4 h-4 text-muted-foreground" />
              <h2 className="text-sm font-bold text-foreground">My Recent Queries</h2>
            </div>
            <button
              onClick={() => navigate('/research')}
              className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
            >
              View all
            </button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : (stats?.recentQueries ?? []).length === 0 ? (
            <div className="text-center py-8">
              <Search className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-40" />
              <p className="text-sm text-muted-foreground">No research queries yet.</p>
              <button
                onClick={() => navigate('/research')}
                className="mt-3 text-xs text-primary-600 dark:text-primary-400 hover:underline"
              >
                Start your first query →
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {(stats?.recentQueries ?? []).map((q) => (
                <div key={q.id} className="flex items-start gap-3 p-2.5 rounded-lg border border-border bg-card/50">
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-foreground truncate">{q.query_text}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">
                        {q.query_type.replace('_', ' ')}
                      </span>
                      <span className="text-muted-foreground">·</span>
                      <span className="text-[10px] text-muted-foreground">
                        {q.created_at ? format(parseISO(q.created_at), 'MMM d, h:mm a') : '—'}
                      </span>
                    </div>
                  </div>
                  <span
                    className={cn(
                      'flex-shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded capitalize',
                      QUERY_STATUS_COLORS[q.status] ?? 'text-muted-foreground bg-accent',
                    )}
                  >
                    {q.status === 'processing' ? (
                      <span className="flex items-center gap-1">
                        <Loader2 className="w-2.5 h-2.5 animate-spin" />
                        processing
                      </span>
                    ) : q.status === 'completed' ? (
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="w-2.5 h-2.5" />
                        done
                      </span>
                    ) : q.status === 'pending' ? (
                      <span className="flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5" />
                        pending
                      </span>
                    ) : q.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Recent Evidence */}
        <motion.div variants={ITEM} className="clinical-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-muted-foreground" />
              <h2 className="text-sm font-bold text-foreground">Recent Evidence</h2>
            </div>
            <button
              onClick={() => navigate('/research')}
              className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
            >
              Search evidence
            </button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : (stats?.recentEvidence ?? []).length === 0 ? (
            <div className="text-center py-8">
              <BookOpen className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-40" />
              <p className="text-sm text-muted-foreground">No evidence in database yet.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {(stats?.recentEvidence ?? []).map((e) => (
                <div key={e.id} className="p-2.5 rounded-lg border border-border bg-card/50">
                  <div className="flex items-start gap-2">
                    <span
                      className={cn(
                        'flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded mt-0.5',
                        EVIDENCE_LEVEL_COLORS[e.evidence_level] ?? 'text-muted-foreground bg-accent',
                      )}
                    >
                      Level {e.evidence_level}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-foreground line-clamp-2">{e.title}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {e.journal} · {e.year} · {e.citation_count.toLocaleString()} citations
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Quick Access Panel */}
      <motion.div variants={ITEM} className="clinical-card">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-4 h-4 text-muted-foreground" />
          <h2 className="text-sm font-bold text-foreground">Quick Access</h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Literature Search', icon: BookOpen, desc: 'Search PubMed + evidence DB', href: '/research' },
            { label: 'Clinical Trials', icon: FlaskConical, desc: 'Browse recruiting trials', href: '/research' },
            { label: 'AI Q&A', icon: Sparkles, desc: 'Ask clinical questions', href: '/research' },
            { label: 'Analytics', icon: BarChart3, desc: 'Population cohort data', href: '/analytics' },
          ].map((item) => (
            <button
              key={item.label}
              onClick={() => navigate(item.href)}
              className="flex flex-col items-start p-3 rounded-lg border border-border bg-card hover:bg-accent hover:border-primary-300 dark:hover:border-primary-700 transition-all text-left group"
            >
              <item.icon className="w-5 h-5 text-primary-500 mb-2 group-hover:scale-110 transition-transform" />
              <p className="text-xs font-semibold text-foreground">{item.label}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">{item.desc}</p>
            </button>
          ))}
        </div>
      </motion.div>
    </motion.div>
  )
}
