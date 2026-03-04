import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Search,
  Filter,
  Plus,
  Download,
  Users,
  ChevronUp,
  ChevronDown,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react'
import { format } from 'date-fns'
import api from '@/services/api'
import { RiskScoreBadge } from '@/components/charts/RiskScoreGauge'
import type { PatientSummary } from '@/types/clinical'
import { cn } from '@/lib/utils'

interface PatientListResponse {
  count: number
  results: PatientSummary[]
}

type SortField = 'name' | 'risk_score' | 'last_contact' | 'open_care_gaps'
type SortOrder = 'asc' | 'desc'

export default function PatientListPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [search, setSearch] = useState(searchParams.get('q') ?? '')
  const [sortField, setSortField] = useState<SortField>('risk_score')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [page, setPage] = useState(1)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState({
    riskLevel: searchParams.get('risk') ?? '',
    condition: '',
    hasCareGaps: '',
    alertStatus: '',
  })

  const PAGE_SIZE = 25

  const { data, isLoading, refetch } = useQuery<PatientListResponse>({
    queryKey: ['patients', search, sortField, sortOrder, page, filters],
    queryFn: () =>
      api.get('/patients/', {
        params: {
          search,
          ordering: sortOrder === 'desc' ? `-${sortField}` : sortField,
          page,
          page_size: PAGE_SIZE,
          risk_level: filters.riskLevel,
          condition: filters.condition,
          has_care_gaps: filters.hasCareGaps,
          alert_status: filters.alertStatus,
        },
      }).then((r) => r.data),
    placeholderData: (prev) => prev,
  })

  useEffect(() => {
    if (search) {
      setSearchParams({ q: search })
    } else {
      setSearchParams({})
    }
  }, [search])

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <ChevronDown className="w-3 h-3 text-muted-foreground opacity-30" />
    return sortOrder === 'asc'
      ? <ChevronUp className="w-3 h-3 text-primary-500" />
      : <ChevronDown className="w-3 h-3 text-primary-500" />
  }

  const totalPages = Math.ceil((data?.count ?? 0) / PAGE_SIZE)
  const patients = data?.results ?? []

  return (
    <div className="space-y-4 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Users className="w-5 h-5 text-primary-500" />
            Patients
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data?.count?.toLocaleString() ?? '—'} patients enrolled
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="p-2 rounded-lg border border-border hover:bg-accent text-muted-foreground"
          >
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          </button>
          <button
            onClick={() => {}}
            className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-accent transition-colors"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
          <button
            onClick={() => navigate('/patients/new')}
            className="flex items-center gap-2 px-3 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Patient
          </button>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder="Search by name, MRN, DOB..."
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 placeholder:text-muted-foreground"
          />
        </div>

        <button
          onClick={() => setShowFilters((v) => !v)}
          className={cn(
            'flex items-center gap-2 px-3 py-2 border rounded-lg text-sm font-medium transition-colors',
            showFilters
              ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-300 text-primary-700 dark:text-primary-400'
              : 'border-border text-muted-foreground hover:bg-accent',
          )}
        >
          <Filter className="w-4 h-4" />
          Filters
          {Object.values(filters).some(Boolean) && (
            <span className="w-2 h-2 rounded-full bg-primary-500" />
          )}
        </button>
      </div>

      {/* Filter panel */}
      {showFilters && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="flex flex-wrap gap-3 p-4 bg-accent/50 rounded-xl border border-border"
        >
          <div>
            <label className="block text-xs font-medium text-foreground mb-1">Risk Level</label>
            <select
              value={filters.riskLevel}
              onChange={(e) => setFilters((f) => ({ ...f, riskLevel: e.target.value }))}
              className="text-sm border border-border rounded-lg px-2 py-1.5 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary-400"
            >
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-foreground mb-1">Care Gaps</label>
            <select
              value={filters.hasCareGaps}
              onChange={(e) => setFilters((f) => ({ ...f, hasCareGaps: e.target.value }))}
              className="text-sm border border-border rounded-lg px-2 py-1.5 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary-400"
            >
              <option value="">All</option>
              <option value="true">Has Open Gaps</option>
              <option value="false">No Open Gaps</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-foreground mb-1">Alert Status</label>
            <select
              value={filters.alertStatus}
              onChange={(e) => setFilters((f) => ({ ...f, alertStatus: e.target.value }))}
              className="text-sm border border-border rounded-lg px-2 py-1.5 bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary-400"
            >
              <option value="">All</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="normal">Normal</option>
            </select>
          </div>

          <button
            onClick={() => setFilters({ riskLevel: '', condition: '', hasCareGaps: '', alertStatus: '' })}
            className="self-end text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Clear filters
          </button>
        </motion.div>
      )}

      {/* Patient table */}
      <div className="clinical-card p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-muted/50 border-b border-border">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">
                  <button
                    onClick={() => handleSort('name')}
                    className="flex items-center gap-1 hover:text-foreground"
                  >
                    Patient <SortIcon field="name" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Conditions</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">
                  <button
                    onClick={() => handleSort('risk_score')}
                    className="flex items-center gap-1 hover:text-foreground"
                  >
                    Risk Score <SortIcon field="risk_score" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">
                  <button
                    onClick={() => handleSort('open_care_gaps')}
                    className="flex items-center gap-1 hover:text-foreground"
                  >
                    Care Gaps <SortIcon field="open_care_gaps" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">
                  <button
                    onClick={() => handleSort('last_contact')}
                    className="flex items-center gap-1 hover:text-foreground"
                  >
                    Last Contact <SortIcon field="last_contact" />
                  </button>
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="skeleton h-4 rounded w-full" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : patients.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-muted-foreground text-sm">
                    {search ? `No patients found matching "${search}"` : 'No patients enrolled'}
                  </td>
                </tr>
              ) : (
                patients.map((patient) => (
                  <PatientRow
                    key={patient.id}
                    patient={patient}
                    onClick={() => navigate(`/patients/${patient.id}`)}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border">
            <p className="text-xs text-muted-foreground">
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data?.count ?? 0)} of {data?.count?.toLocaleString()} patients
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-xs rounded-md border border-border hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="px-3 py-1 text-xs text-foreground font-medium">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1 text-xs rounded-md border border-border hover:bg-accent disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── Patient Row ──────────────────────────────────────────────────────────────

function PatientRow({ patient, onClick }: { patient: PatientSummary; onClick: () => void }) {
  return (
    <tr
      onClick={onClick}
      className="hover:bg-accent/40 cursor-pointer transition-colors group"
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-clinical flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {patient.firstName[0]}{patient.lastName[0]}
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              {patient.firstName} {patient.lastName}
            </p>
            <p className="text-xs text-muted-foreground">
              {patient.age}y · {patient.gender} · <span className="font-mono">{patient.mrn}</span>
            </p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          {patient.activeConditions.slice(0, 2).map((c, i) => (
            <span key={i} className="text-[10px] bg-clinical-100 dark:bg-clinical-800 text-clinical-700 dark:text-clinical-300 px-1.5 py-0.5 rounded font-medium truncate max-w-[120px]" title={c.display}>
              {c.code}
            </span>
          ))}
          {patient.activeConditions.length > 2 && (
            <span className="text-[10px] text-muted-foreground">+{patient.activeConditions.length - 2}</span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        {patient.riskScore ? (
          <RiskScoreBadge score={patient.riskScore.score} />
        ) : (
          <span className="text-xs text-muted-foreground">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        {patient.openCareGaps > 0 ? (
          <span className="text-sm font-semibold text-warning-600 dark:text-warning-400">
            {patient.openCareGaps}
          </span>
        ) : (
          <span className="text-sm text-secondary-600 dark:text-secondary-400">0</span>
        )}
      </td>
      <td className="px-4 py-3">
        <span className="text-xs text-muted-foreground">
          {patient.lastContactDate
            ? format(new Date(patient.lastContactDate), 'MMM d, yyyy')
            : '—'}
        </span>
      </td>
      <td className="px-4 py-3">
        {patient.alertStatus === 'critical' ? (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-danger-600 dark:text-danger-400">
            <AlertTriangle className="w-3 h-3" />
            Critical
          </span>
        ) : patient.alertStatus === 'warning' ? (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-warning-600 dark:text-warning-400">
            <AlertTriangle className="w-3 h-3" />
            Warning
          </span>
        ) : (
          <span className="text-xs text-secondary-600 dark:text-secondary-400">Stable</span>
        )}
      </td>
    </tr>
  )
}
