'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createClient } from '@supabase/supabase-js'
import {
  Cpu,
  Play,
  Layers,
  DollarSign,
  Activity,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Timer,
  Zap,
  CheckCircle,
  XCircle,
  Pause,
  Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { StatCard, StatsGrid } from '@/components/scan'
import {
  Card,
  CardHeader,
  CardContent,
  PageHeader,
  ProgressBar,
  StatusDot,
  EmptyState,
  ListSkeleton,
} from '@/components/ui'

function getSupabase() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  // Return null if credentials are not configured
  if (!url || !key || url === 'https://placeholder.supabase.co') {
    return null
  }

  return createClient(url, key)
}

interface Agent {
  id: string
  name: string
  description?: string
  agent_type: string
  status: string
  last_heartbeat?: string
  last_seen?: string
  total_requests: number
  total_tokens: number
  total_cost_usd: number
  total_tasks_completed: number
  total_tasks_failed: number
  tags?: string[]
  active_tasks?: number
  tasks_24h?: number
  cost_24h?: number
}

interface Task {
  id: string
  task_id: string
  title: string
  description?: string
  task_type?: string
  status: string
  progress_percent: number
  model?: string
  input_tokens: number
  output_tokens: number
  cost_usd: number
  started_at?: string
  completed_at?: string
  duration_ms?: number
  agent_id: string
  agents?: { name: string; agent_type: string }
}

const AGENT_TYPE_ICONS: Record<string, string> = {
  'claude-code': '🤖',
  cursor: '✨',
  aider: '🧠',
  copilot: '✈️',
  demo: '🎯',
  custom: '⚙️',
}

const TASK_STATUS_CONFIG: Record<string, { color: string; icon: typeof CheckCircle }> = {
  pending: { color: 'bg-amber-500/10 text-amber-400', icon: Clock },
  running: { color: 'bg-cyan-500/10 text-cyan-400', icon: Play },
  paused: { color: 'bg-slate-500/10 text-slate-400', icon: Pause },
  completed: { color: 'bg-emerald-500/10 text-emerald-400', icon: CheckCircle },
  failed: { color: 'bg-rose-500/10 text-rose-400', icon: XCircle },
  cancelled: { color: 'bg-slate-500/10 text-slate-500', icon: XCircle },
}

