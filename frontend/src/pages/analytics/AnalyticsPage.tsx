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
  LineChart, Line, Legend, Cell,
} from 'recharts'
import api from '@/services/api'
import PopulationRiskPyramid from '@/components/charts/PopulationRiskPyramid'
import AgentActivityTimeline from '@/components/charts/AgentActivityTimeline'
import { useAgentStore } from '@/store/agentStore'
import type { AgentExecution } from '@/types/agent'
import { useMemo } from 'react'
import { subHours, subMinutes } from 'date-fns'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL ?? ''

export default function AnalyticsPage() {
  const executions = useAgentStore((state) => state.executions)
  const executionSlice = useMemo(() => {
    if (executions.length > 0) return executions.slice(0, 200)
    return DEMO_EXECUTIONS
  }, [executions])

  const { data: populationDataRaw } = useQuery({
    queryKey: ['population-metrics'],
    queryFn: () => api.get('/analytics/population/').then((r) => r.data),
  })

  const d = useMemo(() => {
    if (populationDataRaw && populationDataRaw.riskDistribution?.total > 0) return populationDataRaw
    return DEMO_POPULATION_DATA
  }, [populationDataRaw])

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
          { label: 'Total Patients', value: d?.riskDistribution?.total?.toLocaleString() ?? '—', icon: Users, color: 'text-primary-500' },
          { label: 'Avg Risk Score', value: '42%', icon: Activity, color: 'text-warning-500' },
          { label: 'Med Adherence', value: '85%', icon: TrendingUp, color: 'text-secondary-500' },
          { label: '30d Readmission', value: '8.2%', icon: BarChart3, color: 'text-danger-500' },
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
          <PopulationRiskPyramid
            data={d?.riskDistribution ?? { critical: 0, high: 0, medium: 0, low: 0, total: 0 }}
            orientation="vertical"
            height={220}
          />
        </motion.div>

        {/* Disease prevalence */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4">Disease Prevalence</h2>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d?.diseasePrevalence ?? []} layout="vertical" margin={{ left: 100, right: 40, top: 0, bottom: 0 }}>
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
        </motion.div>

        {/* Care gap rates */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4">Care Gap Closure Rates</h2>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d?.careGapRates ?? []} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
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
        </motion.div>

        {/* Medication adherence trend */}
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-4">Medication Adherence Trend</h2>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={d?.adherenceTrend ?? []} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
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
        </motion.div>

        {/* Quality measures */}
        <motion.div variants={ITEM} className="clinical-card lg:col-span-2">
          <h2 className="text-sm font-bold text-foreground mb-4">HEDIS Quality Measures</h2>
          <div className="space-y-3">
            {(d?.qualityMeasures ?? []).map((measure: { measure: string; rate: number; benchmark: number }) => (
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
                  {/* Benchmark line */}
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-foreground/30"
                    style={{ left: `${measure.benchmark}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Agent performance */}
        <motion.div variants={ITEM} className="clinical-card lg:col-span-2">
          <h2 className="text-sm font-bold text-foreground mb-4">Agent Activity (24h)</h2>
          <AgentActivityTimeline executions={executionSlice} height={300} />
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

// ─── Demo Data ────────────────────────────────────────────────────────────────

const _now = new Date()

const DEMO_EXECUTIONS: AgentExecution[] = [
  { id: 'demo-e1', agentId: 'vital_signs_agent', agentName: 'Vital Sign Monitor', tier: 'tier1_ingestion', status: 'completed', patientId: 'demo-p1', patientName: 'James Morrison', triggeredBy: 'system', triggeredAt: subMinutes(_now, 15).toISOString(), startedAt: subMinutes(_now, 15).toISOString(), completedAt: subMinutes(_now, 14).toISOString(), runtimeSeconds: 4.2 },
  { id: 'demo-e2', agentId: 'risk_stratification_agent', agentName: 'Risk Stratification', tier: 'tier2_analysis', status: 'completed', triggeredBy: 'scheduler', triggeredAt: subMinutes(_now, 45).toISOString(), startedAt: subMinutes(_now, 45).toISOString(), completedAt: subMinutes(_now, 43).toISOString(), runtimeSeconds: 12.8 },
  { id: 'demo-e3', agentId: 'care_gap_detection_agent', agentName: 'Care Gap Detector', tier: 'tier3_clinical', status: 'completed', patientId: 'demo-p5', patientName: 'William Jackson', triggeredBy: 'system', triggeredAt: subHours(_now, 1).toISOString(), startedAt: subHours(_now, 1).toISOString(), completedAt: subMinutes(subHours(_now, 1), -2).toISOString(), runtimeSeconds: 8.1 },
  { id: 'demo-e4', agentId: 'medication_adherence_agent', agentName: 'Medication Adherence', tier: 'tier3_clinical', status: 'completed', patientId: 'demo-p3', patientName: 'Robert Chen', triggeredBy: 'system', triggeredAt: subHours(_now, 2).toISOString(), startedAt: subHours(_now, 2).toISOString(), completedAt: subMinutes(subHours(_now, 2), -1).toISOString(), runtimeSeconds: 5.3 },
  { id: 'demo-e5', agentId: 'fhir_ingestion_agent', agentName: 'FHIR Data Ingestion', tier: 'tier1_ingestion', status: 'completed', triggeredBy: 'scheduler', triggeredAt: subHours(_now, 3).toISOString(), startedAt: subHours(_now, 3).toISOString(), completedAt: subMinutes(subHours(_now, 3), -5).toISOString(), runtimeSeconds: 31.4 },
  { id: 'demo-e6', agentId: 'notification_agent', agentName: 'Patient Outreach', tier: 'tier5_engagement', status: 'pending_hitl', patientId: 'demo-p2', patientName: 'Maria Gonzalez', triggeredBy: 'care_gap_detection_agent', triggeredAt: subHours(_now, 4).toISOString(), startedAt: subHours(_now, 4).toISOString(), runtimeSeconds: 2.1 },
  { id: 'demo-e7', agentId: 'ehr_sync_agent', agentName: 'EHR Sync', tier: 'tier1_ingestion', status: 'completed', triggeredBy: 'scheduler', triggeredAt: subHours(_now, 6).toISOString(), startedAt: subHours(_now, 6).toISOString(), completedAt: subMinutes(subHours(_now, 6), -3).toISOString(), runtimeSeconds: 18.7 },
  { id: 'demo-e8', agentId: 'predictive_analytics_agent', agentName: 'Readmission Predictor', tier: 'tier2_analysis', status: 'completed', patientId: 'demo-p1', patientName: 'James Morrison', triggeredBy: 'risk_stratification_agent', triggeredAt: subHours(_now, 8).toISOString(), startedAt: subHours(_now, 8).toISOString(), completedAt: subMinutes(subHours(_now, 8), -1).toISOString(), runtimeSeconds: 6.9 },
  { id: 'demo-e9', agentId: 'population_health_agent', agentName: 'HEDIS Quality Measure', tier: 'tier2_analysis', status: 'failed', triggeredBy: 'scheduler', triggeredAt: subHours(_now, 10).toISOString(), startedAt: subHours(_now, 10).toISOString(), completedAt: subMinutes(subHours(_now, 10), -1).toISOString(), runtimeSeconds: 3.2, error: 'Timeout fetching external measure definitions' },
  { id: 'demo-e10', agentId: 'vital_signs_agent', agentName: 'Vital Sign Monitor', tier: 'tier1_ingestion', status: 'running', patientId: 'demo-p4', patientName: 'Dorothy Williams', triggeredBy: 'system', triggeredAt: subMinutes(_now, 2).toISOString(), startedAt: subMinutes(_now, 2).toISOString() },
]

const DEMO_POPULATION_DATA = {
  riskDistribution: { critical: 47, high: 183, medium: 521, low: 533, total: 1284 },
  diseasePrevalence: [
    { condition: 'Type 2 Diabetes', count: 486, percentage: 37.8 },
    { condition: 'Hypertension', count: 641, percentage: 49.9 },
    { condition: 'Heart Failure', count: 127, percentage: 9.9 },
    { condition: 'CKD', count: 198, percentage: 15.4 },
    { condition: 'COPD', count: 89, percentage: 6.9 },
    { condition: 'AFib', count: 112, percentage: 8.7 },
  ],
  careGapRates: [
    { category: 'Preventive', openGaps: 312, closureRate: 68 },
    { category: 'Screening', openGaps: 184, closureRate: 72 },
    { category: 'Chronic Mgmt', openGaps: 247, closureRate: 61 },
    { category: 'Medication', openGaps: 89, closureRate: 81 },
    { category: 'Follow-up', openGaps: 156, closureRate: 74 },
  ],
  adherenceTrend: [
    { month: 'Sep', adherence: 76 },
    { month: 'Oct', adherence: 78 },
    { month: 'Nov', adherence: 74 },
    { month: 'Dec', adherence: 80 },
    { month: 'Jan', adherence: 82 },
    { month: 'Feb', adherence: 85 },
  ],
  qualityMeasures: [
    { measure: 'HbA1c Control (<8%)', rate: 68, benchmark: 72 },
    { measure: 'BP Control (<140/90)', rate: 71, benchmark: 68 },
    { measure: 'Statin Therapy', rate: 84, benchmark: 80 },
    { measure: 'Colorectal Screening', rate: 59, benchmark: 65 },
    { measure: 'Breast Cancer Screen', rate: 72, benchmark: 70 },
    { measure: 'Influenza Vaccine', rate: 81, benchmark: 75 },
  ],
}
