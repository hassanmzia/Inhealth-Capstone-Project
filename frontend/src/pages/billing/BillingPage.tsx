import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  DollarSign,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  Send,
  Filter,
  Timer,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell,
} from 'recharts'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

type ClaimStatus = 'draft' | 'submitted' | 'pending' | 'approved' | 'denied' | 'paid'

const STATUS_CONFIG: Record<ClaimStatus, { label: string; color: string; badge: string }> = {
  draft: { label: 'Draft', color: '#94a3b8', badge: 'bg-muted text-muted-foreground' },
  submitted: { label: 'Submitted', color: '#3b82f6', badge: 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400' },
  pending: { label: 'Pending', color: '#f59e0b', badge: 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400' },
  approved: { label: 'Approved', color: '#16a34a', badge: 'bg-secondary-100 dark:bg-secondary-900/30 text-secondary-700 dark:text-secondary-400' },
  denied: { label: 'Denied', color: '#e11d48', badge: 'bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-400' },
  paid: { label: 'Paid', color: '#8b5cf6', badge: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400' },
}

interface Claim {
  id: string
  patientName: string
  claimNumber: string
  status: ClaimStatus
  amount: number
  submittedDate: string
  payerName: string
  cptCodes: string[]
}

interface RpmEpisode {
  id: string
  patientName: string
  device: string
  totalMinutes: number
  targetMinutes: number
  billingCode: string
  period: string
}

export default function BillingPage() {
  const [statusFilter, setStatusFilter] = useState<ClaimStatus | 'all'>('all')

  const { data: claimsData } = useQuery({
    queryKey: ['billing-claims'],
    queryFn: () => api.get('/billing/claims/').then((r) => r.data),
    placeholderData: {
      summary: {
        totalClaims: 1247,
        pendingAmount: 284300,
        approvedAmount: 1892450,
        deniedAmount: 67200,
      },
      claims: [
        { id: '1', patientName: 'Maria Garcia', claimNumber: 'CLM-2024-4281', status: 'approved', amount: 1250, submittedDate: '2024-11-15', payerName: 'BlueCross', cptCodes: ['99214', '83036'] },
        { id: '2', patientName: 'James Wilson', claimNumber: 'CLM-2024-4282', status: 'pending', amount: 890, submittedDate: '2024-11-18', payerName: 'Aetna', cptCodes: ['99213'] },
        { id: '3', patientName: 'Susan Chen', claimNumber: 'CLM-2024-4283', status: 'denied', amount: 2100, submittedDate: '2024-11-10', payerName: 'UnitedHealth', cptCodes: ['99215', '93000'] },
        { id: '4', patientName: 'Robert Johnson', claimNumber: 'CLM-2024-4284', status: 'submitted', amount: 675, submittedDate: '2024-11-20', payerName: 'Cigna', cptCodes: ['99213'] },
        { id: '5', patientName: 'Emily Davis', claimNumber: 'CLM-2024-4285', status: 'paid', amount: 1480, submittedDate: '2024-11-05', payerName: 'BlueCross', cptCodes: ['99214', '80053'] },
        { id: '6', patientName: 'Michael Brown', claimNumber: 'CLM-2024-4286', status: 'draft', amount: 950, submittedDate: '2024-11-22', payerName: 'Aetna', cptCodes: ['99214'] },
      ] as Claim[],
      statusBreakdown: [
        { status: 'Draft', count: 42 },
        { status: 'Submitted', count: 156 },
        { status: 'Pending', count: 287 },
        { status: 'Approved', count: 534 },
        { status: 'Denied', count: 89 },
        { status: 'Paid', count: 139 },
      ],
    },
  })

  const { data: rpmData } = useQuery({
    queryKey: ['billing-rpm-episodes'],
    queryFn: () => api.get('/billing/rpm-episodes/').then((r) => r.data),
    placeholderData: {
      episodes: [
        { id: '1', patientName: 'Maria Garcia', device: 'BP Monitor', totalMinutes: 18, targetMinutes: 20, billingCode: '99458', period: 'Nov 2024' },
        { id: '2', patientName: 'James Wilson', device: 'Glucometer', totalMinutes: 22, targetMinutes: 20, billingCode: '99457', period: 'Nov 2024' },
        { id: '3', patientName: 'Susan Chen', device: 'Pulse Oximeter', totalMinutes: 12, targetMinutes: 20, billingCode: '99458', period: 'Nov 2024' },
        { id: '4', patientName: 'Robert Johnson', device: 'Weight Scale', totalMinutes: 8, targetMinutes: 20, billingCode: '99457', period: 'Nov 2024' },
      ] as RpmEpisode[],
    },
  })

  const d = claimsData
  const rpm = rpmData

  const filteredClaims = (d?.claims ?? []).filter(
    (c: Claim) => statusFilter === 'all' || c.status === statusFilter,
  )

  const STATUS_COLORS = ['#94a3b8', '#3b82f6', '#f59e0b', '#16a34a', '#e11d48', '#8b5cf6']

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-7xl">
      <motion.div variants={ITEM} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-primary-500" />
            Revenue Cycle Management
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Claims processing, billing analytics, and RPM episode tracking
          </p>
        </div>
      </motion.div>

      {/* KPI row */}
      <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Claims', value: d?.summary?.totalClaims?.toLocaleString() ?? '—', icon: FileText, color: 'text-primary-500' },
          { label: 'Pending Amount', value: `$${((d?.summary?.pendingAmount ?? 0) / 1000).toFixed(0)}k`, icon: Clock, color: 'text-warning-500' },
          { label: 'Approved Amount', value: `$${((d?.summary?.approvedAmount ?? 0) / 1000).toFixed(0)}k`, icon: CheckCircle2, color: 'text-secondary-500' },
          { label: 'Denied Amount', value: `$${((d?.summary?.deniedAmount ?? 0) / 1000).toFixed(0)}k`, icon: XCircle, color: 'text-danger-500' },
        ].map((kpi) => (
          <div key={kpi.label} className="clinical-card">
            <kpi.icon className={`w-5 h-5 mb-2 ${kpi.color}`} />
            <p className="text-2xl font-bold font-mono text-foreground">{kpi.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{kpi.label}</p>
          </div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Claims by status chart */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4 text-muted-foreground" />
            Claims by Status
          </h2>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d?.statusBreakdown ?? []} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" strokeOpacity={0.4} />
                <XAxis dataKey="status" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {(d?.statusBreakdown ?? []).map((_: unknown, index: number) => (
                    <Cell key={index} fill={STATUS_COLORS[index % STATUS_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* RPM episodes */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
            <Timer className="w-4 h-4 text-muted-foreground" />
            RPM Monitoring Minutes
          </h2>
          <div className="space-y-3">
            {(rpm?.episodes ?? []).map((ep: RpmEpisode) => {
              const pct = Math.min((ep.totalMinutes / ep.targetMinutes) * 100, 100)
              const met = ep.totalMinutes >= ep.targetMinutes
              return (
                <div key={ep.id}>
                  <div className="flex items-center justify-between mb-1 text-xs">
                    <span className="font-medium text-foreground">{ep.patientName}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-muted-foreground">{ep.device}</span>
                      <span className={cn('font-mono font-bold', met ? 'text-secondary-600 dark:text-secondary-400' : 'text-warning-600 dark:text-warning-400')}>
                        {ep.totalMinutes}/{ep.targetMinutes} min
                      </span>
                    </div>
                  </div>
                  <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn('h-full rounded-full', met ? 'bg-secondary-500' : 'bg-warning-500')}
                      style={{ width: `${pct}%` }}
                    />
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-foreground/30"
                      style={{ left: '100%' }}
                    />
                  </div>
                  <div className="flex items-center justify-between mt-0.5 text-[10px] text-muted-foreground">
                    <span>{ep.billingCode}</span>
                    <span>{ep.period}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </motion.div>
      </div>

      {/* Claims table */}
      <motion.div variants={ITEM} className="clinical-card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Send className="w-4 h-4 text-muted-foreground" />
            Claims
          </h2>
          <div className="flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-muted-foreground mr-1" />
            {(['all', 'draft', 'submitted', 'pending', 'approved', 'denied', 'paid'] as const).map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={cn(
                  'px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors',
                  statusFilter === s
                    ? 'bg-primary-600 text-white'
                    : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground',
                )}
              >
                {s === 'all' ? 'All' : STATUS_CONFIG[s].label}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="pb-2 text-xs font-medium text-muted-foreground">Claim #</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground">Patient</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground">Payer</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground">CPT Codes</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground">Amount</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground">Date</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredClaims.map((claim: Claim) => (
                <tr key={claim.id} className="border-b border-border/50 hover:bg-accent/50 transition-colors">
                  <td className="py-2.5 font-mono text-xs text-foreground">{claim.claimNumber}</td>
                  <td className="py-2.5 font-medium text-foreground">{claim.patientName}</td>
                  <td className="py-2.5 text-muted-foreground">{claim.payerName}</td>
                  <td className="py-2.5">
                    <div className="flex gap-1">
                      {claim.cptCodes.map((code) => (
                        <span key={code} className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono text-muted-foreground">
                          {code}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2.5 font-mono font-bold text-foreground">${claim.amount.toLocaleString()}</td>
                  <td className="py-2.5 text-muted-foreground text-xs">{claim.submittedDate}</td>
                  <td className="py-2.5">
                    <span className={cn('text-[10px] font-bold px-1.5 py-0.5 rounded', STATUS_CONFIG[claim.status].badge)}>
                      {STATUS_CONFIG[claim.status].label}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  )
}
