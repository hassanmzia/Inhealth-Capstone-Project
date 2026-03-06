import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Scale,
  Users,
  BarChart3,
  AlertTriangle,
  Info,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, Cell,
} from 'recharts'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

type DemographicDimension = 'age' | 'sex' | 'diagnosis'

const DIMENSION_OPTIONS: { value: DemographicDimension; label: string }[] = [
  { value: 'age', label: 'Age Groups' },
  { value: 'sex', label: 'Sex' },
  { value: 'diagnosis', label: 'Diagnosis Category' },
]

const SUBGROUP_COLORS = ['#3b82f6', '#16a34a', '#f59e0b', '#e11d48', '#8b5cf6', '#14b8a6']

interface SubgroupMetric {
  subgroup: string
  accuracy: number
  sensitivity: number
  specificity: number
  ppv: number
  count: number
}

interface DisparityMetric {
  name: string
  value: number
  threshold: number
  status: 'pass' | 'warning' | 'fail'
  description: string
}

interface RiskDistribution {
  subgroup: string
  low: number
  medium: number
  high: number
  critical: number
}

export default function FairnessAnalysisPage() {
  const [dimension, setDimension] = useState<DemographicDimension>('age')

  const { data: fairnessData } = useQuery({
    queryKey: ['fairness-analysis', dimension],
    queryFn: () => api.get(`/analytics/fairness/?dimension=${dimension}`).then((r) => r.data),
    placeholderData: {
      subgroupMetrics: dimension === 'age' ? [
        { subgroup: '18-34', accuracy: 0.91, sensitivity: 0.88, specificity: 0.93, ppv: 0.85, count: 187 },
        { subgroup: '35-49', accuracy: 0.89, sensitivity: 0.86, specificity: 0.91, ppv: 0.83, count: 312 },
        { subgroup: '50-64', accuracy: 0.92, sensitivity: 0.90, specificity: 0.93, ppv: 0.88, count: 428 },
        { subgroup: '65-74', accuracy: 0.87, sensitivity: 0.84, specificity: 0.89, ppv: 0.81, count: 246 },
        { subgroup: '75+', accuracy: 0.83, sensitivity: 0.79, specificity: 0.86, ppv: 0.77, count: 111 },
      ] : dimension === 'sex' ? [
        { subgroup: 'Male', accuracy: 0.90, sensitivity: 0.87, specificity: 0.92, ppv: 0.85, count: 612 },
        { subgroup: 'Female', accuracy: 0.89, sensitivity: 0.86, specificity: 0.91, ppv: 0.84, count: 672 },
      ] : [
        { subgroup: 'Diabetes', accuracy: 0.91, sensitivity: 0.89, specificity: 0.92, ppv: 0.87, count: 486 },
        { subgroup: 'Hypertension', accuracy: 0.88, sensitivity: 0.85, specificity: 0.90, ppv: 0.82, count: 641 },
        { subgroup: 'Heart Failure', accuracy: 0.86, sensitivity: 0.83, specificity: 0.88, ppv: 0.80, count: 127 },
        { subgroup: 'CKD', accuracy: 0.84, sensitivity: 0.80, specificity: 0.87, ppv: 0.78, count: 198 },
        { subgroup: 'COPD', accuracy: 0.87, sensitivity: 0.84, specificity: 0.89, ppv: 0.81, count: 89 },
      ] as SubgroupMetric[],
      disparityMetrics: [
        { name: 'Statistical Parity Difference', value: 0.04, threshold: 0.10, status: 'pass', description: 'Difference in positive prediction rates across subgroups' },
        { name: 'Equalized Odds Ratio', value: 0.92, threshold: 0.80, status: 'pass', description: 'Ratio of true positive rates across subgroups' },
        { name: 'Predictive Parity Difference', value: 0.07, threshold: 0.10, status: 'warning', description: 'Difference in PPV across subgroups' },
        { name: 'Calibration Difference', value: 0.03, threshold: 0.05, status: 'pass', description: 'Max difference in calibration slope across subgroups' },
      ] as DisparityMetric[],
      riskDistributions: dimension === 'age' ? [
        { subgroup: '18-34', low: 45, medium: 30, high: 18, critical: 7 },
        { subgroup: '35-49', low: 35, medium: 32, high: 22, critical: 11 },
        { subgroup: '50-64', low: 25, medium: 28, high: 30, critical: 17 },
        { subgroup: '65-74', low: 18, medium: 24, high: 34, critical: 24 },
        { subgroup: '75+', low: 12, medium: 20, high: 36, critical: 32 },
      ] : dimension === 'sex' ? [
        { subgroup: 'Male', low: 28, medium: 30, high: 26, critical: 16 },
        { subgroup: 'Female', low: 30, medium: 29, high: 25, critical: 16 },
      ] : [
        { subgroup: 'Diabetes', low: 22, medium: 28, high: 32, critical: 18 },
        { subgroup: 'Hypertension', low: 30, medium: 30, high: 26, critical: 14 },
        { subgroup: 'Heart Failure', low: 10, medium: 20, high: 38, critical: 32 },
        { subgroup: 'CKD', low: 15, medium: 22, high: 35, critical: 28 },
        { subgroup: 'COPD', low: 25, medium: 28, high: 30, critical: 17 },
      ] as RiskDistribution[],
    },
  })

  const d = fairnessData

  const performanceChartData = (d?.subgroupMetrics ?? []).map((m: SubgroupMetric) => ({
    subgroup: m.subgroup,
    Accuracy: +(m.accuracy * 100).toFixed(1),
    Sensitivity: +(m.sensitivity * 100).toFixed(1),
    Specificity: +(m.specificity * 100).toFixed(1),
    PPV: +(m.ppv * 100).toFixed(1),
  }))

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-7xl">
      <motion.div variants={ITEM} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Scale className="w-5 h-5 text-primary-500" />
            AI Fairness Analysis
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Model performance and bias evaluation across demographic subgroups
          </p>
        </div>
        <div className="flex items-center gap-1">
          {DIMENSION_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setDimension(opt.value)}
              className={cn(
                'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                dimension === opt.value
                  ? 'bg-primary-600 text-white'
                  : 'bg-muted text-muted-foreground hover:bg-accent hover:text-foreground',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </motion.div>

      {/* KPI row */}
      <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {(d?.disparityMetrics ?? []).map((metric: DisparityMetric) => (
          <div key={metric.name} className="clinical-card">
            <div className="flex items-center gap-2 mb-2">
              {metric.status === 'pass' ? (
                <Scale className="w-4 h-4 text-secondary-500" />
              ) : metric.status === 'warning' ? (
                <AlertTriangle className="w-4 h-4 text-warning-500" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-danger-500" />
              )}
              <span className={cn(
                'text-[10px] font-bold px-1.5 py-0.5 rounded',
                metric.status === 'pass'
                  ? 'bg-secondary-100 dark:bg-secondary-900/30 text-secondary-700 dark:text-secondary-400'
                  : metric.status === 'warning'
                  ? 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400'
                  : 'bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-400',
              )}>
                {metric.status.toUpperCase()}
              </span>
            </div>
            <p className="text-2xl font-bold font-mono text-foreground">{metric.value.toFixed(2)}</p>
            <p className="text-xs font-medium text-foreground mt-1">{metric.name}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">Threshold: {metric.threshold}</p>
          </div>
        ))}
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Performance comparison chart */}
        <motion.div variants={ITEM} className="clinical-card lg:col-span-2">
          <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-muted-foreground" />
            Model Performance by Subgroup
          </h2>
          <div style={{ height: 280 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={performanceChartData} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" strokeOpacity={0.4} />
                <XAxis dataKey="subgroup" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                <YAxis domain={[60, 100]} tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                <Tooltip
                  formatter={(v: number) => [`${v}%`]}
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="Accuracy" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Sensitivity" fill="#16a34a" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Specificity" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="PPV" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Risk score distribution */}
        <motion.div variants={ITEM} className="clinical-card lg:col-span-2">
          <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
            <Users className="w-4 h-4 text-muted-foreground" />
            Risk Score Distribution by {DIMENSION_OPTIONS.find((o) => o.value === dimension)?.label}
          </h2>
          <div style={{ height: 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d?.riskDistributions ?? []} margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" strokeOpacity={0.4} />
                <XAxis dataKey="subgroup" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                <Tooltip
                  formatter={(v: number) => [`${v}%`]}
                  contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="low" name="Low" stackId="risk" fill="#16a34a" />
                <Bar dataKey="medium" name="Medium" stackId="risk" fill="#f59e0b" />
                <Bar dataKey="high" name="High" stackId="risk" fill="#ea580c" />
                <Bar dataKey="critical" name="Critical" stackId="risk" fill="#e11d48" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Subgroup detail table */}
      <motion.div variants={ITEM} className="clinical-card">
        <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
          <Info className="w-4 h-4 text-muted-foreground" />
          Detailed Subgroup Metrics
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="pb-2 text-xs font-medium text-muted-foreground">Subgroup</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground text-right">N</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground text-right">Accuracy</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground text-right">Sensitivity</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground text-right">Specificity</th>
                <th className="pb-2 text-xs font-medium text-muted-foreground text-right">PPV</th>
              </tr>
            </thead>
            <tbody>
              {(d?.subgroupMetrics ?? []).map((m: SubgroupMetric, i: number) => (
                <tr key={m.subgroup} className="border-b border-border/50 hover:bg-accent/50 transition-colors">
                  <td className="py-2.5">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: SUBGROUP_COLORS[i % SUBGROUP_COLORS.length] }} />
                      <span className="font-medium text-foreground">{m.subgroup}</span>
                    </div>
                  </td>
                  <td className="py-2.5 text-right font-mono text-muted-foreground">{m.count.toLocaleString()}</td>
                  <td className="py-2.5 text-right font-mono font-bold text-foreground">{(m.accuracy * 100).toFixed(1)}%</td>
                  <td className="py-2.5 text-right font-mono font-bold text-foreground">{(m.sensitivity * 100).toFixed(1)}%</td>
                  <td className="py-2.5 text-right font-mono font-bold text-foreground">{(m.specificity * 100).toFixed(1)}%</td>
                  <td className="py-2.5 text-right font-mono font-bold text-foreground">{(m.ppv * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Disparity descriptions */}
        <div className="mt-4 pt-4 border-t border-border space-y-2">
          {(d?.disparityMetrics ?? []).map((metric: DisparityMetric) => (
            <div key={metric.name} className="flex items-start gap-2 text-xs">
              <Info className="w-3 h-3 text-muted-foreground mt-0.5 flex-shrink-0" />
              <span className="text-muted-foreground">
                <span className="font-medium text-foreground">{metric.name}:</span> {metric.description}
              </span>
            </div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  )
}
