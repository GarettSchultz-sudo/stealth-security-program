'use client'

import { useState, useMemo } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import {
  ExternalLink,
  Clock,
  ChevronUp,
  ChevronDown,
  Search,
  Filter,
  MoreHorizontal,
  RefreshCw,
  Trash2,
  Eye,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { StatusBadge } from './risk-badge'
import { TrustScoreGauge } from './trust-score-gauge'

const tableRowVariants = cva(
  'group border-b border-slate-800/50 transition-colors hover:bg-slate-800/30',
  {
    variants: {
      selected: {
        true: 'bg-cyan-500/5',
        false: '',
      },
    },
  }
)

export interface ScanRecord {
  id: string
  target_type: string
  target: string
  profile: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  trust_score: number | null
  findings_critical: number
  findings_high: number
  findings_medium: number
  findings_low: number
  created_at: string
  completed_at: string | null
  duration_ms: number | null
}

type SortField = 'created_at' | 'trust_score' | 'findings' | 'duration_ms'
type SortDirection = 'asc' | 'desc'

interface ScanHistoryProps {
  scans: ScanRecord[]
  onViewScan: (scanId: string) => void
  onRefresh?: () => void
  isLoading?: boolean
  className?: string
}

export function ScanHistory({
  scans,
  onViewScan,
  onRefresh,
  isLoading = false,
  className,
}: ScanHistoryProps) {
  const [sortField, setSortField] = useState<SortField>('created_at')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const filteredAndSortedScans = useMemo(() => {
    let result = [...scans]

    // Filter by status
    if (filterStatus !== 'all') {
      result = result.filter(scan => scan.status === filterStatus)
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      result = result.filter(scan =>
        scan.target.toLowerCase().includes(query) ||
        scan.target_type.toLowerCase().includes(query)
      )
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0

      switch (sortField) {
        case 'created_at':
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          break
        case 'trust_score':
          comparison = (a.trust_score ?? 0) - (b.trust_score ?? 0)
          break
        case 'findings':
          const aTotal = a.findings_critical + a.findings_high + a.findings_medium + a.findings_low
          const bTotal = b.findings_critical + b.findings_high + b.findings_medium + b.findings_low
          comparison = aTotal - bTotal
          break
        case 'duration_ms':
          comparison = (a.duration_ms ?? 0) - (b.duration_ms ?? 0)
          break
      }

      return sortDirection === 'asc' ? comparison : -comparison
    })

    return result
  }, [scans, filterStatus, searchQuery, sortField, sortDirection])

  const formatDuration = (ms: number | null) => {
    if (!ms) return '—'
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    return `${(ms / 60000).toFixed(1)}m`
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()

    if (diff < 60000) return 'Just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
    return date.toLocaleDateString()
  }

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null
    return sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header with filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search scans..."
            className="w-full bg-slate-800/50 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50"
          />
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-slate-500" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>

        {/* Refresh button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-2 bg-slate-800/50 border border-slate-700 rounded-lg text-sm text-slate-400 hover:text-white hover:border-slate-600 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
            Refresh
          </button>
        )}
      </div>

      {/* Table */}
      <div className="border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-slate-800/50 border-b border-slate-700">
                <th className="px-4 py-3 text-left">
                  <button
                    onClick={() => handleSort('created_at')}
                    className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-white transition-colors"
                  >
                    <Clock size={14} />
                    Date
                    <SortIcon field="created_at" />
                  </button>
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Target</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Profile</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400">Status</th>
                <th className="px-4 py-3 text-center">
                  <button
                    onClick={() => handleSort('trust_score')}
                    className="flex items-center justify-center gap-1 text-xs font-medium text-slate-400 hover:text-white transition-colors mx-auto"
                  >
                    Score
                    <SortIcon field="trust_score" />
                  </button>
                </th>
                <th className="px-4 py-3 text-center">
                  <button
                    onClick={() => handleSort('findings')}
                    className="flex items-center justify-center gap-1 text-xs font-medium text-slate-400 hover:text-white transition-colors mx-auto"
                  >
                    Findings
                    <SortIcon field="findings" />
                  </button>
                </th>
                <th className="px-4 py-3 text-center">
                  <button
                    onClick={() => handleSort('duration_ms')}
                    className="flex items-center justify-center gap-1 text-xs font-medium text-slate-400 hover:text-white transition-colors mx-auto"
                  >
                    Duration
                    <SortIcon field="duration_ms" />
                  </button>
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredAndSortedScans.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center">
                    <div className="flex flex-col items-center gap-2 text-slate-500">
                      <Search size={24} />
                      <span className="text-sm">No scans found</span>
                      {searchQuery && (
                        <span className="text-xs">Try adjusting your search or filters</span>
                      )}
                    </div>
                  </td>
                </tr>
              ) : (
                filteredAndSortedScans.map((scan) => (
                  <tr
                    key={scan.id}
                    className={tableRowVariants({ selected: selectedId === scan.id })}
                    onClick={() => setSelectedId(scan.id === selectedId ? null : scan.id)}
                  >
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-300">{formatDate(scan.created_at)}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-sm text-white font-medium truncate max-w-[200px]">
                          {scan.target}
                        </span>
                        <span className="text-xs text-slate-500 capitalize">
                          {scan.target_type.replace('_', ' ')}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-slate-300 capitalize">{scan.profile}</span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={scan.status} size="sm" />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-center">
                        <TrustScoreGauge score={scan.trust_score} size="sm" animated={false} />
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-center gap-1">
                        {scan.findings_critical > 0 && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">
                            {scan.findings_critical}
                          </span>
                        )}
                        {scan.findings_high > 0 && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400">
                            {scan.findings_high}
                          </span>
                        )}
                        {scan.findings_medium > 0 && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400">
                            {scan.findings_medium}
                          </span>
                        )}
                        {scan.findings_low > 0 && (
                          <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                            {scan.findings_low}
                          </span>
                        )}
                        {scan.findings_critical === 0 &&
                          scan.findings_high === 0 &&
                          scan.findings_medium === 0 &&
                          scan.findings_low === 0 && (
                          <span className="text-xs text-slate-500">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className="text-sm text-slate-400">{formatDuration(scan.duration_ms)}</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onViewScan(scan.id)
                          }}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors"
                          title="View details"
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          onClick={(e) => e.stopPropagation()}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700/50 transition-colors"
                          title="More options"
                        >
                          <MoreHorizontal size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer with count */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          Showing {filteredAndSortedScans.length} of {scans.length} scans
        </span>
      </div>
    </div>
  )
}
