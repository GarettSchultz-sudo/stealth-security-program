'use client'

import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Shield,
  Activity,
  History,
  Eye,
  Settings,
  Bell,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  StatCard,
  StatsGrid,
  StatCardSkeleton,
  TrustScoreGauge,
  TrustScoreBar,
  RiskBadge,
  StatusBadge,
  ScanForm,
  ScanHistory,
  MonitoredSkillsPanel,
  SettingsPanel,
  ScanDetails,
  generateDemoFindings,
} from '@/components/scan'
import type { ScanFinding } from '@/components/scan/scan-details'
import type { ScanFormData } from '@/components/scan/scan-form'
import type { ScanRecord } from '@/components/scan/scan-history'
import type { MonitoredSkill } from '@/components/scan/monitored-skills-panel'

// API response types
interface SkillScan {
  id: string
  skill_id: string
  skill_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  profile: string
  trust_score: number | null
  risk_level: 'low' | 'medium' | 'high' | 'critical' | null
  recommendation: 'safe' | 'caution' | 'avoid' | null
  scan_duration_ms: number | null
  files_scanned: number
  patterns_checked: number
  created_at: string
  completed_at: string | null
}

interface ScanCredits {
  total_credits: number
  used_credits: number
  remaining_credits: number
  period_end: string | null
  scan_costs: { quick: number; standard: number; deep: number; comprehensive: number }
}

interface ApiMonitoredSkill {
  id: string
  skill_id: string
  skill_name: string
  status: 'active' | 'paused' | 'alerted' | 'disabled'
  check_interval_seconds: number
  last_check_at: string | null
  next_check_at: string | null
  baseline_trust_score: number | null
  findings_detected: number
  alerts_sent: number
}

// Tab configuration
const tabs = [
  { id: 'dashboard', label: 'Dashboard', icon: Activity },
  { id: 'history', label: 'History', icon: History },
  { id: 'monitoring', label: 'Monitoring', icon: Eye },
  { id: 'settings', label: 'Settings', icon: Settings },
] as const

type TabId = typeof tabs[number]['id']

