import { useMemo } from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  TooltipProps,
} from 'recharts'
import { format } from 'date-fns'
import type { AgentExecution } from '@/types/agent'
import { AGENT_TIER_COLORS, AGENT_DEFINITIONS } from '@/types/agent'

interface AgentActivityTimelineProps {
  executions: AgentExecution[]
  height?: number
  hoursBack?: number
}

interface PlotPoint {
  x: number
  y: number
  label: string
  agentName: string
  status: string
  tier: string
  duration?: number
  patientId?: string
  timeLabel: string
}

const STATUS_COLORS: Record<string, string> = {
  completed: '#16a34a',
  running: '#3b82f6',
  failed: '#e11d48',
  queued: '#d97706',
  pending_hitl: '#7c3aed',
  cancelled: '#94a3b8',
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload as PlotPoint

  return (
    <div className="bg-card border border-border rounded-lg shadow-clinical p-3 text-xs space-y-1.5">
      <p className="font-semibold text-foreground">{point.agentName}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
        <span className="text-muted-foreground">Status:</span>
        <span
          className="font-semibold capitalize"
          style={{ color: STATUS_COLORS[point.status] ?? '#94a3b8' }}
        >
          {point.status.replace(/_/g, ' ')}
        </span>
        <span className="text-muted-foreground">Time:</span>
        <span className="font-mono">{point.timeLabel}</span>
        {point.duration !== undefined && (
          <>
            <span className="text-muted-foreground">Duration:</span>
            <span className="font-mono">{point.duration}s</span>
          </>
        )}
        {point.patientId && (
          <>
            <span className="text-muted-foreground">Patient:</span>
            <span className="font-mono">{point.patientId}</span>
          </>
        )}
      </div>
    </div>
  )
}

export default function AgentActivityTimeline({
  executions,
  height = 320,
  hoursBack = 24,
}: AgentActivityTimelineProps) {
  const { plotData, yLabels, xDomain } = useMemo(() => {
    const now = Date.now()
    const cutoff = now - hoursBack * 60 * 60 * 1000

    // Get unique agents from executions
    const agentIds = [...new Set(executions.map((e) => e.agentId))]

    const yLabels = agentIds.map((id) => {
      const def = AGENT_DEFINITIONS.find((d) => d.id === id)
      return def?.name ?? id
    })

    const plotData: PlotPoint[] = executions
      .filter((e) => {
        const ts = new Date(e.triggeredAt).getTime()
        return ts >= cutoff && ts <= now
      })
      .map((e) => {
        const x = new Date(e.triggeredAt).getTime()
        const y = agentIds.indexOf(e.agentId)
        const duration = e.completedAt && e.startedAt
          ? Math.round((new Date(e.completedAt).getTime() - new Date(e.startedAt).getTime()) / 1000)
          : undefined

        return {
          x,
          y,
          label: e.agentId,
          agentName: e.agentName,
          status: e.status,
          tier: e.tier,
          duration,
          patientId: e.patientId,
          timeLabel: format(new Date(e.triggeredAt), 'HH:mm:ss'),
        }
      })

    return {
      plotData,
      yLabels,
      xDomain: [cutoff, now] as [number, number],
    }
  }, [executions, hoursBack])

  const xTickFormatter = (value: number) => format(new Date(value), 'HH:mm')

  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 16, right: 16, bottom: 8, left: 120 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.4} />

          <XAxis
            type="number"
            dataKey="x"
            domain={xDomain}
            tickFormatter={xTickFormatter}
            tick={{ fontSize: 10, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
            scale="time"
          />

          <YAxis
            type="number"
            dataKey="y"
            domain={[-0.5, yLabels.length - 0.5]}
            tickCount={yLabels.length}
            tickFormatter={(v: number) => yLabels[v] ?? ''}
            tick={{ fontSize: 10, fill: 'hsl(var(--foreground))', fontWeight: 500 }}
            tickLine={false}
            axisLine={false}
            width={116}
          />

          <Tooltip content={<CustomTooltip />} cursor={false} />

          <Scatter data={plotData} isAnimationActive={false}>
            {plotData.map((point, i) => (
              <Cell
                key={i}
                fill={STATUS_COLORS[point.status] ?? '#94a3b8'}
                opacity={0.85}
                r={6}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-[11px]">
        {Object.entries(STATUS_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            <span className="text-muted-foreground capitalize">{status.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
