'use client'

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import {
  FileText,
  RefreshCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Cpu,
  DollarSign,
  Filter,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Card, CardHeader, CardContent, PageHeader, EmptyState, Button, Input, Select, IconButton } from '@/components/ui'

interface RequestLog {
  id: string
  created_at: string
  model: string
  provider: string
  method: string
  path: string
  status_code: number
  latency_ms: number
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cost_usd: number
  error_message: string | null
  metadata: Record<string, unknown> | null
}

interface LogsResponse {
  logs: RequestLog[]
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
  }
}

function getStatusIcon(statusCode: number | null) {
  if (!statusCode) return <AlertCircle size={14} className="text-slate-400" />
  if (statusCode >= 200 && statusCode < 300) {
    return <CheckCircle size={14} className="text-emerald-400" />
  }
  if (statusCode >= 400 && statusCode < 500) {
    return <AlertCircle size={14} className="text-amber-400" />
  }
  return <XCircle size={14} className="text-rose-400" />
}

function getStatusColor(statusCode: number | null) {
  if (!statusCode) return 'text-slate-400'
  if (statusCode >= 200 && statusCode < 300) return 'text-emerald-400'
  if (statusCode >= 400 && statusCode < 500) return 'text-amber-400'
  return 'text-rose-400'
}

function formatTimestamp(dateStr: string) {
  const date = new Date(dateStr)
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatDuration(ms: number | null) {
  if (!ms) return '-'
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export default function LogsPage() {
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({
    model: '',
    status: '',
    startDate: '',
    endDate: '',
  })
  const [showFilters, setShowFilters] = useState(false)

  // Fetch logs
  const { data, isLoading, refetch, isFetching } = useQuery<LogsResponse>({
    queryKey: ['logs', page, filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.set('page', page.toString())
      params.set('limit', '50')
      if (filters.model) params.set('model', filters.model)
      if (filters.status) params.set('status', filters.status)
      if (filters.startDate) params.set('startDate', filters.startDate)
      if (filters.endDate) params.set('endDate', filters.endDate)

      const response = await fetch(`/api/logs?${params.toString()}`)
      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Unauthorized')
        }
        throw new Error('Failed to fetch logs')
      }
      return response.json()
    },
  })

  const logs = data?.logs || []
  const pagination = data?.pagination || { page: 1, limit: 50, total: 0, totalPages: 0 }

  const handleFilterChange = (key: string, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
    setPage(1) // Reset to first page when filters change
  }

  const clearFilters = () => {
    setFilters({ model: '', status: '', startDate: '', endDate: '' })
    setPage(1)
  }

  const hasActiveFilters = filters.model || filters.status || filters.startDate || filters.endDate

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="API Logs"
        description="View and analyze your API request history"
        icon={FileText}
        iconColor="cyan"
        action={
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={() => refetch()}
            loading={isFetching}
          >
            Refresh
          </Button>
        }
      />

      {/* Filters */}
      <Card variant="default">
        <CardContent className="py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                icon={Filter}
                onClick={() => setShowFilters(!showFilters)}
                className={cn(showFilters && 'text-cyan-400')}
              >
                Filters
              </Button>
              {hasActiveFilters && (
                <span className="text-xs text-cyan-400 bg-cyan-400/10 px-2 py-1 rounded">
                  Active
                </span>
              )}
            </div>
            {hasActiveFilters && (
              <Button variant="ghost" onClick={clearFilters} className="text-sm text-slate-400">
                Clear filters
              </Button>
            )}
          </div>

          {showFilters && (
            <div className="mt-4 pt-4 border-t border-slate-700/50 grid grid-cols-1 md:grid-cols-4 gap-4">
              <Input
                label="Model"
                placeholder="e.g., claude-3-opus"
                value={filters.model}
                onChange={(e) => handleFilterChange('model', e.target.value)}
              />
              <Select
                label="Status Code"
                value={filters.status}
                onChange={(value) => handleFilterChange('status', value)}
                options={[
                  { value: '', label: 'All Statuses' },
                  { value: '200', label: '200 OK' },
                  { value: '201', label: '201 Created' },
                  { value: '400', label: '400 Bad Request' },
                  { value: '401', label: '401 Unauthorized' },
                  { value: '429', label: '429 Rate Limited' },
                  { value: '500', label: '500 Server Error' },
                ]}
              />
              <Input
                label="Start Date"
                type="datetime-local"
                value={filters.startDate}
                onChange={(e) => handleFilterChange('startDate', e.target.value)}
              />
              <Input
                label="End Date"
                type="datetime-local"
                value={filters.endDate}
                onChange={(e) => handleFilterChange('endDate', e.target.value)}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stats Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card variant="default" className="p-4">
          <div className="text-sm text-slate-400">Total Requests</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {pagination.total.toLocaleString()}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Cpu size={14} />
            Total Tokens
          </div>
          <div className="text-2xl font-bold font-mono text-purple-400 mt-1">
            {logs.reduce((sum, log) => sum + (log.total_tokens || 0), 0).toLocaleString()}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <DollarSign size={14} />
            Page Cost
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-1">
            ${logs.reduce((sum, log) => sum + (log.cost_usd || 0), 0).toFixed(4)}
          </div>
        </Card>
        <Card variant="default" className="p-4">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Clock size={14} />
            Avg Latency
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">
            {logs.length > 0
              ? formatDuration(logs.reduce((sum, log) => sum + (log.latency_ms || 0), 0) / logs.length)
              : '-'}
          </div>
        </Card>
      </div>

      {/* Logs Table */}
      <Card variant="default">
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-cyan-400" />
            Request Logs
          </div>
          <span className="text-xs text-slate-500">
            Page {pagination.page} of {pagination.totalPages || 1}
          </span>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-8 text-center text-slate-500">Loading...</div>
          ) : logs.length === 0 ? (
            <EmptyState
              title="No logs found"
              description={hasActiveFilters ? "Try adjusting your filters" : "Make API requests to see logs here"}
              action={
                hasActiveFilters ? (
                  <Button variant="secondary" onClick={clearFilters}>
                    Clear Filters
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="bg-slate-800/50">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Time
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Status
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Model
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Tokens
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Cost
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-slate-400 border-b border-slate-700/50">
                      Latency
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr
                      key={log.id}
                      className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-3 px-4">
                        <div className="text-sm text-slate-300">
                          {formatTimestamp(log.created_at)}
                        </div>
                        <div className="text-xs text-slate-500 font-mono">
                          {log.method} {log.path?.substring(0, 30)}
                          {log.path && log.path.length > 30 && '...'}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(log.status_code)}
                          <span className={cn('text-sm font-mono', getStatusColor(log.status_code))}>
                            {log.status_code || '-'}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <div className="p-1 bg-purple-500/10 rounded">
                            <Cpu size={12} className="text-purple-400" />
                          </div>
                          <div>
                            <div className="text-sm text-white font-medium">
                              {log.model || 'unknown'}
                            </div>
                            <div className="text-xs text-slate-500">
                              {log.provider || '-'}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-sm font-mono text-slate-300">
                          {log.total_tokens?.toLocaleString() || '-'}
                        </div>
                        <div className="text-xs text-slate-500">
                          {log.prompt_tokens || 0} + {log.completion_tokens || 0}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="text-sm font-mono text-emerald-400">
                          ${(log.cost_usd || 0).toFixed(6)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="text-sm font-mono text-slate-400">
                          {formatDuration(log.latency_ms)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {pagination.totalPages > 1 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-400">
            Showing {((page - 1) * pagination.limit) + 1} to {Math.min(page * pagination.limit, pagination.total)} of {pagination.total} results
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              icon={ChevronLeft}
              onClick={() => setPage(page - 1)}
              disabled={page <= 1 || isFetching}
            >
              Previous
            </Button>
            <div className="text-sm text-slate-400 font-mono px-3">
              {page} / {pagination.totalPages}
            </div>
            <Button
              variant="secondary"
              icon={ChevronRight}
              onClick={() => setPage(page + 1)}
              disabled={page >= pagination.totalPages || isFetching}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
