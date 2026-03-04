import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
  LabelList,
  TooltipProps,
} from 'recharts'

interface RiskTier {
  label: string
  count: number
  percentage: number
  color: string
  category: string
}

interface PopulationRiskPyramidProps {
  data: {
    critical: number
    high: number
    medium: number
    low: number
    total: number
  }
  height?: number
  orientation?: 'horizontal' | 'vertical'
}

function CustomTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null
  const entry = payload[0]
  const item = entry.payload as RiskTier

  return (
    <div className="bg-card border border-border rounded-lg shadow-clinical p-3 text-xs">
      <p className="font-semibold text-foreground">{item.label} Risk</p>
      <p className="text-muted-foreground mt-1">
        <span className="font-mono font-bold text-foreground">{item.count.toLocaleString()}</span>
        {' '}patients ({item.percentage.toFixed(1)}%)
      </p>
    </div>
  )
}

export default function PopulationRiskPyramid({
  data,
  height = 280,
  orientation = 'horizontal',
}: PopulationRiskPyramidProps) {
  const tiers: RiskTier[] = [
    {
      label: 'Critical',
      count: data.critical,
      percentage: data.total > 0 ? (data.critical / data.total) * 100 : 0,
      color: '#e11d48',
      category: 'critical',
    },
    {
      label: 'High',
      count: data.high,
      percentage: data.total > 0 ? (data.high / data.total) * 100 : 0,
      color: '#ea580c',
      category: 'high',
    },
    {
      label: 'Medium',
      count: data.medium,
      percentage: data.total > 0 ? (data.medium / data.total) * 100 : 0,
      color: '#d97706',
      category: 'medium',
    },
    {
      label: 'Low',
      count: data.low,
      percentage: data.total > 0 ? (data.low / data.total) * 100 : 0,
      color: '#16a34a',
      category: 'low',
    },
  ]

  if (orientation === 'vertical') {
    return (
      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={tiers}
            layout="vertical"
            margin={{ top: 8, right: 60, bottom: 8, left: 64 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" strokeOpacity={0.5} />
            <XAxis
              type="number"
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              tick={{ fontSize: 12, fill: 'hsl(var(--foreground))', fontWeight: 500 }}
              tickLine={false}
              axisLine={false}
              width={60}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(var(--accent))' }} />
            <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={32}>
              {tiers.map((tier) => (
                <Cell key={tier.category} fill={tier.color} fillOpacity={0.9} />
              ))}
              <LabelList
                dataKey="percentage"
                position="right"
                formatter={(v: number) => `${v.toFixed(1)}%`}
                style={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    )
  }

  return (
    <div>
      {/* Pyramid bars */}
      <div className="space-y-2">
        {tiers.map((tier) => (
          <div key={tier.category} className="flex items-center gap-3">
            <div className="w-16 text-right">
              <span className="text-xs font-medium text-foreground">{tier.label}</span>
            </div>
            <div className="flex-1 relative">
              <div className="flex items-center h-8 bg-muted rounded-md overflow-hidden">
                <div
                  className="h-full rounded-md transition-all duration-700 flex items-center px-2"
                  style={{
                    width: `${Math.max(tier.percentage, 2)}%`,
                    backgroundColor: tier.color,
                    opacity: 0.9,
                  }}
                />
              </div>
            </div>
            <div className="w-24 text-right">
              <span className="text-xs font-mono font-semibold text-foreground">
                {tier.count.toLocaleString()}
              </span>
              <span className="text-xs text-muted-foreground ml-1">
                ({tier.percentage.toFixed(1)}%)
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Total */}
      <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Total Active Patients</span>
        <span className="font-bold font-mono text-foreground">{data.total.toLocaleString()}</span>
      </div>
    </div>
  )
}
