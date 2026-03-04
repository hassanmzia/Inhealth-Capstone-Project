import { useMemo } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  ReferenceArea,
  TooltipProps,
  Line,
  ComposedChart,
  Scatter,
} from 'recharts'
import { format } from 'date-fns'

export interface GlucoseReading {
  timestamp: string
  value: number
  predicted?: number
  isHypo?: boolean
  isHyper?: boolean
  source?: 'cgm' | 'fingerstick'
}

interface GlucoseChartProps {
  readings: GlucoseReading[]
  height?: number
  showPrediction?: boolean
  targetLow?: number   // default 70
  targetHigh?: number  // default 180
  showTIR?: boolean    // show time-in-range stats
}

interface TIRStats {
  veryLow: number
  low: number
  inRange: number
  high: number
  veryHigh: number
}

function calculateTIR(readings: GlucoseReading[], low: number, high: number): TIRStats {
  if (!readings.length) return { veryLow: 0, low: 0, inRange: 0, high: 0, veryHigh: 0 }
  const total = readings.length
  return {
    veryLow: Math.round((readings.filter((r) => r.value < 54).length / total) * 100),
    low: Math.round((readings.filter((r) => r.value >= 54 && r.value < low).length / total) * 100),
    inRange: Math.round((readings.filter((r) => r.value >= low && r.value <= high).length / total) * 100),
    high: Math.round((readings.filter((r) => r.value > high && r.value <= 250).length / total) * 100),
    veryHigh: Math.round((readings.filter((r) => r.value > 250).length / total) * 100),
  }
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload as GlucoseReading & { timeLabel: string }
  if (!point) return null

  const value = point.value
  const predicted = point.predicted

  let statusText = 'In Range'
  let statusColor = '#16a34a'
  if (value < 54) { statusText = 'Very Low'; statusColor = '#be123c' }
  else if (value < 70) { statusText = 'Low'; statusColor = '#e11d48' }
  else if (value > 250) { statusText = 'Very High'; statusColor = '#7c3aed' }
  else if (value > 180) { statusText = 'High'; statusColor = '#d97706' }

  return (
    <div className="bg-card border border-border rounded-lg shadow-clinical p-3 text-xs space-y-1">
      <p className="font-semibold text-foreground">{point.timeLabel}</p>
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full" style={{ background: statusColor }} />
        <span className="font-mono font-bold text-foreground">{value} mg/dL</span>
        <span style={{ color: statusColor }} className="font-medium">{statusText}</span>
      </div>
      {predicted !== undefined && (
        <div className="flex items-center gap-2 text-muted-foreground">
          <span className="w-2 h-2 rounded-full bg-purple-400" />
          <span>Predicted: </span>
          <span className="font-mono font-semibold">{Math.round(predicted)} mg/dL</span>
        </div>
      )}
    </div>
  )
}

export default function GlucoseChart({
  readings,
  height = 300,
  showPrediction = true,
  targetLow = 70,
  targetHigh = 180,
  showTIR = true,
}: GlucoseChartProps) {
  const chartData = useMemo(() => {
    return readings
      .map((r) => ({
        ...r,
        timeLabel: format(new Date(r.timestamp), 'MMM d HH:mm'),
        timeMs: new Date(r.timestamp).getTime(),
      }))
      .sort((a, b) => a.timeMs - b.timeMs)
  }, [readings])

  const tir = useMemo(() => calculateTIR(readings, targetLow, targetHigh), [readings, targetLow, targetHigh])

  const maxVal = Math.max(300, ...readings.map((r) => r.value))
  const domain: [number, number] = [40, maxVal + 20]

  // Find hypo/hyper events for scatter
  const hypoEvents = chartData.filter((r) => r.value < targetLow)
  const hyperEvents = chartData.filter((r) => r.value > targetHigh)

  return (
    <div className="space-y-3">
      {/* Time in range stats */}
      {showTIR && readings.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Time in Range</span>
            <span className="font-semibold text-secondary-600 dark:text-secondary-400">
              {tir.inRange}% in range
            </span>
          </div>
          {/* TIR bar */}
          <div className="flex h-3 rounded-full overflow-hidden w-full">
            <div className="bg-danger-800" style={{ width: `${tir.veryLow}%` }} title={`Very Low: ${tir.veryLow}%`} />
            <div className="bg-danger-500" style={{ width: `${tir.low}%` }} title={`Low: ${tir.low}%`} />
            <div className="bg-secondary-500" style={{ width: `${tir.inRange}%` }} title={`In Range: ${tir.inRange}%`} />
            <div className="bg-warning-500" style={{ width: `${tir.high}%` }} title={`High: ${tir.high}%`} />
            <div className="bg-purple-600" style={{ width: `${tir.veryHigh}%` }} title={`Very High: ${tir.veryHigh}%`} />
          </div>
          <div className="flex justify-between text-[10px] text-muted-foreground">
            <span className="text-danger-600">&lt;54: {tir.veryLow}%</span>
            <span className="text-danger-500">54-70: {tir.low}%</span>
            <span className="text-secondary-600">70-180: {tir.inRange}%</span>
            <span className="text-warning-600">180-250: {tir.high}%</span>
            <span className="text-purple-600">&gt;250: {tir.veryHigh}%</span>
          </div>
        </div>
      )}

      {/* Chart */}
      <div style={{ height: height - (showTIR && readings.length > 0 ? 64 : 0) }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <defs>
              <linearGradient id="glucoseGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.02} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.4} />

            <XAxis
              dataKey="timeLabel"
              tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
              tickLine={false}
              axisLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              domain={domain}
              tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
              tickLine={false}
              axisLine={false}
              width={36}
              label={{
                value: 'mg/dL',
                angle: -90,
                position: 'insideLeft',
                style: { fontSize: 10, fill: 'hsl(var(--muted-foreground))' },
              }}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Target range shading */}
            <ReferenceArea
              y1={targetLow}
              y2={targetHigh}
              fill="#16a34a"
              fillOpacity={0.07}
              stroke="none"
            />

            {/* Target range lines */}
            <ReferenceLine y={targetHigh} stroke="#d97706" strokeDasharray="5 3" strokeWidth={1.5} label={{ value: `${targetHigh}`, position: 'right', fontSize: 10, fill: '#d97706' }} />
            <ReferenceLine y={targetLow} stroke="#e11d48" strokeDasharray="5 3" strokeWidth={1.5} label={{ value: `${targetLow}`, position: 'right', fontSize: 10, fill: '#e11d48' }} />
            <ReferenceLine y={54} stroke="#be123c" strokeDasharray="2 2" strokeWidth={1} />

            {/* Glucose area */}
            <Area
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              fill="url(#glucoseGradient)"
              dot={false}
              activeDot={{ r: 4, fill: '#3b82f6' }}
              connectNulls
            />

            {/* Predicted glucose (dashed) */}
            {showPrediction && (
              <Line
                type="monotone"
                dataKey="predicted"
                stroke="#7c3aed"
                strokeWidth={1.5}
                strokeDasharray="6 3"
                dot={false}
                activeDot={{ r: 3, fill: '#7c3aed' }}
                connectNulls
              />
            )}

            {/* Hypo event markers */}
            <Scatter
              data={hypoEvents}
              dataKey="value"
              fill="#e11d48"
              shape={(props: Record<string, unknown>) => {
                const { cx, cy } = props as { cx: number; cy: number }
                return (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={4}
                    fill="#e11d48"
                    stroke="#fff"
                    strokeWidth={1}
                  />
                )
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
