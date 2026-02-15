'use client'

import { use } from 'react'
import { useQuery } from '@tanstack/react-query'
import { createClient } from '@supabase/supabase-js'
import Link from 'next/link'
import {
  ArrowLeft, Activity, Cpu, Zap, Clock, CheckCircle, XCircle,
  Play, Pause, RefreshCw, TrendingUp, DollarSign, Timer, Layers,
  AlertCircle, BarChart2
} from 'lucide-react'

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
  )
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700',
  running: 'bg-blue-100 text-blue-700',
  paused: 'bg-gray-100 text-gray-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

export default function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  // Fetch agent details
  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ['agent', id],
    queryFn: async () => {
      const supabase = getSupabase()
      const { data, error } = await supabase
        .from('agent_utilization')
        .select('*')
        .eq('id', id)
        .single()

      if (error) throw error
      return data
    },
    refetchInterval: 5000,
  })

  // Fetch agent tasks
  const { data: tasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['agent-tasks', id],
    queryFn: async () => {
      const supabase = getSupabase()
      const { data, error } = await supabase
        .from('agent_tasks')
        .select('*')
        .eq('agent_id', id)
        .order('created_at', { ascending: false })
        .limit(50)

      if (error) throw error
      return data || []
    },
    refetchInterval: 3000,
  })

  // Fetch recent events
  const { data: events } = useQuery({
    queryKey: ['agent-events', id],
    queryFn: async () => {
      const supabase = getSupabase()
      const { data, error } = await supabase
        .from('task_events')
        .select('*')
        .eq('agent_id', id)
        .order('recorded_at', { ascending: false })
        .limit(20)

      if (error) throw error
      return data || []
    },
  })

  if (agentLoading) {
    return (
      <div className="p-8 text-center text-gray-500">
        Loading agent details...
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="p-8 text-center text-gray-500">
        Agent not found
        <Link href="/agents" className="block mt-4 text-blue-500 hover:underline">
          ← Back to Agents
        </Link>
      </div>
    )
  }

  const successRate = agent.total_tasks_completed + agent.total_tasks_failed > 0
    ? ((agent.total_tasks_completed / (agent.total_tasks_completed + agent.total_tasks_failed)) * 100).toFixed(1)
    : 'N/A'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/agents" className="text-gray-500 hover:text-gray-700">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{agent.name}</h1>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span className={`w-2 h-2 rounded-full ${
                agent.status === 'active' ? 'bg-green-500' :
                agent.status === 'paused' ? 'bg-yellow-500' : 'bg-gray-400'
              }`} />
              <span className="capitalize">{agent.status}</span>
              <span>•</span>
              <span>{agent.agent_type}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">
            Last seen: {agent.last_seen ? new Date(agent.last_seen).toLocaleString() : 'Never'}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <Play size={14} />
            Active Tasks
          </div>
          <div className="text-2xl font-bold text-blue-600">{agent.active_tasks || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <Layers size={14} />
            24h Tasks
          </div>
          <div className="text-2xl font-bold">{agent.tasks_24h || 0}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <DollarSign size={14} />
            24h Cost
          </div>
          <div className="text-2xl font-bold">${(agent.cost_24h || 0).toFixed(2)}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <CheckCircle size={14} />
            Completed
          </div>
          <div className="text-2xl font-bold text-green-600">{agent.total_tasks_completed}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <XCircle size={14} />
            Failed
          </div>
          <div className="text-2xl font-bold text-red-600">{agent.total_tasks_failed}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex items-center gap-2 text-gray-500 text-sm mb-1">
            <TrendingUp size={14} />
            Success Rate
          </div>
          <div className="text-2xl font-bold">{successRate}%</div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tasks List */}
        <div className="lg:col-span-2 bg-white rounded-lg shadow">
          <div className="p-4 border-b flex items-center justify-between">
            <h2 className="font-semibold">Recent Tasks</h2>
            <span className="text-xs text-gray-500">{tasks?.length || 0} tasks</span>
          </div>
          <div className="divide-y max-h-[600px] overflow-y-auto">
            {tasksLoading ? (
              <div className="p-4 text-center text-gray-500">Loading...</div>
            ) : tasks?.length === 0 ? (
              <div className="p-4 text-center text-gray-500">No tasks yet</div>
            ) : (
              tasks?.map(task => (
                <div key={task.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{task.title}</div>
                      <div className="text-xs text-gray-500">
                        {task.task_type || 'general'} • {task.model || 'no model'}
                      </div>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded ${STATUS_COLORS[task.status]}`}>
                      {task.status}
                    </span>
                  </div>

                  <div className="mb-2">
                    <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                      <span>Progress</span>
                      <span>{task.progress_percent}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all ${
                          task.status === 'completed' ? 'bg-green-500' :
                          task.status === 'failed' ? 'bg-red-500' : 'bg-blue-500'
                        }`}
                        style={{ width: `${task.progress_percent}%` }}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Clock size={12} />
                      {task.created_at ? new Date(task.created_at).toLocaleTimeString() : '-'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Timer size={12} />
                      {task.duration_ms ? `${(task.duration_ms / 1000).toFixed(1)}s` : '-'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Zap size={12} />
                      {(task.input_tokens + task.output_tokens).toLocaleString()} tokens
                    </span>
                    <span className="flex items-center gap-1">
                      <DollarSign size={12} />
                      ${task.cost_usd?.toFixed(4) || '0.0000'}
                    </span>
                  </div>

                  {task.error_message && (
                    <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-600 flex items-start gap-2">
                      <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                      {task.error_message}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Agent Info */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-4">Agent Info</h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">ID</dt>
                <dd className="font-mono text-xs">{id}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Type</dt>
                <dd className="capitalize">{agent.agent_type}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Total Requests</dt>
                <dd>{agent.total_requests?.toLocaleString() || 0}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Total Tokens</dt>
                <dd>{agent.total_tokens?.toLocaleString() || 0}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Total Cost</dt>
                <dd className="font-medium">${(agent.total_cost_usd || 0).toFixed(2)}</dd>
              </div>
            </dl>
          </div>

          {/* Recent Events */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-4">Recent Events</h3>
            <div className="space-y-2 text-sm max-h-64 overflow-y-auto">
              {events?.length === 0 ? (
                <div className="text-gray-500 text-center py-4">No events yet</div>
              ) : (
                events?.map(event => (
                  <div key={event.id} className="flex items-start gap-2">
                    <div className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${
                      event.event_type === 'completed' ? 'bg-green-500' :
                      event.event_type === 'failed' ? 'bg-red-500' :
                      event.event_type === 'started' ? 'bg-blue-500' :
                      'bg-gray-400'
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className="capitalize">{event.event_type}</div>
                      <div className="text-xs text-gray-500">
                        {event.recorded_at ? new Date(event.recorded_at).toLocaleString() : '-'}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
