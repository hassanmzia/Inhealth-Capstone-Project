import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  BarChart3,
  TrendingUp,
  Users,
  Activity,
  ExternalLink,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from 'recharts'
import api from '@/services/api'
import PopulationRiskPyramid from '@/components/charts/PopulationRiskPyramid'
import AgentActivityTimeline from '@/components/charts/AgentActivityTimeline'
import { useAgentStore } from '@/store/agentStore'
import { useMemo } from 'react'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL ?? ''

export default function AnalyticsPage() {
  const executions = useAgentStore((state) => state.executions)
  const executionSlice = useMemo(() => executions.slice(0, 200), [executions])

  const { data: populationData } = useQuery({
    queryKey: ['population-metrics'],
    queryFn: () => api.get('/analytics/population/').then((r) => r.data),
  })

  const { data: patientList } = useQuery({
    queryKey: ['patients-list'],
    queryFn: () => api.get('/patients/').then((r) => r.data),
  })

  const patientCount = useMemo(() => {
    if (Array.isArray(patientList)) return patientList.length
    if (patientList?.results) return patientList.results.length
    if (patientList?.count != null) return patientList.count
    return 0
  }, [patientList])

  const patients = useMemo(() => {
    const list = Array.isArray(patientList) ? patientList : patientList?.results ?? []
    return list as Array<{ riskScore?: { score: number; level: string }; activeConditions?: Array<{ display: string }> }>
  }, [patientList])

  // Build risk distribution from actual patients
  const riskDistribution = useMemo(() => {
    if (populationData?.riskDistribution?.total > 0) return populationData.riskDistribution
    const dist = { critical: 0, high: 0, medium: 0, low: 0, total: patientCount }
    for (const p of patients) {
      const level = p.riskScore?.level?.toLowerCase()
      if (level === 'critical') dist.critical++
      else if (level === 'high') dist.high++
      else if (level === 'medium') dist.medium++
      else dist.low++
    }
    return dist
  }, [populationData, patients, patientCount])

  // Build disease prevalence from actual patients
  const diseasePrevalence = useMemo(() => {
    if (populationData?.diseasePrevalence?.length > 0) return populationData.diseasePrevalence
    const counts: Record<string, number> = {}
    for (const p of patients) {
      for (const c of p.activeConditions ?? []) {
        counts[c.display] = (counts[c.display] ?? 0) + 1
      }
    }
    return Object.entries(counts)
      .map(([condition, count]) => ({ condition, count, percentage: patientCount > 0 ? Math.round((count / patientCount) * 1000) / 10 : 0 }))
      .sort((a, b) => b.count - a.count)
  }, [populationData, patients, patientCount])

  const d = populationData

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-7xl">
      <motion.div variants={ITEM} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary-500" />
            Population Health Analytics
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Real-time insights across your patient population
          </p>
        </div>
        {GRAFANA_URL && (
          <a
            href={GRAFANA_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2 border border-border rounded-lg text-sm font-medium text-foreground hover:bg-accent"
          >
            <ExternalLink className="w-4 h-4" />
            Grafana Dashboard
          </a>
        )}
      </motion.div>

      {/* KPI row */}
      <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { label: 'Total Patients', value: patientCount > 0 ? patientCount.toLocaleString() : '—', icon: Users, color: 'text-primary-500' },
          { label: 'Avg Risk Score', value: d?.avgRiskScore ?? '—', icon: Activity, color: 'text-warning-500' },
          { label: 'Med Adherence', value: d?.medAdherence ?? '—', icon: TrendingUp, color: 'text-secondary-500' },
          { label: '30d Readmission', value: d?.readmissionRate ?? '—', icon: BarChart3, color: 'text-danger-500' },
        ].map((kpi) => (
          <div key={kpi.label} className="clinical-card">
            <kpi.icon className={`w-5 h-5 mb-2 ${kpi.color}`} />
            <p className="text-2xl font-bold font-mono text-foreground">{kpi.value}</p>
            <p className="text-xs text-muted-foreground mt-1">{kpi.label}</p>
          </div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk distribution */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-muted-foreground" />
            Population Risk Distribution
          </h2>
          {riskDistribution.total > 0 ? (
            <PopulationRiskPyramid
              data={riskDistribution}
              orientation="vertical"
              height={220}
            />
          ) : (
            <p className="text-sm text-muted-foreground text-center py-10">No patient data available</p>
          )}
        </motion.div>

        {/* Disease prevalence */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4">Disease Prevalence</h2>
          {diseasePrevalence.length > 0 ? (
            <div style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={diseasePrevalence} layout="vertical" margin={{ left: 100, right: 40, top: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" strokeOpacity={0.4} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                  <YAxis type="category" dataKey="condition" tick={{ fontSize: 10, fill: 'hsl(var(--foreground))' }} tickLine={false} axisLine={false} width={96} />
                  <Tooltip
                    formatter={(v: number) => [`${v} patients`, 'Count']}
                    contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]} fill="#1d6fdb" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-10">No patient data available</p>
          )}
        </motion.div>

        {/* Care gap rates */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4">Care Gap Closure Rates</h2>
          {(d?.careGapRates ?? []).length > 0 ? (
            <div style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={d.careGapRates} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" strokeOpacity={0.4} />
                  <XAxis dataKey="category" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="closureRate" name="Closure Rate %" fill="#16a34a" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="openGaps" name="Open Gaps" fill="#e11d48" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-10">No care gap data available</p>
          )}
        </motion.div>

        {/* Medication adherence trend */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4">Medication Adherence Trend</h2>
          {(d?.adherenceTrend ?? []).length > 0 ? (
            <div style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={d.adherenceTrend} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.4} />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                  <YAxis domain={[60, 100]} tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                  <Tooltip
                    formatter={(v: number) => [`${v}%`, 'Adherence']}
                    contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                  />
                  <Line type="monotone" dataKey="adherence" stroke="#16a34a" strokeWidth={2.5} dot={{ r: 4, fill: '#16a34a' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-10">No adherence data available</p>
          )}
        </motion.div>

        {/* Quality measures */}
        <motion.div variants={ITEM} className="clinical-card lg:col-span-2">
          <h2 className="text-sm font-bold text-foreground mb-4">HEDIS Quality Measures</h2>
          {(d?.qualityMeasures ?? []).length > 0 ? (
            <div className="space-y-3">
              {d.qualityMeasures.map((measure: { measure: string; rate: number; benchmark: number }) => (
                <div key={measure.measure}>
                  <div className="flex items-center justify-between mb-1 text-xs">
                    <span className="font-medium text-foreground">{measure.measure}</span>
                    <div className="flex items-center gap-3">
                      <span className={`font-mono font-bold ${measure.rate >= measure.benchmark ? 'text-secondary-600 dark:text-secondary-400' : 'text-warning-600 dark:text-warning-400'}`}>
                        {measure.rate}%
                      </span>
                      <span className="text-muted-foreground">Benchmark: {measure.benchmark}%</span>
                    </div>
                  </div>
                  <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${measure.rate >= measure.benchmark ? 'bg-secondary-500' : 'bg-warning-500'}`}
                      style={{ width: `${measure.rate}%` }}
                    />
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-foreground/30"
                      style={{ left: `${measure.benchmark}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-10">No quality measure data available</p>
          )}
        </motion.div>

        {/* Agent performance */}
        <motion.div variants={ITEM} className="clinical-card lg:col-span-2">
          <h2 className="text-sm font-bold text-foreground mb-4">Agent Activity (24h)</h2>
          {executionSlice.length > 0 ? (
            <AgentActivityTimeline executions={executionSlice} height={300} />
          ) : (
            <p className="text-sm text-muted-foreground text-center py-10">No agent activity recorded yet</p>
          )}
        </motion.div>
      </div>

      {/* Grafana embed */}
      {GRAFANA_URL && (
        <motion.div variants={ITEM} className="clinical-card p-0 overflow-hidden">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h2 className="text-sm font-bold text-foreground">Live Operations Dashboard</h2>
            <a href={GRAFANA_URL} target="_blank" rel="noopener noreferrer" className="text-xs text-primary-600 flex items-center gap-1 hover:underline">
              Open in Grafana <ExternalLink className="w-3 h-3" />
            </a>
          </div>
          <iframe
            src={GRAFANA_URL}
            className="w-full border-0"
            style={{ height: 480 }}
            title="Grafana Dashboard"
          />
        </motion.div>
      )}
    </motion.div>
  )
}
