'use client'

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
  ComposedChart,
  Area,
} from 'recharts'
import {
  TrendingUp,
  PieChart as PieChartIcon,
  BarChart3,
  Calendar,
  RefreshCw,
  Cpu,
  DollarSign,
  Zap,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Cloud,
  Users,
  Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  Card,
  CardHeader,
  CardContent,
  PageHeader,
  Button,
  Select,
} from '@/components/ui'
import { StatCard, StatsGrid } from '@/components/scan'

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

interface StatsResponse {
  todaySpend: number
  yesterdaySpend: number
  monthSpend: number
  monthRequests: number
  avgCostPerRequest: number
  trend: number
}

interface ProviderDataItem {
  provider: string
  spend_usd: number
  requests: number
  tokens: number
  model_count: number
  percent_of_total: number
}

interface AgentDataItem {
  agent_id: string | null
  agent_name: string
  spend_usd: number
  requests: number
  tokens: number
  avg_latency_ms: number
  percent_of_total: number
}

// Custom tooltip for charts
function CustomTooltip({ active, payload, label }: any) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800/95 backdrop-blur-sm border border-slate-700 rounded-lg p-3 shadow-xl">
        <p className="text-xs text-slate-400 mb-1">{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} className="text-sm font-mono" style={{ color: entry.color }}>
            {entry.name}: {entry.name.includes('Cost') || entry.name.includes('Spend')
              ? `$${entry.value.toFixed(4)}`
              : entry.value.toLocaleString()}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(30)

  // Fetch stats
  const { data: stats, isLoading: statsLoading, refetch } = useQuery<StatsResponse>({
    queryKey: ['stats'],
    queryFn: async () => {
      const response = await fetch('/api/stats')
      if (!response.ok) throw new Error('Failed to fetch stats')
      return response.json()
    },
  })

  // Fetch chart data
  const { data: chartResponse, isLoading: chartLoading } = useQuery<{ data: ChartDataItem[] }>({
    queryKey: ['chart', days],
    queryFn: async () => {
      const response = await fetch(`/api/stats/charts?days=${days}`)
      if (!response.ok) throw new Error('Failed to fetch chart data')
      return response.json()
    },
  })

  // Fetch model breakdown
  const { data: modelResponse, isLoading: modelLoading } = useQuery<{ data: ModelDataItem[] }>({
    queryKey: ['models', days],
    queryFn: async () => {
      const response = await fetch(`/api/stats/models?days=${days}`)
      if (!response.ok) throw new Error('Failed to fetch model data')
      return response.json()
    },
  })

  // Fetch provider breakdown
  const { data: providerResponse, isLoading: providerLoading } = useQuery<ProviderDataItem[]>({
    queryKey: ['providers', days],
    queryFn: async () => {
      const response = await fetch(`/api/analytics/providers?days=${days}`)
      if (!response.ok) throw new Error('Failed to fetch provider data')
      return response.json()
    },
  })

  // Fetch agent breakdown
  const { data: agentResponse, isLoading: agentLoading } = useQuery<AgentDataItem[]>({
    queryKey: ['agents', days],
    queryFn: async () => {
      const response = await fetch(`/api/analytics/agents?days=${days}`)
      if (!response.ok) throw new Error('Failed to fetch agent data')
      return response.json()
    },
  })

  const chartData = chartResponse?.data || []
  const modelData = modelResponse?.data || []
  const providerData = providerResponse || []
  const agentData = agentResponse || []

  // Add percent to model data
  const totalModelCost = modelData.reduce((sum, item) => sum + item.total_cost, 0)
  const pieData = modelData.slice(0, 6).map((item) => ({
    ...item,
    percent: totalModelCost > 0 ? item.total_cost / totalModelCost : 0,
  }))

  // Calculate trend indicators
  const costTrend = stats?.trend || 0
  const isUp = costTrend > 0

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Analytics"
        description="Deep dive into your AI usage patterns and costs"
        icon={TrendingUp}
        iconColor="purple"
        action={
          <div className="flex items-center gap-2">
            <Select
              value={days.toString()}
              onChange={(value) => setDays(parseInt(value, 10))}
              options={[
                { value: '7', label: 'Last 7 days' },
                { value: '14', label: 'Last 14 days' },
                { value: '30', label: 'Last 30 days' },
                { value: '60', label: 'Last 60 days' },
                { value: '90', label: 'Last 90 days' },
              ]}
            />
            <Button
              variant="secondary"
              icon={RefreshCw}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
          </div>
        }
      />

      {/* Stats Grid */}
      <StatsGrid columns={4}>
        <StatCard
          label="Total Spend"
          value={stats?.monthSpend?.toFixed(2) || '0.00'}
          icon={DollarSign}
          prefix="$"
          accent="cyan"
          trend={costTrend !== 0 ? {
            value: costTrend,
            label: 'vs last period',
          } : undefined}
        />
        <StatCard
          label="Total Requests"
          value={stats?.monthRequests?.toLocaleString() || '0'}
          icon={Zap}
          accent="purple"
        />
        <StatCard
          label="Avg Cost/Request"
          value={stats?.avgCostPerRequest?.toFixed(6) || '0.000000'}
          icon={TrendingUp}
          prefix="$"
          accent="emerald"
        />
        <StatCard
          label="Unique Models"
          value={modelData.length.toString()}
          icon={Cpu}
          accent="amber"
        />
      </StatsGrid>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Spend & Requests Over Time */}
        <Card variant="default" className="col-span-1 lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <TrendingUp size={18} className="text-cyan-400" />
              Spend & Requests Over Time
            </div>
            <span className="text-xs text-slate-500">Last {days} days</span>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="h-80">
              {chartLoading ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  Loading chart...
                </div>
              ) : chartData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No data available
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData}>
                    <defs>
                      <linearGradient id="spendGradientAnalytics" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={CHART_COLORS.cyan} stopOpacity={0.3} />
                        <stop offset="95%" stopColor={CHART_COLORS.cyan} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
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
                      yAxisId="left"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `$${v}`}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      wrapperStyle={{ paddingTop: 16 }}
                      formatter={(value) => (
                        <span className="text-slate-400 text-sm">{value}</span>
                      )}
                    />
                    <Area
                      yAxisId="left"
                      type="monotone"
                      dataKey="spend"
                      name="Spend ($)"
                      stroke={CHART_COLORS.cyan}
                      strokeWidth={2}
                      fill="url(#spendGradientAnalytics)"
                    />
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="requests"
                      name="Requests"
                      stroke={CHART_COLORS.purple}
                      strokeWidth={2}
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Cost Distribution Pie Chart */}
        <Card variant="default">
          <CardHeader>
            <div className="flex items-center gap-2">
              <PieChartIcon size={18} className="text-purple-400" />
              Cost Distribution
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="h-64">
              {modelLoading ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  Loading...
                </div>
              ) : pieData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No data available
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
                      innerRadius={45}
                      outerRadius={75}
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
                    <Tooltip
                      formatter={(value: number) => [`$${value.toFixed(4)}`, 'Cost']}
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </div>
            {/* Legend */}
            <div className="mt-4 space-y-2">
              {pieData.slice(0, 5).map((item: ModelDataItem, index: number) => (
                <div key={item.model} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: PIE_COLORS[index % PIE_COLORS.length] }}
                    />
                    <span className="text-slate-400 truncate max-w-[100px]">{item.model}</span>
                  </div>
                  <span className="font-mono text-slate-300">
                    {(item.percent! * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Model Performance Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cost by Model */}
        <Card variant="default">
          <CardHeader>
            <div className="flex items-center gap-2">
              <DollarSign size={18} className="text-emerald-400" />
              Cost by Model
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="h-72">
              {modelLoading ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  Loading...
                </div>
              ) : modelData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No data available
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={modelData.slice(0, 8)} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickFormatter={(v) => `$${v}`}
                    />
                    <YAxis
                      dataKey="model"
                      type="category"
                      width={120}
                      tick={{ fontSize: 11, fill: '#64748b' }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                      dataKey="total_cost"
                      name="Cost"
                      fill={CHART_COLORS.cyan}
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Requests by Model */}
        <Card variant="default">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Zap size={18} className="text-amber-400" />
              Requests by Model
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="h-72">
              {modelLoading ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  Loading...
                </div>
              ) : modelData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No data available
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={modelData.slice(0, 8)} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                    />
                    <YAxis
                      dataKey="model"
                      type="category"
                      width={120}
                      tick={{ fontSize: 11, fill: '#64748b' }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                      dataKey="requests"
                      name="Requests"
                      fill={CHART_COLORS.purple}
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Latency Analysis */}
      <Card variant="default">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-rose-400" />
            Latency Analysis
          </div>
          <span className="text-xs text-slate-500">Average response time by model</span>
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
                    Avg Latency
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Requests
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Performance
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
                      No data available
                    </td>
                  </tr>
                ) : (
                  modelData.map((row: ModelDataItem, i: number) => {
                    const latency = row.avg_latency
                    const maxLatency = Math.max(...modelData.map((m) => m.avg_latency))
                    const latencyPercent = maxLatency > 0 ? (latency / maxLatency) * 100 : 0

                    return (
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
                        <td className="py-3 px-4 text-right font-mono text-rose-400">
                          {latency}ms
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-300">
                          {row.requests.toLocaleString()}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className={cn(
                                  'h-full rounded-full transition-all',
                                  latency < 500 ? 'bg-emerald-500' :
                                  latency < 1000 ? 'bg-amber-500' : 'bg-rose-500'
                                )}
                                style={{ width: `${latencyPercent}%` }}
                              />
                            </div>
                            <span className={cn(
                              'text-xs font-medium',
                              latency < 500 ? 'text-emerald-400' :
                              latency < 1000 ? 'text-amber-400' : 'text-rose-400'
                            )}>
                              {latency < 500 ? 'Fast' : latency < 1000 ? 'Normal' : 'Slow'}
                            </span>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Provider Comparison Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Provider Comparison Chart */}
        <Card variant="default">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Cloud size={18} className="text-blue-400" />
              Provider Comparison
            </div>
            <span className="text-xs text-slate-500">Spend by provider</span>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="h-72">
              {providerLoading ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  Loading...
                </div>
              ) : providerData.length === 0 ? (
                <div className="h-full flex items-center justify-center text-slate-500">
                  No data available
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={providerData.slice(0, 6)} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickFormatter={(v) => `$${v}`}
                    />
                    <YAxis
                      dataKey="provider"
                      type="category"
                      width={80}
                      tick={{ fontSize: 11, fill: '#64748b' }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar
                      dataKey="spend_usd"
                      name="Spend"
                      fill={CHART_COLORS.blue}
                      radius={[0, 4, 4, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Provider Stats Table */}
        <Card variant="default">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-emerald-400" />
              Provider Details
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Provider
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Requests
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Models
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Share
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {providerLoading ? (
                    [...Array(5)].map((_, i) => (
                      <tr key={i} className="border-b border-slate-800/50">
                        <td className="py-3 px-4" colSpan={4}>
                          <div className="h-4 bg-slate-700/50 rounded animate-pulse" />
                        </td>
                      </tr>
                    ))
                  ) : providerData.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-slate-500">
                        No data available
                      </td>
                    </tr>
                  ) : (
                    providerData.slice(0, 6).map((row: ProviderDataItem, i: number) => (
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
                            <span className="text-slate-200 font-medium capitalize">{row.provider}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-300">
                          {row.requests.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-300">
                          {row.model_count}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-cyan-400">
                          {row.percent_of_total.toFixed(1)}%
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

      {/* Agent Activity Section */}
      <Card variant="default">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Users size={18} className="text-purple-400" />
            Agent Activity Metrics
          </div>
          <span className="text-xs text-slate-500">Usage breakdown by agent</span>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="bg-slate-800/50">
                  <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Agent
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Spend
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Requests
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Tokens
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Avg Latency
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                    Share
                  </th>
                </tr>
              </thead>
              <tbody>
                {agentLoading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="border-b border-slate-800/50">
                      <td className="py-3 px-4" colSpan={6}>
                        <div className="h-4 bg-slate-700/50 rounded animate-pulse" />
                      </td>
                    </tr>
                  ))
                ) : agentData.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No agent activity data available
                    </td>
                  </tr>
                ) : (
                  agentData.map((row: AgentDataItem, i: number) => {
                    const latency = row.avg_latency_ms
                    return (
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
                            <span className="text-slate-200 font-medium">{row.agent_name}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-emerald-400">
                          ${row.spend_usd.toFixed(4)}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-300">
                          {row.requests.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-300">
                          {row.tokens.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right font-mono text-slate-300">
                          <span className={cn(
                            latency < 500 ? 'text-emerald-400' :
                            latency < 1000 ? 'text-amber-400' : 'text-rose-400'
                          )}>
                            {latency}ms
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 h-2 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full bg-purple-500"
                                style={{ width: `${row.percent_of_total}%` }}
                              />
                            </div>
                            <span className="font-mono text-purple-400 text-xs">
                              {row.percent_of_total.toFixed(1)}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
