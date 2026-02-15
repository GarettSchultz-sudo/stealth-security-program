'use client'

import { useQuery } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import {
  DollarSign,
  TrendingUp,
  Activity,
  Zap,
  Calendar,
  RefreshCw,
  Cpu,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  StatCard,
  StatsGrid,
  StatCardSkeleton,
} from '@/components/scan'
import { Card, CardHeader, CardContent, PageHeader } from '@/components/ui'
import { useRealtimeLogs } from '@/lib/useRealtimeLogs'

// Chart colors matching the design system
const CHART_COLORS = {
  cyan: '#22d3ee',
  purple: '#a855f7',
  emerald: '#34d399',
  amber: '#fbbf24',
  rose: '#fb7185',
  blue: '#60a5fa',
}

const PIE_COLORS = [
  CHART_COLORS.cyan,
  CHART_COLORS.purple,
  CHART_COLORS.emerald,
  CHART_COLORS.amber,
  CHART_COLORS.rose,
  CHART_COLORS.blue,
]

// Custom tooltip for charts
function CustomTooltip({ active, payload, label }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg p-3 shadow-xl">
        <p className="text-xs text-slate-400 mb-1">{label}</p>
        <p className="text-sm font-mono font-semibold text-white">
          ${payload[0].value.toFixed(4)}
        </p>
      </div>
    )
  }
  return null
}

function CustomPieTooltip({ active, payload }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg p-3 shadow-xl">
        <p className="text-sm text-white font-medium">{payload[0].name}</p>
        <p className="text-xs font-mono text-cyan-400 mt-1">
          ${payload[0].value.toFixed(4)}
        </p>
        <p className="text-xs text-slate-400">
          {(payload[0].payload.percent * 100).toFixed(1)}% of total
        </p>
      </div>
    )
  }
  return null
}

interface StatsResponse {
  todaySpend: number
  yesterdaySpend: number
  monthSpend: number
  monthRequests: number
  avgCostPerRequest: number
  trend: number
}

interface ChartDataItem {
  date: string
  spend: number
  requests: number
}

interface ModelDataItem {
  model: string
  requests: number
  total_cost: number
  avg_latency: number
  percent?: number
}

