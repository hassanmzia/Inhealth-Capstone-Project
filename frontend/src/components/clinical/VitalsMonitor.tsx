import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Heart,
  Activity,
  Thermometer,
  Wind,
  Weight,
  TrendingUp,
  TrendingDown,
  Minus,
  HeartPulse,
} from 'lucide-react'
import type { VitalSign, VitalType } from '@/types/clinical'
import { VITAL_RANGES, ECG_RHYTHM_LABELS } from '@/types/clinical'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'

interface VitalsMonitorProps {
  vitals: VitalSign[]
  isRealtime?: boolean
  compact?: boolean
}

interface VitalDisplay {
  type: VitalType
  label: string
  icon: React.ElementType
  unit: string
  getValue: (vitals: VitalSign[]) => VitalSign | undefined
  format: (v: VitalSign) => string
}

const VITAL_DISPLAYS: VitalDisplay[] = [
  {
    type: 'heart_rate',
    label: 'Heart Rate',
    icon: Heart,
    unit: 'bpm',
    getValue: (vitals) => vitals.find((v) => v.type === 'heart_rate'),
    format: (v) => `${Math.round(v.value)}`,
  },
  {
    type: 'blood_pressure_systolic',
    label: 'Blood Pressure',
    icon: Activity,
    unit: 'mmHg',
    getValue: (vitals) => vitals.find((v) => v.type === 'blood_pressure_systolic'),
    format: (v) => `${Math.round(v.systolic ?? v.value)}/${Math.round(v.diastolic ?? 80)}`,
  },
  {
    type: 'spo2',
    label: 'SpO2',
    icon: Wind,
    unit: '%',
    getValue: (vitals) => vitals.find((v) => v.type === 'spo2'),
    format: (v) => `${v.value.toFixed(1)}`,
  },
  {
    type: 'temperature',
    label: 'Temp',
    icon: Thermometer,
    unit: '°C',
    getValue: (vitals) => vitals.find((v) => v.type === 'temperature'),
    format: (v) => `${v.value.toFixed(1)}`,
  },
  {
    type: 'respiratory_rate',
    label: 'Resp Rate',
    icon: Wind,
    unit: '/min',
    getValue: (vitals) => vitals.find((v) => v.type === 'respiratory_rate'),
    format: (v) => `${Math.round(v.value)}`,
  },
  {
    type: 'weight',
    label: 'Weight',
    icon: Weight,
    unit: 'kg',
    getValue: (vitals) => vitals.find((v) => v.type === 'weight'),
    format: (v) => `${v.value.toFixed(1)}`,
  },
  {
    type: 'ecg',
    label: 'ECG',
    icon: HeartPulse,
    unit: 'bpm',
    getValue: (vitals) => vitals.find((v) => v.type === 'ecg'),
    format: (v) => v.ecgRhythm ? ECG_RHYTHM_LABELS[v.ecgRhythm] ?? `${Math.round(v.value)}` : `${Math.round(v.value)}`,
  },
]

function getStatusStyles(status: string) {
  switch (status) {
    case 'critical':
      return {
        card: 'border-danger-300 dark:border-danger-700 bg-danger-50/50 dark:bg-danger-900/10',
        value: 'text-danger-600 dark:text-danger-400',
        pulse: 'animate-critical-pulse',
        badge: 'bg-danger-100 dark:bg-danger-900/30 text-danger-700 dark:text-danger-400',
      }
    case 'warning':
      return {
        card: 'border-warning-300 dark:border-warning-700 bg-warning-50/50 dark:bg-warning-900/10',
        value: 'text-warning-600 dark:text-warning-400',
        pulse: '',
        badge: 'bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-400',
      }
    default:
      return {
        card: 'border-border',
        value: 'text-foreground',
        pulse: '',
        badge: 'bg-secondary-100 dark:bg-secondary-900/30 text-secondary-700 dark:text-secondary-400',
      }
  }
}