export default function AgentsPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'tasks' | 'activity'>('overview')
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [isAutoRefresh, setIsAutoRefresh] = useState(true)

  // Fetch agents with utilization data
  const { data: agents, isLoading: agentsLoading, refetch: refetchAgents } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const supabase = getSupabase()
      if (!supabase) return []
      const { data, error } = await supabase
        .from('agent_utilization')
        .select('*')
        .order('last_seen', { ascending: false })

      if (error) throw error
      return (data || []) as Agent[]
    },
    refetchInterval: isAutoRefresh ? 5000 : false,
  })

  // Fetch active tasks
  const { data: activeTasks, isLoading: tasksLoading, refetch: refetchTasks } = useQuery({
    queryKey: ['active-tasks'],
    queryFn: async () => {
      const supabase = getSupabase()
      if (!supabase) return []
      const { data, error } = await supabase
        .from('active_tasks')
        .select('*')
        .order('created_at', { ascending: false })
        .limit(50)

      if (error) throw error
      return (data || []) as Task[]
    },
    refetchInterval: isAutoRefresh ? 3000 : false,
  })

  // Fetch recent tasks for selected agent
  const { data: agentTasks } = useQuery({
    queryKey: ['agent-tasks', selectedAgent],
    queryFn: async () => {
      if (!selectedAgent) return []
      const supabase = getSupabase()
      if (!supabase) return []
      const { data, error } = await supabase
        .from('agent_tasks')
        .select('*')
        .eq('agent_id', selectedAgent)
        .order('created_at', { ascending: false })
        .limit(20)

      if (error) throw error
      return (data || []) as Task[]
    },
    enabled: !!selectedAgent,
  })

  const refreshAll = () => {
    refetchAgents()
    refetchTasks()
  }

  // Calculate totals
  const totals = {
    agents: agents?.length || 0,
    activeAgents: agents?.filter((a) => a.status === 'active').length || 0,
    activeTasks: activeTasks?.length || 0,
    totalCost24h: agents?.reduce((sum, a) => sum + (a.cost_24h || 0), 0) || 0,
    totalTasks24h: agents?.reduce((sum, a) => sum + (a.tasks_24h || 0), 0) || 0,
  }

  const isLoading = agentsLoading || tasksLoading

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Agent Tracking"
        description="Monitor your AI agents in real-time"
        icon={Cpu}
        iconColor="purple"
        action={
          <div className="flex items-center gap-3">
            {/* Auto-refresh toggle */}
            <button
              onClick={() => setIsAutoRefresh(!isAutoRefresh)}
              className={cn(
                'flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all',
                isAutoRefresh
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-slate-800/50 text-slate-400 border border-slate-700/50 hover:border-slate-600'
              )}
            >
              <RefreshCw size={14} className={isAutoRefresh ? 'animate-spin' : ''} />
              {isAutoRefresh ? 'Live' : 'Paused'}
            </button>
            {/* Manual refresh */}
            <button
              onClick={refreshAll}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/30 transition-all text-sm"
            >
              <RefreshCw size={14} />
              Refresh
            </button>
          </div>
        }
      />

      {/* Stats Grid */}
      <StatsGrid columns={5}>
        <StatCard
          label="Active Agents"
          value={`${totals.activeAgents}/${totals.agents}`}
          icon={Cpu}
          accent="cyan"
        />
        <StatCard
          label="Running Tasks"
          value={totals.activeTasks}
          icon={Play}
          accent="purple"
        />
        <StatCard
          label="Tasks (24h)"
          value={totals.totalTasks24h}
          icon={Layers}
          accent="emerald"
        />
        <StatCard
          label="Cost (24h)"
          value={totals.totalCost24h.toFixed(2)}
          icon={DollarSign}
          prefix="$"
          accent="amber"
        />
        <StatCard
          label="System Status"
          value="Operational"
          icon={Activity}
          accent="emerald"
        />
      </StatsGrid>

      {/* Tabs */}
      <div className="border-b border-slate-800/80">
        <div className="flex gap-1">
          {(['overview', 'tasks', 'activity'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab
                  ? 'text-cyan-400 border-cyan-400'
                  : 'text-slate-400 border-transparent hover:text-white hover:border-slate-600'
              )}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Agents List */}
          <Card variant="default">
            <CardHeader>
              Agents
              <span className="text-xs text-slate-500 font-normal ml-2">
                {totals.agents} registered
              </span>
            </CardHeader>
            <CardContent className="p-0">
              {agentsLoading ? (
                <ListSkeleton count={4} />
              ) : !agents || agents.length === 0 ? (
                <EmptyState
                  title="No agents registered"
                  description="Agents will appear here when they connect to the system"
                />
              ) : (
                <div className="divide-y divide-slate-800/50">
                  {agents.map((agent) => (
                    <div key={agent.id}>
                      <div
                        onClick={() =>
                          setSelectedAgent(selectedAgent === agent.id ? null : agent.id)
                        }
                        className={cn(
                          'flex items-center justify-between p-4 cursor-pointer transition-colors',
                          selectedAgent === agent.id
                            ? 'bg-cyan-500/5'
                            : 'hover:bg-slate-800/30'
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <div className="text-2xl">
                            {AGENT_TYPE_ICONS[agent.agent_type] || '🤖'}
                          </div>
                          <div>
                            <div className="font-medium text-white">{agent.name}</div>
                            <div className="text-xs text-slate-500">{agent.agent_type}</div>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <StatusDot
                            status={
                              agent.status === 'active'
                                ? 'active'
                                : agent.status === 'paused'
                                ? 'paused'
                                : 'idle'
                            }
                            pulse={agent.status === 'active'}
                          />
                          <span className="text-xs text-slate-500">
                            {agent.active_tasks || 0} active
                          </span>
                          {selectedAgent === agent.id ? (
                            <ChevronDown size={16} className="text-slate-400" />
                          ) : (
                            <ChevronRight size={16} className="text-slate-400" />
                          )}
                        </div>
                      </div>

                      {/* Expanded Details */}
                      {selectedAgent === agent.id && (
                        <div className="px-4 pb-4">
                          <div className="grid grid-cols-3 gap-4 p-3 bg-slate-800/30 rounded-lg text-sm">
                            <div>
                              <div className="text-slate-500 text-xs">Completed</div>
                              <div className="font-mono text-slate-200">
                                {agent.total_tasks_completed.toLocaleString()}
                              </div>
                            </div>
                            <div>
                              <div className="text-slate-500 text-xs">Failed</div>
                              <div className="font-mono text-rose-400">
                                {agent.total_tasks_failed}
                              </div>
                            </div>
                            <div>
                              <div className="text-slate-500 text-xs">Total Cost</div>
                              <div className="font-mono text-cyan-400">
                                ${agent.total_cost_usd.toFixed(2)}
                              </div>
                            </div>
                            <div>
                              <div className="text-slate-500 text-xs">24h Tasks</div>
                              <div className="font-mono text-slate-200">
                                {agent.tasks_24h || 0}
                              </div>
                            </div>
                            <div>
                              <div className="text-slate-500 text-xs">24h Cost</div>
                              <div className="font-mono text-cyan-400">
                                ${(agent.cost_24h || 0).toFixed(2)}
                              </div>
                            </div>
                            <div>
                              <div className="text-slate-500 text-xs">Last Seen</div>
                              <div className="font-mono text-slate-400 text-xs">
                                {agent.last_seen
                                  ? new Date(agent.last_seen).toLocaleTimeString()
                                  : 'Never'}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Active Tasks */}
          <Card variant="default">
            <CardHeader
              action={
                <span className="text-xs bg-cyan-500/10 text-cyan-400 px-2 py-1 rounded">
                  {activeTasks?.length || 0} running
                </span>
              }
            >
              Active Tasks
            </CardHeader>
            <CardContent className="p-0">
              {tasksLoading ? (
                <ListSkeleton count={4} />
              ) : !activeTasks || activeTasks.length === 0 ? (
                <EmptyState
                  title="No active tasks"
                  description="Running tasks will appear here in real-time"
                />
              ) : (
                <div className="divide-y divide-slate-800/50 max-h-[480px] overflow-y-auto">
                  {activeTasks.map((task) => {
                    const statusConfig = TASK_STATUS_CONFIG[task.status] || TASK_STATUS_CONFIG.pending
                    const StatusIcon = statusConfig.icon
                    return (
                      <div key={task.id} className="p-4">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1 min-w-0 mr-3">
                            <div className="font-medium text-white truncate">
                              {task.title || 'Untitled Task'}
                            </div>
                            <div className="text-xs text-slate-500 flex items-center gap-2 mt-0.5">
                              <span>{(task as any).agent_name || 'Unknown Agent'}</span>
                              {task.model && (
                                <>
                                  <span className="text-slate-600">•</span>
                                  <span className="font-mono">{task.model}</span>
                                </>
                              )}
                            </div>
                          </div>
                          <span
                            className={cn(
                              'text-xs px-2 py-1 rounded flex items-center gap-1',
                              statusConfig.color
                            )}
                          >
                            <StatusIcon size={12} />
                            {task.status}
                          </span>
                        </div>

                        {/* Progress Bar */}
                        <div className="mb-3">
                          <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
                            <span>Progress</span>
                            <span className="font-mono">{task.progress_percent}%</span>
                          </div>
                          <ProgressBar
                            value={task.progress_percent}
                            variant={task.status === 'running' ? 'default' : 'success'}
                            size="md"
                          />
                        </div>

                        {/* Metrics */}
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          <span className="flex items-center gap-1">
                            <Timer size={12} />
                            {task.duration_ms
                              ? `${Math.round(task.duration_ms / 1000)}s`
                              : task.started_at
                              ? `${Math.round((Date.now() - new Date(task.started_at).getTime()) / 1000)}s`
                              : 'pending'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Zap size={12} />
                            <span className="font-mono">
                              {(task.input_tokens + task.output_tokens).toLocaleString()} tokens
                            </span>
                          </span>
                          <span className="flex items-center gap-1">
                            <DollarSign size={12} />
                            <span className="font-mono text-cyan-400">
                              ${task.cost_usd.toFixed(4)}
                            </span>
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'tasks' && (
        <Card variant="default">
          <CardHeader>All Tasks</CardHeader>
          <CardContent className="p-0">
            {!agentTasks || agentTasks.length === 0 ? (
              <EmptyState
                title="No tasks to display"
                description="Select an agent from the Overview tab to view their tasks"
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="bg-slate-800/50">
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                        Task
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                        Agent
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                        Status
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                        Progress
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                        Cost
                      </th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                        Tokens
                      </th>
                      <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                        Duration
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {agentTasks.map((task) => {
                      const statusConfig = TASK_STATUS_CONFIG[task.status] || TASK_STATUS_CONFIG.pending
                      const StatusIcon = statusConfig.icon
                      return (
                        <tr
                          key={task.id}
                          className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                        >
                          <td className="py-3 px-4">
                            <div className="font-medium text-slate-200 truncate max-w-[200px]">
                              {task.title || 'Untitled'}
                            </div>
                            <div className="text-xs text-slate-500">
                              {task.task_type || 'general'}
                            </div>
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-400">
                            {(task as any).agents?.name || 'Unknown'}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={cn(
                                'text-xs px-2 py-1 rounded inline-flex items-center gap-1',
                                statusConfig.color
                              )}
                            >
                              <StatusIcon size={12} />
                              {task.status}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <ProgressBar
                                value={task.progress_percent}
                                size="sm"
                                className="w-16"
                              />
                              <span className="text-xs text-slate-500 font-mono">
                                {task.progress_percent}%
                              </span>
                            </div>
                          </td>
                          <td className="py-3 px-4 text-right text-sm font-mono text-cyan-400">
                            ${task.cost_usd.toFixed(4)}
                          </td>
                          <td className="py-3 px-4 text-right text-sm font-mono text-slate-300">
                            {(task.input_tokens + task.output_tokens).toLocaleString()}
                          </td>
                          <td className="py-3 px-4 text-sm text-slate-400">
                            {task.duration_ms
                              ? `${(task.duration_ms / 1000).toFixed(1)}s`
                              : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 'activity' && (
        <Card variant="default">
          <CardContent className="py-12">
            <EmptyState
              title="Activity Feed Coming Soon"
              description="Track task events, errors, and milestones in real-time"
              icon={Activity}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
