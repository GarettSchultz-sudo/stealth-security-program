'use client'

import { useState } from 'react'
import {
  Shield,
  Clock,
  Bell,
  BellOff,
  Play,
  Pause,
  Trash2,
  RefreshCw,
  Plus,
  CheckCircle,
  AlertTriangle,
  XCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TrustScoreGauge } from './trust-score-gauge'
import { StatusBadge, RiskBadge } from './risk-badge'

export interface MonitoredSkill {
  id: string
  skill_id: string
  skill_name: string
  status: 'active' | 'paused'
  check_interval_seconds: number
  last_check_at: string | null
  next_check_at: string | null
  baseline_trust_score: number | null
  current_trust_score: number | null
  findings_detected: number
  alerts_sent: number
  last_change?: {
    type: 'improved' | 'degraded' | 'unchanged'
    score_delta: number
  }
}

interface MonitoredSkillsPanelProps {
  skills: MonitoredSkill[]
  onPause?: (id: string) => void
  onResume?: (id: string) => void
  onRemove?: (id: string) => void
  onScanNow?: (id: string) => void
  onAddSkill?: () => void
  className?: string
}

export function MonitoredSkillsPanel({
  skills,
  onPause,
  onResume,
  onRemove,
  onScanNow,
  onAddSkill,
  className,
}: MonitoredSkillsPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const formatInterval = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`
    return `${Math.floor(seconds / 86400)}d`
  }

  const formatNextCheck = (dateStr: string | null) => {
    if (!dateStr) return 'Not scheduled'
    const date = new Date(dateStr)
    const now = new Date()
    const diff = date.getTime() - now.getTime()

    if (diff < 0) return 'Overdue'
    if (diff < 60000) return 'In less than a minute'
    if (diff < 3600000) return `In ${Math.ceil(diff / 60000)} minutes`
    if (diff < 86400000) return `In ${Math.ceil(diff / 3600000)} hours`
    return date.toLocaleDateString()
  }

  const getChangeIndicator = (change?: MonitoredSkill['last_change']) => {
    if (!change) return null

    if (change.type === 'improved') {
      return (
        <div className="flex items-center gap-1 text-emerald-400 text-xs">
          <CheckCircle size={12} />
          <span>+{change.score_delta} pts</span>
        </div>
      )
    }
    if (change.type === 'degraded') {
      return (
        <div className="flex items-center gap-1 text-red-400 text-xs">
          <AlertTriangle size={12} />
          <span>-{Math.abs(change.score_delta)} pts</span>
        </div>
      )
    }
    return (
      <div className="flex items-center gap-1 text-slate-500 text-xs">
        <span>No change</span>
      </div>
    )
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield size={18} className="text-cyan-400" />
          <h3 className="text-sm font-medium text-white">Monitored Skills</h3>
          <span className="px-2 py-0.5 rounded-full bg-slate-700/50 text-xs text-slate-400">
            {skills.length}
          </span>
        </div>
        {onAddSkill && (
          <button
            onClick={onAddSkill}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 text-sm hover:bg-cyan-500/20 transition-colors"
          >
            <Plus size={14} />
            Add
          </button>
        )}
      </div>

      {/* Skills List */}
      {skills.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-slate-500 border border-dashed border-slate-700 rounded-xl">
          <Shield size={32} className="mb-2 opacity-50" />
          <p className="text-sm">No skills being monitored</p>
          <p className="text-xs mt-1">Add a skill to track its security over time</p>
        </div>
      ) : (
        <div className="space-y-2">
          {skills.map((skill) => (
            <div
              key={skill.id}
              className={cn(
                'border rounded-xl overflow-hidden transition-all duration-200',
                skill.status === 'active'
                  ? 'border-slate-700/50 bg-slate-800/30'
                  : 'border-slate-800 bg-slate-900/50'
              )}
            >
              {/* Main Row */}
              <div
                className="flex items-center gap-4 p-4 cursor-pointer hover:bg-slate-800/20"
                onClick={() => setExpandedId(expandedId === skill.id ? null : skill.id)}
              >
                {/* Trust Score Gauge */}
                <div className="flex-shrink-0">
                  <TrustScoreGauge
                    score={skill.current_trust_score}
                    size="md"
                    animated={false}
                  />
                </div>

                {/* Skill Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white truncate">
                      {skill.skill_name}
                    </span>
                    {skill.status === 'paused' && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-700 text-slate-400">
                        Paused
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-slate-500 font-mono truncate">
                      {skill.skill_id}
                    </span>
                    {skill.last_change && getChangeIndicator(skill.last_change)}
                  </div>
                </div>

                {/* Status Indicators */}
                <div className="flex items-center gap-4">
                  {/* Findings */}
                  {skill.findings_detected > 0 && (
                    <div className="flex items-center gap-1 text-amber-400">
                      <AlertTriangle size={14} />
                      <span className="text-xs">{skill.findings_detected}</span>
                    </div>
                  )}

                  {/* Next Check */}
                  <div className="hidden sm:flex items-center gap-1 text-slate-500">
                    <Clock size={14} />
                    <span className="text-xs">{formatNextCheck(skill.next_check_at)}</span>
                  </div>

                  {/* Alerts */}
                  {skill.alerts_sent > 0 && (
                    <div className="flex items-center gap-1 text-slate-500">
                      <Bell size={14} />
                      <span className="text-xs">{skill.alerts_sent}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Expanded Details */}
              {expandedId === skill.id && (
                <div className="border-t border-slate-700/50 bg-slate-900/30 p-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <span className="text-xs text-slate-500 block mb-1">Check Interval</span>
                      <span className="text-sm text-white">{formatInterval(skill.check_interval_seconds)}</span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 block mb-1">Baseline Score</span>
                      <span className="text-sm text-white">{skill.baseline_trust_score ?? '—'}</span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 block mb-1">Last Check</span>
                      <span className="text-sm text-white">
                        {skill.last_check_at ? new Date(skill.last_check_at).toLocaleString() : 'Never'}
                      </span>
                    </div>
                    <div>
                      <span className="text-xs text-slate-500 block mb-1">Alerts Sent</span>
                      <span className="text-sm text-white">{skill.alerts_sent}</span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                    {skill.status === 'active' ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onPause?.(skill.id)
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-slate-700/50 text-slate-300 hover:bg-slate-700 transition-colors"
                      >
                        <Pause size={12} />
                        Pause
                      </button>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onResume?.(skill.id)
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                      >
                        <Play size={12} />
                        Resume
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onScanNow?.(skill.id)
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors"
                    >
                      <RefreshCw size={12} />
                      Scan Now
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onRemove?.(skill.id)
                      }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors ml-auto"
                    >
                      <Trash2 size={12} />
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