function TrendIcon({ trend }: { trend?: 'up' | 'down' | 'stable' }) {
  if (!trend || trend === 'stable') return <Minus className="w-3.5 h-3.5 text-muted-foreground" />
  if (trend === 'up') return <TrendingUp className="w-3.5 h-3.5 text-warning-500" />
  return <TrendingDown className="w-3.5 h-3.5 text-secondary-500" />
}

// Sparkline using inline SVG
function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null

  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const w = 48
  const h = 20

  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w
    const y = h - ((v - min) / range) * h
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export default function VitalsMonitor({ vitals, isRealtime = false, compact = false }: VitalsMonitorProps) {
  const [updatedVitals, setUpdatedVitals] = useState<Set<string>>(new Set())

  // Flash animation on vital update
  useEffect(() => {
    const types = vitals.map((v) => v.type)
    setUpdatedVitals(new Set(types))
    const timer = setTimeout(() => setUpdatedVitals(new Set()), 1500)
    return () => clearTimeout(timer)
  }, [vitals])

  const latestVitals = VITAL_DISPLAYS.map((display) => ({
    ...display,
    vital: display.getValue(vitals),
  }))

  const lastUpdate = vitals[0]?.timestamp
    ? formatDistanceToNow(new Date(vitals[0].timestamp), { addSuffix: true })
    : null

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        {isRealtime && (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-xs text-secondary-600 dark:text-secondary-400">
              <span className="w-2 h-2 rounded-full bg-secondary-500 animate-vitals-pulse" />
              Live
            </span>
            {lastUpdate && (
              <span className="text-xs text-muted-foreground">Updated {lastUpdate}</span>
            )}
          </div>
        )}
      </div>

      {/* Vitals grid */}
      <div className={cn(
        'grid gap-3',
        compact
          ? 'grid-cols-3 sm:grid-cols-6'
          : 'grid-cols-2 sm:grid-cols-3 lg:grid-cols-6',
      )}>
        {latestVitals.map(({ type, label, icon: Icon, unit, vital, format }) => {
          if (!vital) return null

          const status = vital.status ?? 'normal'
          const styles = getStatusStyles(status)
          const isUpdated = updatedVitals.has(type)

          // Get historical values for sparkline
          const historicalValues = vitals
            .filter((v) => v.type === type)
            .slice(0, 12)
            .reverse()
            .map((v) => v.value)

          const sparkColor = status === 'critical' ? '#e11d48' : status === 'warning' ? '#d97706' : '#16a34a'

          return (
            <motion.div
              key={type}
              animate={isUpdated && isRealtime ? { scale: [1, 1.03, 1] } : {}}
              transition={{ duration: 0.3 }}
              className={cn(
                'p-3 rounded-xl border bg-card transition-colors',
                styles.card,
                isUpdated && isRealtime && 'ring-2 ring-primary-400 ring-opacity-50',
                styles.pulse && status === 'critical' && 'animate-critical-pulse',
              )}
            >
              {/* Icon + label */}
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-1.5">
                  <Icon className={cn('w-3.5 h-3.5', status === 'critical' ? 'text-danger-500' : status === 'warning' ? 'text-warning-500' : 'text-muted-foreground')} />
                  <span className="vital-label text-[10px]">{label}</span>
                </div>
                <TrendIcon trend={vital.trend} />
              </div>

              {/* Value */}
              <div className={cn('vital-value text-xl', styles.value)}>
                {format(vital)}
                <span className="text-xs font-normal text-muted-foreground ml-1">{unit}</span>
              </div>

              {/* Sparkline */}
              {!compact && historicalValues.length > 1 && (
                <div className="mt-2">
                  <Sparkline values={historicalValues} color={sparkColor} />
                </div>
              )}

              {/* Status badge */}
              {status !== 'normal' && (
                <div className={cn('mt-2 px-1.5 py-0.5 rounded text-[10px] font-semibold inline-block', styles.badge)}>
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </div>
              )}
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
