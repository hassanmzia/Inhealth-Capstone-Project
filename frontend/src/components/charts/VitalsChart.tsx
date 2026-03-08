import { useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  TooltipProps,
} from 'recharts'
import { format } from 'date-fns'
import type { VitalSign } from '@/types/clinical'

interface VitalsChartProps {
  vitals: VitalSign[]
  height?: number
  showHR?: boolean
  showBP?: boolean
  showSpO2?: boolean
  showTemp?: boolean
  timeRangeHours?: number
}

interface ChartDataPoint {
  time: number
  timeLabel: string
  hr?: number
  sys?: number
  dia?: number
  spo2?: number
  temp?: number
  hrStatus?: string
  bpStatus?: string
  spo2Status?: string
}

const STATUS_COLORS = {
  normal: '#16a34a',
  warning: '#d97706',
  critical: '#e11d48',
}

function CustomTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null

  return (
    <div className="bg-card border border-border rounded-lg shadow-clinical p-3 text-xs space-y-1.5">
      <p className="font-semibold text-foreground border-b border-border pb-1.5 mb-1.5">
        {label}
      </p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: entry.color }}
          />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-semibold text-foreground font-mono">
            {entry.value}
            {entry.name === 'HR' ? ' bpm' : entry.name === 'SpO2' ? '%' : entry.name === 'Temp' ? '°C' : ' mmHg'}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function VitalsChart({
  vitals,
  height = 280,
  showHR = true,
  showBP = true,
  showSpO2 = true,
  showTemp = false,
  timeRangeHours = 24,
}: VitalsChartProps) {
  const chartData = useMemo<ChartDataPoint[]>(() => {
    const cutoff = Date.now() - timeRangeHours * 60 * 60 * 1000
    let filtered = vitals.filter((v) => new Date(v.timestamp).getTime() > cutoff)

    // If no data within the time range, show all available data
    if (filtered.length === 0 && vitals.length > 0) {
      filtered = vitals
    }

    // Group by timestamp (rounded to minute)
    const byTime = new Map<number, ChartDataPoint>()

    for (const v of filtered) {
      const ts = Math.floor(new Date(v.timestamp).getTime() / 60000) * 60000
      if (!byTime.has(ts)) {
        byTime.set(ts, {
          time: ts,
          timeLabel: format(new Date(ts), 'HH:mm'),
        })
      }
      const point = byTime.get(ts)!

      switch (v.type) {
        case 'heart_rate':
          point.hr = v.value
          point.hrStatus = v.status
          break
        case 'blood_pressure_systolic':
          point.sys = v.systolic ?? v.value
          point.dia = v.diastolic ?? point.dia
          point.bpStatus = v.status
          break
        case 'blood_pressure_diastolic':
          point.dia = v.value
          break
        case 'spo2':
          point.spo2 = v.value
          point.spo2Status = v.status
          break
        case 'temperature':
          point.temp = v.value
          break
      }
    }

    return Array.from(byTime.values()).sort((a, b) => a.time - b.time)
  }, [vitals, timeRangeHours])

  const yAxisLeft = showBP
    ? { domain: [40, 200], label: 'mmHg / bpm' }
    : { domain: [40, 160], label: 'bpm' }

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.5} />

          <XAxis
            dataKey="timeLabel"
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />

          {/* Left Y-axis: HR + BP */}
          <YAxis
            yAxisId="left"
            domain={yAxisLeft.domain}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
            width={36}
            label={{
              value: yAxisLeft.label,
              angle: -90,
              position: 'insideLeft',
              style: { fontSize: 10, fill: 'hsl(var(--muted-foreground))' },
              offset: 10,
            }}
          />

          {/* Right Y-axis: SpO2 */}
          {showSpO2 && (
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[85, 100]}
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              tickLine={false}
              axisLine={false}
              width={36}
              label={{
                value: 'SpO2 %',
                angle: 90,
                position: 'insideRight',
                style: { fontSize: 10, fill: 'hsl(var(--muted-foreground))' },
              }}
            />
          )}

          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }}
            formatter={(value) => <span style={{ color: 'hsl(var(--muted-foreground))' }}>{value}</span>}
          />

          {/* Normal range reference lines */}
          {showHR && (
            <>
              <ReferenceLine yAxisId="left" y={100} stroke="#16a34a" strokeDasharray="4 2" strokeOpacity={0.4} strokeWidth={1} />
              <ReferenceLine yAxisId="left" y={60} stroke="#16a34a" strokeDasharray="4 2" strokeOpacity={0.4} strokeWidth={1} />
            </>
          )}

          {showBP && (
            <>
              <ReferenceLine yAxisId="left" y={140} stroke="#d97706" strokeDasharray="4 2" strokeOpacity={0.4} strokeWidth={1} />
              <ReferenceLine yAxisId="left" y={90} stroke="#d97706" strokeDasharray="4 2" strokeOpacity={0.4} strokeWidth={1} />
            </>
          )}

          {showSpO2 && (
            <ReferenceLine yAxisId="right" y={95} stroke="#e11d48" strokeDasharray="4 2" strokeOpacity={0.5} strokeWidth={1.5} label={{ value: 'SpO2 min', fontSize: 9, fill: '#e11d48', position: 'insideTopRight' }} />
          )}

          {/* Data lines */}
          {showHR && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="hr"
              name="HR"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#3b82f6' }}
              connectNulls
            />
          )}

          {showBP && (
            <>
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="sys"
                name="Systolic"
                stroke="#e11d48"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#e11d48' }}
                connectNulls
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="dia"
                name="Diastolic"
                stroke="#f87171"
                strokeWidth={1.5}
                strokeDasharray="4 2"
                dot={false}
                activeDot={{ r: 4, fill: '#f87171' }}
                connectNulls
              />
            </>
          )}

          {showSpO2 && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="spo2"
              name="SpO2"
              stroke="#16a34a"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: '#16a34a' }}
              connectNulls
            />
          )}

          {showTemp && (
            <Line
              yAxisId="left"
              type="monotone"
              dataKey="temp"
              name="Temp"
              stroke="#d97706"
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4, fill: '#d97706' }}
              connectNulls
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// Export STATUS_COLORS for use in other components
export { STATUS_COLORS }
