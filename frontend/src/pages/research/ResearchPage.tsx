import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  FlaskConical,
  BookOpen,
  FileText,
  Microscope,
  ExternalLink,
  Bookmark,
  Download,
  Loader2,
  Sparkles,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import api from '@/services/api'
import { cn } from '@/lib/utils'

type QueryType = 'literature' | 'trials' | 'guidelines' | 'qa'

interface SearchResult {
  id: string
  title: string
  authors?: string[]
  abstract?: string
  source: string
  url?: string
  evidenceLevel?: string
  publishedDate?: string
  relevanceScore?: number
  type: QueryType
  trialStatus?: string
  phase?: string
}

const QUERY_TYPES: { id: QueryType; label: string; icon: React.ElementType; placeholder: string }[] = [
  { id: 'literature', label: 'Literature', icon: BookOpen, placeholder: 'Search PubMed literature...' },
  { id: 'trials', label: 'Clinical Trials', icon: FlaskConical, placeholder: 'Search clinicaltrials.gov...' },
  { id: 'guidelines', label: 'Guidelines', icon: FileText, placeholder: 'Search clinical guidelines...' },
  { id: 'qa', label: 'AI Q&A', icon: Sparkles, placeholder: 'Ask a clinical question...' },
]

export default function ResearchPage() {
  const [query, setQuery] = useState('')
  const [queryType, setQueryType] = useState<QueryType>('literature')
  const [results, setResults] = useState<SearchResult[]>([])
  const [savedSearches, setSavedSearches] = useState<string[]>([])
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [aiAnswer, setAiAnswer] = useState('')

  const searchMutation = useMutation({
    mutationFn: async (q: string) => {
      const response = await api.post('/research/search/', {
        query: q,
        type: queryType,
      })
      return response.data
    },
    onSuccess: (data) => {
      setResults(data.results ?? [])
      if (queryType === 'qa') {
        setAiAnswer(data.answer ?? '')
      }
    },
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) searchMutation.mutate(query)
  }

  const saveSearch = (q: string) => {
    setSavedSearches((prev) => [...new Set([q, ...prev])].slice(0, 10))
  }

  const queryTypeConfig = QUERY_TYPES.find((t) => t.id === queryType)!

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
          <Microscope className="w-5 h-5 text-primary-500" />
          AI Research Interface
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Search literature, clinical trials, and guidelines with AI assistance
        </p>
      </div>

      {/* Search bar */}
      <div className="clinical-card space-y-4">
        {/* Query type selector */}
        <div className="flex gap-2 flex-wrap">
          {QUERY_TYPES.map((t) => (
            <button
              key={t.id}
              onClick={() => setQueryType(t.id)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors border',
                queryType === t.id
                  ? 'bg-primary-600 text-white border-primary-600'
                  : 'border-border text-muted-foreground hover:bg-accent hover:text-foreground',
              )}
            >
              <t.icon className="w-4 h-4" />
              {t.label}
            </button>
          ))}
        </div>

        {/* Search input */}
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={queryTypeConfig.placeholder}
              className="w-full pl-12 pr-4 py-3.5 rounded-xl border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 placeholder:text-muted-foreground"
            />
          </div>
          <button
            type="submit"
            disabled={!query.trim() || searchMutation.isPending}
            className="flex items-center gap-2 px-6 py-3.5 bg-gradient-clinical text-white rounded-xl font-semibold text-sm hover:opacity-90 transition-opacity disabled:opacity-60"
          >
            {searchMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Search className="w-4 h-4" />
            )}
            Search
          </button>
        </form>

        {/* Saved searches */}
        {savedSearches.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-muted-foreground">Recent:</span>
            {savedSearches.map((s, i) => (
              <button
                key={i}
                onClick={() => { setQuery(s); searchMutation.mutate(s) }}
                className="text-xs text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 px-2 py-0.5 rounded-full hover:bg-primary-100 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* AI Q&A Answer */}
      <AnimatePresence>
        {queryType === 'qa' && aiAnswer && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="clinical-card border-primary-200 dark:border-primary-800 bg-primary-50/30 dark:bg-primary-900/10"
          >
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-4 h-4 text-primary-500" />
              <h3 className="text-sm font-bold text-foreground">AI Clinical Answer</h3>
              <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                GPT-4 + RAG
              </span>
            </div>
            <p className="text-sm text-foreground leading-relaxed">{aiAnswer}</p>
            <p className="text-xs text-muted-foreground mt-3">
              * AI-generated content. Always verify with primary literature before clinical application.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      {searchMutation.isPending && (
        <div className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            <p className="text-sm text-muted-foreground">
              Searching {queryTypeConfig.label.toLowerCase()}...
            </p>
          </div>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {results.length} results
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => saveSearch(query)}
                className="flex items-center gap-1.5 text-xs text-primary-600 hover:underline"
              >
                <Bookmark className="w-3 h-3" />
                Save search
              </button>
              <button
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
              >
                <Download className="w-3 h-3" />
                Export
              </button>
            </div>
          </div>

          {results.map((result) => (
            <ResultCard
              key={result.id}
              result={result}
              expanded={expandedId === result.id}
              onToggle={() => setExpandedId(expandedId === result.id ? null : result.id)}
            />
          ))}
        </div>
      )}

      {searchMutation.isSuccess && results.length === 0 && (
        <div className="text-center py-12">
          <Search className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm font-medium text-foreground">No results found</p>
          <p className="text-xs text-muted-foreground mt-1">Try different search terms or query type</p>
        </div>
      )}
    </div>
  )
}

// ─── Result Card ──────────────────────────────────────────────────────────────

function ResultCard({
  result,
  expanded,
  onToggle,
}: {
  result: SearchResult
  expanded: boolean
  onToggle: () => void
}) {
  const TypeIcon = result.type === 'trials' ? FlaskConical : result.type === 'guidelines' ? FileText : BookOpen

  const evidenceColors: Record<string, string> = {
    A: 'text-secondary-600 bg-secondary-50 dark:bg-secondary-900/20',
    B: 'text-primary-600 bg-primary-50 dark:bg-primary-900/20',
    C: 'text-warning-600 bg-warning-50 dark:bg-warning-900/20',
    I: 'text-muted-foreground bg-muted',
  }

  return (
    <div className="clinical-card hover:shadow-card-hover transition-shadow">
      <button onClick={onToggle} className="w-full text-left">
        <div className="flex items-start gap-3">
          <div className="p-1.5 bg-primary-50 dark:bg-primary-900/20 rounded-lg flex-shrink-0">
            <TypeIcon className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-foreground leading-snug">
                {result.title}
              </h3>
              <div className="flex items-center gap-2 flex-shrink-0">
                {result.evidenceLevel && (
                  <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded', evidenceColors[result.evidenceLevel] ?? evidenceColors.I)}>
                    Level {result.evidenceLevel}
                  </span>
                )}
                {result.relevanceScore !== undefined && (
                  <span className="text-[10px] font-mono text-muted-foreground">
                    {Math.round(result.relevanceScore * 100)}%
                  </span>
                )}
                {expanded ? (
                  <ChevronDown className="w-4 h-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                )}
              </div>
            </div>
            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
              <span>{result.source}</span>
              {result.publishedDate && <span>{result.publishedDate}</span>}
              {result.trialStatus && (
                <span className="text-primary-600 dark:text-primary-400 font-medium">
                  {result.trialStatus}
                </span>
              )}
            </div>
          </div>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="mt-3 pt-3 border-t border-border space-y-3">
              {result.authors && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">Authors:</span> {result.authors.join(', ')}
                </p>
              )}
              {result.abstract && (
                <p className="text-sm text-foreground/80 leading-relaxed">{result.abstract}</p>
              )}
              {result.phase && (
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium">Phase:</span> {result.phase}
                </p>
              )}
              <div className="flex items-center gap-3">
                {result.url && (
                  <a
                    href={result.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-xs font-medium text-primary-600 hover:underline"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    View Full Text
                  </a>
                )}
                <button className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
                  <Bookmark className="w-3.5 h-3.5" />
                  Save
                </button>
                <button className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
                  <Download className="w-3.5 h-3.5" />
                  Export
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
