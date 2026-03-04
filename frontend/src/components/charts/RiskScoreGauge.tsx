import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts'
import { cn } from '@/lib/utils'

interface RiskScoreGaugeProps {
  score: number              // 0-100
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  animate?: boolean
}

function getRiskConfig(score: number) {
  if (score >= 80) return {
    label: 'Critical',
    color: '#e11d48',
    bg: 'bg-danger-50 dark:bg-danger-900/20',
    textColor: 'text-danger-600 dark:text-danger-400',
    ring: 'ring-danger-200 dark:ring-danger-800',
  }
  if (score >= 60) return {
    label: 'High',
    color: '#ea580c',
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    textColor: 'text-orange-600 dark:text-orange-400',
    ring: 'ring-orange-200 dark:ring-orange-800',
  }
  if (score >= 30) return {
    label: 'Medium',
    color: '#d97706',
    bg: 'bg-warning-50 dark:bg-warning-900/20',
    textColor: 'text-warning-600 dark:text-warning-400',
    ring: 'ring-warning-200 dark:ring-warning-800',
  }
  return {
    label: 'Low',
    color: '#16a34a',
    bg: 'bg-secondary-50 dark:bg-secondary-900/20',
    textColor: 'text-secondary-600 dark:text-secondary-400',
    ring: 'ring-secondary-200 dark:ring-secondary-800',
  }
}

const SIZE_CONFIG = {
  sm: { height: 80, innerRadius: 25, outerRadius: 38, fontSize: 'text-lg', labelSize: 'text-[10px]' },
  md: { height: 140, innerRadius: 44, outerRadius: 62, fontSize: 'text-2xl', labelSize: 'text-xs' },
  lg: { height: 200, innerRadius: 64, outerRadius: 88, fontSize: 'text-4xl', labelSize: 'text-sm' },
}

export default function RiskScoreGauge({
  score,
  size = 'md',
  showLabel = true,
  animate = true,
}: RiskScoreGaugeProps) {
  const config = getRiskConfig(score)
  const sizeConfig = SIZE_CONFIG[size]

  // Data for the gauge
  const data = [
    { name: 'bg', value: 100, fill: 'hsl(var(--muted))' },
    { name: 'score', value: score, fill: config.color },
  ]

  return (
    <div className="relative flex flex-col items-center">
      <div style={{ height: sizeConfig.height, width: sizeConfig.height }} className="relative">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius={sizeConfig.innerRadius}
            outerRadius={sizeConfig.outerRadius}
            barSize={sizeConfig.size === 'sm' ? 8 : 12}
            data={data}
            startAngle={210}
            endAngle={-30}
          >
            <RadialBar
              dataKey="value"
              cornerRadius={4}
              background={{ fill: 'hsl(var(--muted))' }}
              isAnimationActive={animate}
              animationBegin={0}
              animationDuration={800}
              animationEasing="ease-out"
            />
          </RadialBarChart>
        </ResponsiveContainer>

        {/* Center score */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={cn('font-bold tabular-nums leading-none', sizeConfig.fontSize, config.textColor)}
          >
            {Math.round(score)}
          </span>
          {showLabel && size !== 'sm' && (
            <span className={cn('font-medium mt-0.5', sizeConfig.labelSize, config.textColor)}>
              {config.label}
            </span>
          )}
        </div>
      </div>

      {/* Risk label below for sm */}
      {showLabel && size === 'sm' && (
        <span className={cn('text-[10px] font-semibold mt-1', config.textColor)}>
          {config.label}
        </span>
      )}
    </div>
  )
}

// ─── Mini inline version ──────────────────────────────────────────────────────

interface RiskScoreBadgeProps {
  score: number
  showScore?: boolean
}

export function RiskScoreBadge({ score, showScore = true }: RiskScoreBadgeProps) {
  const config = getRiskConfig(score)

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-semibold',
        config.bg,
        config.textColor,
      )}
    >
      <span
        className="w-1.5 h-1.5 rounded-full flex-shrink-0"
        style={{ background: config.color }}
      />
      {config.label}
      {showScore && <span className="font-mono">{Math.round(score)}%</span>}
    </span>
  )
}