export default function Dashboard() {
  // Enable realtime updates for request logs
  const { isConnected: realtimeConnected } = useRealtimeLogs(true)

  // Fetch stats using authenticated endpoint
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useQuery<StatsResponse>({
    queryKey: ['stats'],
    queryFn: async () => {
      const response = await fetch('/api/stats')
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Unauthorized')
        }
        throw new Error('Failed to fetch stats')
      }
      return response.json()
    },
  })

  // Fetch chart data
  const { data: chartResponse, isLoading: chartLoading, refetch: refetchCharts } = useQuery<{ data: ChartDataItem[] }>({
    queryKey: ['chart'],
    queryFn: async () => {
      const response = await fetch('/api/stats/charts?days=30')
      if (!response.ok) {
        throw new Error('Failed to fetch chart data')
      }
      return response.json()
    },
  })

  // Fetch model breakdown
  const { data: modelResponse, isLoading: modelLoading } = useQuery<{ data: ModelDataItem[] }>({
    queryKey: ['models'],
    queryFn: async () => {
      const response = await fetch('/api/stats/models?days=7')
      if (!response.ok) {
        throw new Error('Failed to fetch model data')
      }
      return response.json()
    },
  })

  const chartData = chartResponse?.data || []
  const modelData = modelResponse?.data || []

  // Add percent to model data for pie chart
  const totalModelCost = modelData.reduce((sum, item) => sum + item.total_cost, 0)
  const pieData = modelData.map((item) => ({
    ...item,
    percent: totalModelCost > 0 ? item.total_cost / totalModelCost : 0,
  }))

  const isLoading = statsLoading || chartLoading || modelLoading

  const handleRefresh = () => {
    refetchStats()
    refetchCharts()
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Cost Control Dashboard"
        description="Monitor and optimize your AI infrastructure costs"
        icon={Activity}
        iconColor="cyan"
        action={
          <div className="flex items-center gap-2">
            {/* Realtime status indicator */}
            <div className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm transition-all',
              realtimeConnected
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-slate-800/50 border-slate-700/50 text-slate-500'
            )}>
              {realtimeConnected ? (
                <>
                  <Wifi size={14} />
                  <span className="hidden sm:inline">Live</span>
                </>
              ) : (
                <>
                  <WifiOff size={14} />
                  <span className="hidden sm:inline">Offline</span>
                </>
              )}
            </div>
            <button
              onClick={handleRefresh}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/30 transition-all text-sm"
            >
              <RefreshCw size={14} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        }
      />

      {/* Stats Grid */}
      {isLoading ? (
        <StatsGrid columns={4}>
          {[...Array(4)].map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </StatsGrid>
      ) : (
        <StatsGrid columns={4}>
          <StatCard
            label="Today's Spend"
            value={stats?.todaySpend?.toFixed(2) || '0.00'}
            icon={DollarSign}
            prefix="$"
            accent="cyan"
            trend={stats?.trend !== 0 ? {
              value: stats?.trend || 0,
              label: 'vs yesterday',
            } : undefined}
          />
          <StatCard
            label="This Month"
            value={stats?.monthSpend?.toFixed(2) || '0.00'}
            icon={Calendar}
            prefix="$"
            accent="purple"
          />
          <StatCard
            label="Total Requests"
            value={stats?.monthRequests?.toLocaleString() || '0'}
            icon={Zap}
            accent="emerald"
          />
          <StatCard
            label="Avg Cost/Request"
            value={stats?.avgCostPerRequest?.toFixed(6) || '0.000000'}
            icon={TrendingUp}
            prefix="$"
            accent="amber"
          />
        </StatsGrid>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Spend Over Time */}
        <Card variant="default" className="col-span-1 lg:col-span-2">
          <CardHeader>
            Daily Spend
            <span className="text-xs text-slate-500 font-normal ml-2">Last 30 Days</span>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="h-72">
              {chartLoading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-slate-500">Loading chart...</div>
                </div>
              ) : chartData.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center text-slate-500">
                    <Activity size={32} className="mx-auto mb-2 opacity-50" />
                    <p>No usage data yet</p>
                    <p className="text-sm text-slate-600 mt-1">Make API requests to see your spending trends</p>
                  </div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.cyan} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={CHART_COLORS.cyan} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={{ stroke: '#334155' }}
                      tickFormatter={(value) => {
                        const date = new Date(value)
                        return `${date.getMonth() + 1}/${date.getDate()}`
                      }}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `$${v}`}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="spend"
                      stroke={CHART_COLORS.cyan}
                      strokeWidth={2}
                      fill="url(#spendGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Model Breakdown */}
        <Card variant="default">
          <CardHeader>
            Cost by Model
            <span className="text-xs text-slate-500 font-normal ml-2">7 Days</span>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="h-64">
              {modelLoading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-slate-500">Loading...</div>
                </div>
              ) : pieData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  <div className="text-center">
                    <Cpu size={32} className="mx-auto mb-2 opacity-50" />
                    <p>No model data</p>
                  </div>
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="total_cost"
                      nameKey="model"
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={2}
                    >
                      {pieData.map((_: ModelDataItem, index: number) => (
                        <Cell
                          key={index}
                          fill={PIE_COLORS[index % PIE_COLORS.length]}
                          stroke="transparent"
                        />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomPieTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
            {/* Legend */}
            <div className="mt-4 space-y-2">
              {pieData.slice(0, 4).map((item: ModelDataItem, index: number) => (
                <div key={item.model} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
                    />
                    <span className="text-slate-400 truncate max-w-[120px]">{item.model}</span>
                  </div>
                  <span className="font-mono text-slate-300">
                    ${item.total_cost.toFixed(4)}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Model Performance Table */}
      <Card variant="default">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Cpu size={18} className="text-cyan-400" />
            Model Performance
          </div>
          <span className="text-xs text-slate-500">Last 7 Days</span>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-slate-800/50">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Model
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Requests
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Total Cost
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Avg Latency
                  </th>
                </tr>
              </thead>
              <tbody>
                {modelLoading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="border-b border-slate-800/50">
                      <td className="py-3 px-4" colSpan={4}>
                        <div className="h-4 bg-slate-700/50 rounded animate-pulse" />
                      </td>
                    </tr>
                  ))
                ) : modelData.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-slate-500">
                      <Cpu size={24} className="mx-auto mb-2 opacity-50" />
                      No model data available
                      <p className="text-sm text-slate-600 mt-1">Make API requests to see model performance</p>
                    </td>
                  </tr>
                ) : (
                  modelData.map((row: ModelDataItem, i: number) => (
                    <tr
                      key={i}
                      className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                          />
                          <span className="text-slate-200 font-medium">{row.model}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-slate-300">
                        {row.requests.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-cyan-400">
                        ${row.total_cost.toFixed(4)}
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-slate-400">
                        {row.avg_latency}ms
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
