import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Activity,
  Heart,
  HeartPulse,
  Thermometer,
  Wind,
  Droplets,
  User,
  AlertTriangle,
  Wifi,
  WifiOff,
  Radio,
  Clock,
  RefreshCw,
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import api from '@/services/api'
import * as fhirService from '@/services/fhir'
import { cn } from '@/lib/utils'
import { useSimulatorStore } from '@/store/simulatorStore'
import EcgWaveform from '@/components/charts/EcgWaveform'
import type { EcgRhythm } from '@/types/clinical'
import type { FHIRObservation } from '@/types/fhir'

const CONTAINER = { hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.08 } } }
const ITEM = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

// ─── LOINC code to display mapping ──────────────────────────────────────────

interface VitalDef {
  code: string
  label: string
  unit: string
  icon: React.ElementType
  color: string
  chartColor: string
  normalLow: number
  normalHigh: number
  normalRange: string
}

const VITAL_DEFS: VitalDef[] = [
  { code: '8867-4', label: 'Heart Rate', unit: 'bpm', icon: Heart, color: 'text-danger-500', chartColor: '#e11d48', normalLow: 60, normalHigh: 100, normalRange: '60-100 bpm' },
  { code: '8480-6', label: 'Systolic BP', unit: 'mmHg', icon: Activity, color: 'text-primary-500', chartColor: '#3b82f6', normalLow: 90, normalHigh: 140, normalRange: '90-140 mmHg' },
  { code: '8462-4', label: 'Diastolic BP', unit: 'mmHg', icon: Activity, color: 'text-indigo-500', chartColor: '#6366f1', normalLow: 60, normalHigh: 90, normalRange: '60-90 mmHg' },
  { code: '59408-5', label: 'SpO2', unit: '%', icon: Droplets, color: 'text-sky-500', chartColor: '#0ea5e9', normalLow: 95, normalHigh: 100, normalRange: '95-100%' },
  { code: '8310-5', label: 'Temperature', unit: '°F', icon: Thermometer, color: 'text-orange-500', chartColor: '#f97316', normalLow: 97.8, normalHigh: 99.1, normalRange: '97.8-99.1°F' },
  { code: '9279-1', label: 'Resp. Rate', unit: 'br/min', icon: Wind, color: 'text-teal-500', chartColor: '#14b8a6', normalLow: 12, normalHigh: 20, normalRange: '12-20 br/min' },
  { code: '2339-0', label: 'Blood Glucose', unit: 'mg/dL', icon: Droplets, color: 'text-purple-500', chartColor: '#8b5cf6', normalLow: 70, normalHigh: 140, normalRange: '70-140 mg/dL' },
]

const ECG_LOINC = '8601-7'

// ─── Helpers ────────────────────────────────────────────────────────────────

function getObsValue(obs: FHIRObservation): number | null {
  if (obs.valueQuantity?.value != null) return obs.valueQuantity.value
  if ((obs as Record<string, unknown>).value_quantity != null) return (obs as Record<string, unknown>).value_quantity as number
  return null
}