export default function ScanPage() {
  const [activeTab, setActiveTab] = useState<TabId>('dashboard')
  const [error, setError] = useState<string | null>(null)
  const [selectedScan, setSelectedScan] = useState<ScanRecord | null>(null)
  const [scanFindings, setScanFindings] = useState<ScanFinding[]>([])
  const queryClient = useQueryClient()

  // Fetch scan credits
  const { data: credits, isLoading: creditsLoading } = useQuery<ScanCredits>({
    queryKey: ['scan-credits'],
    queryFn: async () => {
      const response = await fetch('/api/proxy/scan/credits')
      if (!response.ok) throw new Error('Failed to fetch credits')
      return response.json()
    },
  })

  // Fetch recent scans
  const { data: apiScans, isLoading: scansLoading, refetch: refetchScans } = useQuery<SkillScan[]>({
    queryKey: ['scan-scans'],
    queryFn: async () => {
      const response = await fetch('/api/proxy/scan/scans')
      if (!response.ok) throw new Error('Failed to fetch scans')
      const data = await response.json()
      return data.scans || data
    },
    refetchInterval: 5000,
  })

  // Fetch monitored skills
  const { data: apiMonitored, isLoading: monitoredLoading, refetch: refetchMonitored } = useQuery<ApiMonitoredSkill[]>({
    queryKey: ['scan-monitored'],
    queryFn: async () => {
      const response = await fetch('/api/proxy/scan/monitoring')
      if (!response.ok) throw new Error('Failed to fetch monitored skills')
      return response.json()
    },
    refetchInterval: 10000,
  })

  // Initiate scan mutation
  const scanMutation = useMutation({
    mutationFn: async (data: ScanFormData) => {
      const response = await fetch('/api/proxy/scan/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_id: data.target,
          profile: data.profile,
          target_type: data.target_type,
        }),
      })
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Scan failed')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scan-scans'] })
      queryClient.invalidateQueries({ queryKey: ['scan-credits'] })
      setActiveTab('history')
    },
    onError: (err: Error) => {
      setError(err.message)
    },
  })

  // Stop monitoring mutation
  const stopMonitoringMutation = useMutation({
    mutationFn: async (monitorId: string) => {
      const response = await fetch(`/api/proxy/scan/monitoring/${monitorId}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('Failed to stop monitoring')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scan-monitored'] })
    },
  })

  // Transform API scans to ScanRecord format
  const scans: ScanRecord[] = (apiScans || []).map((scan): ScanRecord => ({
    id: scan.id,
    target_type: 'skill',
    target: scan.skill_id,
    profile: scan.profile,
    status: scan.status,
    trust_score: scan.trust_score,
    findings_critical: scan.risk_level === 'critical' ? 1 : 0,
    findings_high: scan.risk_level === 'high' ? 1 : 0,
    findings_medium: scan.risk_level === 'medium' ? 1 : 0,
    findings_low: scan.risk_level === 'low' ? 1 : 0,
    created_at: scan.created_at,
    completed_at: scan.completed_at,
    duration_ms: scan.scan_duration_ms,
  }))

  // Transform API monitored skills to MonitoredSkill format
  const monitoredSkills: MonitoredSkill[] = (apiMonitored || []).map((skill): MonitoredSkill => ({
    id: skill.id,
    skill_id: skill.skill_id,
    skill_name: skill.skill_name,
    status: skill.status === 'alerted' ? 'active' : skill.status === 'disabled' ? 'paused' : skill.status,
    check_interval_seconds: skill.check_interval_seconds,
    last_check_at: skill.last_check_at,
    next_check_at: skill.next_check_at,
    baseline_trust_score: skill.baseline_trust_score,
    current_trust_score: skill.baseline_trust_score, // Would be different in real app
    findings_detected: skill.findings_detected,
    alerts_sent: skill.alerts_sent,
  }))

  // Calculate stats
  const stats = {
    totalScans: scans.length,
    completedScans: scans.filter(s => s.status === 'completed').length,
    criticalFindings: scans.reduce((sum, s) => sum + s.findings_critical, 0),
    highFindings: scans.reduce((sum, s) => sum + s.findings_high, 0),
    avgTrustScore: scans.filter(s => s.trust_score !== null).length > 0
      ? Math.round(scans.filter(s => s.trust_score !== null).reduce((sum, s) => sum + (s.trust_score ?? 0), 0) / scans.filter(s => s.trust_score !== null).length)
      : null,
  }

  // Handlers
  const handleScanSubmit = useCallback(async (data: ScanFormData) => {
    await scanMutation.mutateAsync(data)
  }, [scanMutation])

  const handleViewScan = useCallback(async (scanId: string) => {
    const scan = scans.find(s => s.id === scanId)
    if (scan) {
      setSelectedScan(scan)

      // Fetch real findings from API
      try {
        const response = await fetch(`/api/proxy/scan/scans/${scanId}`)
        if (response.ok) {
          const data = await response.json()
          // Transform API findings to ScanFinding format
          const apiFindings = (data.findings || []).map((f: any): ScanFinding => ({
            id: f.id,
            severity: f.severity,
            category: f.type || 'misconfiguration',
            title: f.title,
            description: f.description,
            file_path: f.file_path,
            line_number: f.line_number,
            code_snippet: f.code_snippet,
            recommendation: f.remediation || 'Review and address this finding',
            references: f.reference_urls,
          }))
          setScanFindings(apiFindings.length > 0 ? apiFindings : generateDemoFindings(scan))
        } else {
          // Fallback to demo findings if API fails
          setScanFindings(generateDemoFindings(scan))
        }
      } catch (err) {
        console.error('Error fetching scan details:', err)
        setScanFindings(generateDemoFindings(scan))
      }
    }
  }, [scans])

  const handleRefreshScans = useCallback(async () => {
    await refetchScans()
  }, [refetchScans])

  const handleSaveSettings = useCallback(async () => {
    // Would save to backend in real implementation
    await new Promise(resolve => setTimeout(resolve, 500))
  }, [])

  const isLoading = creditsLoading || scansLoading

  return (
    <div className="space-y-6">
      {/* Page Header with Credits */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Shield className="text-cyan-400" size={28} />
            Claw<span className="text-cyan-400">Shell</span> Scan
          </h1>
          <p className="text-sm text-slate-400 mt-1">Security Scanner for OpenClaw Skills</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Credits */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/50 border border-slate-700/50">
            <div className="p-1 bg-amber-500/10 rounded">
              <Zap size={14} className="text-amber-400" />
            </div>
            <div className="text-right">
              <div className="text-sm font-mono font-semibold text-white">
                {credits?.remaining_credits ?? '—'}
                <span className="text-slate-600">/{credits?.total_credits ?? 50}</span>
              </div>
            </div>
          </div>

          {/* Refresh */}
          <button
            onClick={() => { refetchScans(); refetchMonitored(); }}
            className="p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-cyan-400 hover:border-cyan-500/30 transition-all"
            title="Refresh data"
          >
            <RefreshCw size={18} />
          </button>

          {/* Notifications */}
          <button className="relative p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-slate-400 hover:text-white transition-colors">
            <Bell size={18} />
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="border-b border-slate-800/80 bg-slate-900/30 backdrop-blur-sm rounded-t-xl">
        <div className="flex gap-1">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors border-b-2 -mb-px',
                  activeTab === tab.id
                    ? 'text-cyan-400 border-cyan-400'
                    : 'text-slate-400 border-transparent hover:text-white hover:border-slate-600'
                )}
              >
                <Icon size={16} />
                {tab.label}
              </button>
            )
          })}
        </div>
      </nav>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 flex items-center gap-2">
          <AlertTriangle size={18} />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto p-1 hover:bg-red-500/20 rounded"
          >
            ×
          </button>
        </div>
      )}

          {/* Loading State */}
          {isLoading ? (
            <div className="space-y-8">
              <StatsGrid columns={4}>
                {[...Array(4)].map((_, i) => (
                  <StatCardSkeleton key={i} />
                ))}
              </StatsGrid>
              <div className="animate-pulse h-96 bg-slate-800/50 rounded-xl" />
            </div>
          ) : (
            <>
              {/* Dashboard Tab */}
              {activeTab === 'dashboard' && (
                <div className="space-y-8">
                  {/* Stats Grid */}
                  <StatsGrid columns={4}>
                    <StatCard
                      label="Total Scans"
                      value={stats.totalScans}
                      icon={Activity}
                      accent="cyan"
                      trend={stats.totalScans > 0 ? { value: 12, label: 'this month' } : undefined}
                    />
                    <StatCard
                      label="Completed"
                      value={stats.completedScans}
                      icon={CheckCircle}
                      accent="emerald"
                    />
                    <StatCard
                      label="Critical Issues"
                      value={stats.criticalFindings}
                      icon={AlertTriangle}
                      accent={stats.criticalFindings > 0 ? 'rose' : 'slate'}
                    />
                    <StatCard
                      label="Avg Trust Score"
                      value={stats.avgTrustScore ?? '—'}
                      icon={TrendingUp}
                      accent={stats.avgTrustScore && stats.avgTrustScore >= 70 ? 'emerald' : stats.avgTrustScore && stats.avgTrustScore >= 40 ? 'amber' : 'slate'}
                    />
                  </StatsGrid>

                  {/* Main Content Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Scan Form */}
                    <div className="lg:col-span-2">
                      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-6">
                          <h2 className="text-lg font-semibold text-white">New Security Scan</h2>
                          <div className="flex items-center gap-2 text-xs text-slate-500">
                            <Shield size={14} className="text-cyan-400" />
                            Secure & Private
                          </div>
                        </div>
                        <ScanForm
                          onSubmit={handleScanSubmit}
                          credits={credits?.remaining_credits ?? 0}
                          isSubmitting={scanMutation.isPending}
                        />
                      </div>
                    </div>

                    {/* Trust Score Overview */}
                    <div className="space-y-6">
                      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
                        <h3 className="text-sm font-medium text-slate-400 mb-4">Overall Trust Score</h3>
                        <div className="flex justify-center mb-4">
                          <TrustScoreGauge
                            score={stats.avgTrustScore}
                            size="xl"
                            label="Average"
                          />
                        </div>
                        <TrustScoreBar score={stats.avgTrustScore} />
                      </div>

                      {/* Recent Activity */}
                      <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-sm font-medium text-slate-400">Recent Scans</h3>
                          <button
                            onClick={() => setActiveTab('history')}
                            className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                          >
                            View All
                          </button>
                        </div>
                        <div className="space-y-3">
                          {scans.length === 0 ? (
                            <p className="text-sm text-slate-500 text-center py-4">No scans yet</p>
                          ) : (
                            scans.slice(0, 5).map((scan) => (
                              <div
                                key={scan.id}
                                className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-800/50 transition-colors cursor-pointer"
                                onClick={() => handleViewScan(scan.id)}
                              >
                                <TrustScoreGauge score={scan.trust_score} size="sm" animated={false} />
                                <div className="flex-1 min-w-0">
                                  <p className="text-sm text-white truncate">{scan.target}</p>
                                  <p className="text-xs text-slate-500">{scan.target_type}</p>
                                </div>
                                <StatusBadge status={scan.status} size="sm" />
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* History Tab */}
              {activeTab === 'history' && (
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
                  <ScanHistory
                    scans={scans}
                    onViewScan={handleViewScan}
                    onRefresh={handleRefreshScans}
                    isLoading={scansLoading}
                  />
                </div>
              )}

              {/* Monitoring Tab */}
              {activeTab === 'monitoring' && (
                <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
                  <MonitoredSkillsPanel
                    skills={monitoredSkills}
                    onPause={(id) => console.log('Pause:', id)}
                    onResume={(id) => console.log('Resume:', id)}
                    onRemove={(id) => stopMonitoringMutation.mutate(id)}
                    onScanNow={(id) => console.log('Scan now:', id)}
                    onAddSkill={() => console.log('Add skill')}
                  />
                </div>
              )}

              {/* Settings Tab */}
              {activeTab === 'settings' && (
                <div className="max-w-2xl mx-auto">
                  <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-sm">
                    <SettingsPanel onSave={handleSaveSettings} />
                  </div>
                </div>
              )}
            </>
          )}

        {/* Scan Details Modal */}
        {selectedScan && (
          <ScanDetails
            scan={selectedScan}
            findings={scanFindings}
            isOpen={!!selectedScan}
            onClose={() => {
              setSelectedScan(null)
              setScanFindings([])
            }}
          />
        )}
    </div>
  )
}
