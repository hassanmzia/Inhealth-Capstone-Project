import { useState, useEffect, useCallback, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Activity,
  Heart,
  Thermometer,
  Wind,
  Droplets,
  User,
  AlertTriangle,
  Wifi,
  WifiOff,
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import api from '@/services/api'
import { cn } from '@/lib/utils'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

interface VitalSign {
  label: string
  value: string
  unit: string
  icon: React.ElementType
  color: string
  chartColor: string
  normalRange: string
  thresholdHigh: number
  thresholdLow: number
  status: 'normal' | 'warning' | 'critical'
  trend: { time: string; value: number }[]
}

interface Patient {
  id: string
  name: string
}

const STATUS_STYLES = {
  normal: 'border-secondary-500/30 bg-secondary-50/30 dark:bg-secondary-900/10',
  warning: 'border-warning-500/30 bg-warning-50/30 dark:bg-warning-900/10',
  critical: 'border-danger-500/30 bg-danger-50/30 dark:bg-danger-900/10 animate-pulse',
}

function useVitalsWebSocket(patientId: string | null) {
  const [vitals, setVitals] = useState<VitalSign[] | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback(() => {
    if (!patientId) return

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/vitals/${patientId}/`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => setConnected(false)
      ws.onerror = () => setConnected(false)
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.vitals) setVitals(data.vitals)
        } catch {
          /* ignore parse errors */
        }
      }
    } catch {
      setConnected(false)
    }
  }, [patientId])

  useEffect(() => {
    connect()
    return () => {
      wsRef.current?.close()
    }
  }, [connect])

  return { vitals, connected }
}

export default function VitalsPage() {
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null)

  const { data: patientsData } = useQuery({
    queryKey: ['vitals-patients'],
    queryFn: () => api.get('/patients/').then((r) => r.data),
    placeholderData: {
      results: [
        { id: 'p1', name: 'Maria Garcia' },
        { id: 'p2', name: 'James Wilson' },
        { id: 'p3', name: 'Susan Chen' },
        { id: 'p4', name: 'Robert Johnson' },
      ] as Patient[],
    },
  })

  const patients = patientsData?.results ?? []

  const { vitals: wsVitals, connected } = useVitalsWebSocket(selectedPatientId)

  // Placeholder vitals when no WebSocket data
  const placeholderVitals: VitalSign[] = [
    {
      label: 'Heart Rate', value: '72', unit: 'bpm', icon: Heart, color: 'text-danger-500',
      chartColor: '#e11d48', normalRange: '60-100 bpm', thresholdHigh: 100, thresholdLow: 60, status: 'normal',
      trend: [
        { time: '00:00', value: 68 }, { time: '04:00', value: 65 }, { time: '08:00', value: 74 },
        { time: '12:00', value: 78 }, { time: '16:00', value: 72 }, { time: '20:00', value: 70 },
        { time: 'Now', value: 72 },
      ],
    },
    {
      label: 'Blood Pressure', value: '128/82', unit: 'mmHg', icon: Activity, color: 'text-primary-500',
      chartColor: '#3b82f6', normalRange: '<140/90 mmHg', thresholdHigh: 140, thresholdLow: 90, status: 'normal',
      trend: [
        { time: '00:00', value: 122 }, { time: '04:00', value: 118 }, { time: '08:00', value: 130 },
        { time: '12:00', value: 135 }, { time: '16:00', value: 128 }, { time: '20:00', value: 126 },
        { time: 'Now', value: 128 },
      ],
    },
    {
      label: 'SpO2', value: '97', unit: '%', icon: Droplets, color: 'text-sky-500',
      chartColor: '#0ea5e9', normalRange: '95-100%', thresholdHigh: 100, thresholdLow: 95, status: 'normal',
      trend: [
        { time: '00:00', value: 98 }, { time: '04:00', value: 97 }, { time: '08:00', value: 96 },
        { time: '12:00', value: 97 }, { time: '16:00', value: 98 }, { time: '20:00', value: 97 },
        { time: 'Now', value: 97 },
      ],
    },
    {
      label: 'Temperature', value: '98.6', unit: '\u00B0F', icon: Thermometer, color: 'text-orange-500',
      chartColor: '#f97316', normalRange: '97.8-99.1\u00B0F', thresholdHigh: 100.4, thresholdLow: 97.0, status: 'normal',
      trend: [
        { time: '00:00', value: 98.2 }, { time: '04:00', value: 97.9 }, { time: '08:00', value: 98.4 },
        { time: '12:00', value: 98.8 }, { time: '16:00', value: 98.6 }, { time: '20:00', value: 98.5 },
        { time: 'Now', value: 98.6 },
      ],
    },
    {
      label: 'Respiratory Rate', value: '16', unit: 'br/min', icon: Wind, color: 'text-teal-500',
      chartColor: '#14b8a6', normalRange: '12-20 br/min', thresholdHigh: 20, thresholdLow: 12, status: 'normal',
      trend: [
        { time: '00:00', value: 14 }, { time: '04:00', value: 15 }, { time: '08:00', value: 16 },
        { time: '12:00', value: 18 }, { time: '16:00', value: 16 }, { time: '20:00', value: 15 },
        { time: 'Now', value: 16 },
      ],
    },
    {
      label: 'Blood Glucose', value: '112', unit: 'mg/dL', icon: Droplets, color: 'text-purple-500',
      chartColor: '#8b5cf6', normalRange: '70-140 mg/dL', thresholdHigh: 140, thresholdLow: 70, status: 'normal',
      trend: [
        { time: '00:00', value: 95 }, { time: '04:00', value: 88 }, { time: '08:00', value: 145 },
        { time: '12:00', value: 132 }, { time: '16:00', value: 118 }, { time: '20:00', value: 108 },
        { time: 'Now', value: 112 },
      ],
    },
  ]

  const vitals = wsVitals ?? placeholderVitals

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-7xl">
      <motion.div variants={ITEM} className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-500" />
            Real-Time Vitals Monitoring
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Live patient vital signs with threshold alerts
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={cn('flex items-center gap-1.5 text-xs font-medium', connected ? 'text-secondary-600 dark:text-secondary-400' : 'text-muted-foreground')}>
            {connected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {connected ? 'Live' : 'Offline'}
          </span>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <select
              value={selectedPatientId ?? ''}
              onChange={(e) => setSelectedPatientId(e.target.value || null)}
              className="pl-9 pr-4 py-2 rounded-lg border border-border bg-card text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-primary-400 appearance-none cursor-pointer"
            >
              <option value="">Select patient...</option>
              {patients.map((p: Patient) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        </div>
      </motion.div>

      {/* Vital sign cards */}
      <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {vitals.map((vital) => (
          <div
            key={vital.label}
            className={cn('clinical-card border', STATUS_STYLES[vital.status])}
          >
            <div className="flex items-center justify-between mb-2">
              <vital.icon className={cn('w-5 h-5', vital.color)} />
              {vital.status !== 'normal' && (
                <AlertTriangle className="w-4 h-4 text-warning-500" />
              )}
            </div>
            <p className="text-2xl font-bold font-mono text-foreground">{vital.value}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{vital.unit}</p>
            <p className="text-xs font-medium text-foreground mt-1">{vital.label}</p>
            <p className="text-[10px] text-muted-foreground">Normal: {vital.normalRange}</p>
          </div>
        ))}
      </motion.div>

      {/* Trend charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {vitals.map((vital) => (
          <motion.div key={vital.label} variants={ITEM} className="clinical-card">
            <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
              <vital.icon className={cn('w-4 h-4', vital.color)} />
              {vital.label} (24h Trend)
            </h2>
            <div style={{ height: 180 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={vital.trend} margin={{ top: 5, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.4} />
                  <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                  <Tooltip
                    formatter={(v: number) => [`${v} ${vital.unit}`, vital.label]}
                    contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                  />
                  <ReferenceLine y={vital.thresholdHigh} stroke="#e11d48" strokeDasharray="4 4" strokeOpacity={0.6} />
                  <ReferenceLine y={vital.thresholdLow} stroke="#f59e0b" strokeDasharray="4 4" strokeOpacity={0.6} />
                  <Line type="monotone" dataKey="value" stroke={vital.chartColor} strokeWidth={2.5} dot={{ r: 3, fill: vital.chartColor }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