function getObsTime(obs: FHIRObservation): string {
  const dt = obs.effectiveDateTime ?? (obs as Record<string, unknown>).effective_datetime as string | undefined
  if (!dt) return ''
  try {
    return new Date(dt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return dt.slice(11, 16)
  }
}

function getObsInterpretation(obs: FHIRObservation): string {
  if (obs.interpretation?.[0]?.coding?.[0]?.code) return obs.interpretation[0].coding[0].code
  if ((obs as Record<string, unknown>).interpretation) return (obs as Record<string, unknown>).interpretation as string
  return 'N'
}

function vitalStatus(value: number, def: VitalDef): 'normal' | 'warning' | 'critical' {
  if (value >= def.normalHigh * 1.2 || value <= def.normalLow * 0.8) return 'critical'
  if (value > def.normalHigh || value < def.normalLow) return 'warning'
  return 'normal'
}

const STATUS_STYLES = {
  normal: 'border-secondary-500/30 bg-secondary-50/30 dark:bg-secondary-900/10',
  warning: 'border-warning-500/30 bg-warning-50/30 dark:bg-warning-900/10',
  critical: 'border-danger-500/30 bg-danger-50/30 dark:bg-danger-900/10 animate-pulse',
}

interface Patient {
  id: string
  name: string
}

// ─── WebSocket hook ─────────────────────────────────────────────────────────

function useVitalsWebSocket(patientId: string | null) {
  const [vitals, setVitals] = useState<Record<string, unknown>[] | null>(null)
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

// ─── Component ──────────────────────────────────────────────────────────────

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

  const { connected } = useVitalsWebSocket(selectedPatientId)
  const bgStore = useSimulatorStore()

  // ─── Fetch historical observations from FHIR API ─────────────────────────
  const { data: observationsData, isLoading: obsLoading, refetch: refetchObs } = useQuery({
    queryKey: ['vitals-observations', selectedPatientId],
    queryFn: async () => {
      if (!selectedPatientId) return null
      // Fetch all vital-sign observations for this patient (last 24h)
      const since = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
      const result = await fhirService.getObservations(selectedPatientId, {
        date: `ge${since}`,
        _count: 500,
        _sort: '-date',
      })
      return result
    },
    enabled: !!selectedPatientId,
    refetchInterval: 10_000, // poll every 10s for new readings
  })

  // Group observations by LOINC code
  const { vitalGroups, ecgObs } = useMemo(() => {
    const entries = observationsData?.entry ?? []
    const groups: Record<string, { values: { time: string; value: number }[]; latest: number | null; latestStatus: 'normal' | 'warning' | 'critical' }> = {}

    for (const def of VITAL_DEFS) {
      groups[def.code] = { values: [], latest: null, latestStatus: 'normal' }
    }

    const ecgList: FHIRObservation[] = []

    for (const entry of entries) {
      const obs = entry.resource as FHIRObservation
      const code = obs.code?.coding?.[0]?.code ?? (obs as Record<string, unknown>).code as string | undefined
      if (!code) continue

      const value = getObsValue(obs)
      if (value == null) continue

      if (code === ECG_LOINC) {
        ecgList.push(obs)
        continue
      }

      if (groups[code]) {
        groups[code].values.push({ time: getObsTime(obs), value })
        if (groups[code].latest === null) {
          groups[code].latest = value
          const def = VITAL_DEFS.find((d) => d.code === code)!
          groups[code].latestStatus = vitalStatus(value, def)
        }
      }
    }

    // Reverse to chronological order for charts
    for (const g of Object.values(groups)) {
      g.values.reverse()
    }

    return { vitalGroups: groups, ecgObs: ecgList }
  }, [observationsData])

  // Latest ECG interpretation/rhythm
  const latestEcgRhythm = useMemo<EcgRhythm>(() => {
    if (ecgObs.length === 0) return 'normal_sinus'
    const interp = getObsInterpretation(ecgObs[0])
    // Map interpretation codes to rhythm names
    const map: Record<string, EcgRhythm> = {
      NSR: 'normal_sinus',
      SINU: 'sinus_bradycardia',
      AFIB: 'atrial_fibrillation',
      AFLU: 'atrial_flutter',
      VTAC: 'ventricular_tachycardia',
      VFIB: 'ventricular_fibrillation',
    }
    return map[interp] ?? 'normal_sinus'
  }, [ecgObs])

  const latestEcgHR = ecgObs.length > 0 ? getObsValue(ecgObs[0]) : null
  const hasData = Object.values(vitalGroups).some((g) => g.values.length > 0)

  return (
    <motion.div variants={CONTAINER} initial="hidden" animate="show" className="space-y-6 max-w-7xl">
      {/* Header */}
      <motion.div variants={ITEM} className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-foreground flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-500" />
            Patient Vitals
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Live monitoring + historical observations (24h)
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Background simulator indicator */}
          {bgStore.isRunning && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-secondary-600 dark:text-secondary-400 animate-pulse">
              <Radio className="w-3.5 h-3.5" /> Simulator active
            </span>
          )}

          <span className={cn('flex items-center gap-1.5 text-xs font-medium', connected ? 'text-secondary-600 dark:text-secondary-400' : 'text-muted-foreground')}>
            {connected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
            {connected ? 'Live' : 'Offline'}
          </span>

          <button
            onClick={() => refetchObs()}
            className="p-1.5 rounded-lg border border-border bg-card text-muted-foreground hover:text-foreground transition-colors"
            title="Refresh observations"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', obsLoading && 'animate-spin')} />
          </button>

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

      {/* No patient selected */}
      {!selectedPatientId && (
        <motion.div variants={ITEM} className="clinical-card text-center py-12">
          <User className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">Select a patient to view vital signs</p>
        </motion.div>
      )}

      {/* Loading */}
      {selectedPatientId && obsLoading && (
        <motion.div variants={ITEM} className="clinical-card text-center py-8">
          <RefreshCw className="w-6 h-6 text-primary-500 mx-auto mb-2 animate-spin" />
          <p className="text-sm text-muted-foreground">Loading observations...</p>
        </motion.div>
      )}

      {/* No data yet */}
      {selectedPatientId && !obsLoading && !hasData && (
        <motion.div variants={ITEM} className="clinical-card text-center py-12">
          <Clock className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground mb-1">No vital sign data in the last 24 hours</p>
          <p className="text-xs text-muted-foreground">
            Start the simulator with <strong>&quot;Keep alive&quot;</strong> enabled, then navigate here to see data populate.
          </p>
        </motion.div>
      )}

      {/* Vital sign summary cards */}
      {hasData && (
        <motion.div variants={ITEM} className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-4">
          {VITAL_DEFS.map((def) => {
            const group = vitalGroups[def.code]
            const latestVal = group?.latest
            const status = group?.latestStatus ?? 'normal'
            return (
              <div key={def.code} className={cn('clinical-card border', STATUS_STYLES[status])}>
                <div className="flex items-center justify-between mb-2">
                  <def.icon className={cn('w-5 h-5', def.color)} />
                  {status !== 'normal' && <AlertTriangle className="w-4 h-4 text-warning-500" />}
                </div>
                <p className="text-2xl font-bold font-mono text-foreground">
                  {latestVal != null ? (def.code === '8310-5' ? latestVal.toFixed(1) : Math.round(latestVal)) : '—'}
                </p>
                <p className="text-[10px] text-muted-foreground mt-0.5">{def.unit}</p>
                <p className="text-xs font-medium text-foreground mt-1">{def.label}</p>
                <p className="text-[10px] text-muted-foreground">Normal: {def.normalRange}</p>
                {group && group.values.length > 0 && (
                  <p className="text-[10px] text-muted-foreground mt-1">{group.values.length} readings</p>
                )}
              </div>
            )
          })}
        </motion.div>
      )}

      {/* ECG Section */}
      {hasData && (
        <motion.div variants={ITEM} className="clinical-card">
          <h2 className="text-sm font-bold text-foreground mb-3 flex items-center gap-2">
            <HeartPulse className="w-4 h-4 text-danger-500" />
            ECG Monitor
            {ecgObs.length > 0 && (
              <span className="ml-auto text-xs font-normal text-muted-foreground">{ecgObs.length} readings (24h)</span>
            )}
          </h2>

          {ecgObs.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Live ECG waveform based on latest rhythm */}
              <div className="rounded-lg bg-gray-950 p-3">
                <EcgWaveform
                  heartRate={latestEcgHR ?? 72}
                  rhythm={latestEcgRhythm}
                  width={500}
                  height={160}
                  isLive
                  showOverlay
                  color="#22c55e"
                />
              </div>

              {/* ECG history table */}
              <div className="overflow-auto max-h-52">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border text-muted-foreground">
                      <th className="text-left py-1.5 px-2 font-medium">Time</th>
                      <th className="text-left py-1.5 px-2 font-medium">HR (bpm)</th>
                      <th className="text-left py-1.5 px-2 font-medium">Rhythm</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ecgObs.slice(0, 20).map((obs, i) => {
                      const hr = getObsValue(obs)
                      const interp = getObsInterpretation(obs)
                      const rhythmLabel = interp === 'NSR' ? 'Normal Sinus' : interp
                      const isAbnormal = interp !== 'NSR' && interp !== 'N'
                      return (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-1 px-2 text-muted-foreground">{getObsTime(obs)}</td>
                          <td className="py-1 px-2 font-mono font-medium text-foreground">{hr != null ? Math.round(hr) : '—'}</td>
                          <td className={cn('py-1 px-2', isAbnormal ? 'text-danger-500 font-medium' : 'text-secondary-600')}>
                            {rhythmLabel}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">No ECG data available. Run the simulator with ECG enabled to generate readings.</p>
          )}
        </motion.div>
      )}

      {/* Trend charts */}
      {hasData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {VITAL_DEFS.map((def) => {
            const group = vitalGroups[def.code]
            if (!group || group.values.length === 0) return null
            return (
              <motion.div key={def.code} variants={ITEM} className="clinical-card">
                <h2 className="text-sm font-bold text-foreground mb-4 flex items-center gap-2">
                  <def.icon className={cn('w-4 h-4', def.color)} />
                  {def.label} (24h Trend)
                </h2>
                <div style={{ height: 180 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={group.values} margin={{ top: 5, right: 16, bottom: 0, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.4} />
                      <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                      <YAxis tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }} tickLine={false} axisLine={false} />
                      <Tooltip
                        formatter={(v: number) => [`${v} ${def.unit}`, def.label]}
                        contentStyle={{ background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: 8, fontSize: 12 }}
                      />
                      <ReferenceLine y={def.normalHigh} stroke="#e11d48" strokeDasharray="4 4" strokeOpacity={0.6} />
                      <ReferenceLine y={def.normalLow} stroke="#f59e0b" strokeDasharray="4 4" strokeOpacity={0.6} />
                      <Line type="monotone" dataKey="value" stroke={def.chartColor} strokeWidth={2.5} dot={group.values.length < 30 ? { r: 2, fill: def.chartColor } : false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>
            )
          })}
        </div>
      )}
    </motion.div>
  )
}
