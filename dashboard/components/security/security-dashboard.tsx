'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

// Types
interface SecurityEvent {
  id: string
  timestamp: string
  threat_type: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  confidence: number
  description: string
  agent_id?: string
  action_taken: string
}

interface DetectorStatus {
  name: string
  enabled: boolean
  priority: number
  threat_type: string
}

interface SecurityStats {
  total_events: number
  events_24h: number
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  blocked_count: number
  alerted_count: number
  threat_breakdown: Record<string, number>
  severity_breakdown: Record<string, number>
}

interface SecurityDashboardProps {
  orgId?: string
  refreshInterval?: number
}

// Severity badge colors
const severityColors: Record<string, string> = {
  critical: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-black',
  low: 'bg-blue-500 text-white',
  info: 'bg-gray-500 text-white',
}

// Threat type labels
const threatLabels: Record<string, string> = {
  prompt_injection: 'Prompt Injection',
  credential_exposure: 'Credential Exposure',
  data_exfiltration: 'Data Exfiltration',
  tool_abuse: 'Tool Abuse',
  runaway_loop: 'Runaway Loop',
  behavioral_anomaly: 'Anomaly',
  custom: 'Custom Rule',
}

export function SecurityDashboard({
  orgId,
  refreshInterval = 5000,
}: SecurityDashboardProps) {
  const [stats, setStats] = useState<SecurityStats | null>(null)
  const [recentEvents, setRecentEvents] = useState<SecurityEvent[]>([])
  const [detectors, setDetectors] = useState<DetectorStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [connected, setConnected] = useState(false)

  // Fetch security stats
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch('/api/security/stats')
      if (!response.ok) throw new Error('Failed to fetch stats')
      const data = await response.json()
      setStats(data)
    } catch (err) {
      console.error('Error fetching stats:', err)
    }
  }, [])

  // Fetch recent events
  const fetchEvents = useCallback(async () => {
    try {
      const params = new URLSearchParams({
        limit: '20',
        ...(orgId && { org_id: orgId }),
      })
      const response = await fetch(`/api/security/events?${params}`)
      if (!response.ok) throw new Error('Failed to fetch events')
      const data = await response.json()
      setRecentEvents(data.events || [])
    } catch (err) {
      console.error('Error fetching events:', err)
    }
  }, [orgId])

  // Fetch detector status
  const fetchDetectors = useCallback(async () => {
    try {
      const response = await fetch('/security/status')
      if (!response.ok) throw new Error('Failed to fetch detectors')
      const data = await response.json()
      setDetectors(
        Object.entries(data.detectors || {}).map(([name, info]: [string, any]) => ({
          name,
          enabled: info.enabled,
          priority: info.priority,
          threat_type: info.threat_type,
        }))
      )
      setConnected(data.enabled)
    } catch (err) {
      console.error('Error fetching detectors:', err)
      setConnected(false)
    }
  }, [])

  // Initial fetch
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchStats(), fetchEvents(), fetchDetectors()])
      setLoading(false)
    }
    loadData()
  }, [fetchStats, fetchEvents, fetchDetectors])

  // Polling for updates
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStats()
      fetchEvents()
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [fetchStats, fetchEvents, refreshInterval])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
      </div>
    )
  }

  if (!connected) {
    return (
      <Card className="border-yellow-500">
        <CardHeader>
          <CardTitle>Security Engine Offline</CardTitle>
          <CardDescription>
            The security engine is not currently running. Start it to enable threat detection.
          </CardDescription>
        </CardHeader>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Security Dashboard</h2>
          <p className="text-muted-foreground">Real-time threat detection and monitoring</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`h-3 w-3 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-muted-foreground">
            {connected ? 'Protected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Events (24h)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.events_24h || 0}</div>
            <p className="text-xs text-muted-foreground">
              Total: {stats?.total_events || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Critical/High</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {(stats?.critical_count || 0) + (stats?.high_count || 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Critical: {stats?.critical_count || 0} / High: {stats?.high_count || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Blocked</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.blocked_count || 0}</div>
            <p className="text-xs text-muted-foreground">
              Alerted: {stats?.alerted_count || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Active Detectors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {detectors.filter((d) => d.enabled).length}
            </div>
            <p className="text-xs text-muted-foreground">
              of {detectors.length} total
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Severity Distribution */}
      <Card>
        <CardHeader>
          <CardTitle>Severity Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {['critical', 'high', 'medium', 'low'].map((severity) => {
              const count = stats?.severity_breakdown?.[severity] || 0
              const total = stats?.events_24h || 1
              const percentage = Math.round((count / total) * 100)

              return (
                <div key={severity} className="flex items-center gap-4">
                  <div className="w-20 capitalize font-medium">{severity}</div>
                  <Progress value={percentage} className="flex-1" />
                  <div className="w-12 text-right text-sm text-muted-foreground">
                    {count}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Threat Breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Threat Types</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(stats?.threat_breakdown || {}).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm">
                    {threatLabels[type] || type.replace('_', ' ')}
                  </span>
                  <Badge variant="secondary">{count as number}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Detector Status */}
        <Card>
          <CardHeader>
            <CardTitle>Detector Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {detectors.map((detector) => (
                <div key={detector.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div
                      className={`h-2 w-2 rounded-full ${
                        detector.enabled ? 'bg-green-500' : 'bg-gray-400'
                      }`}
                    />
                    <span className="text-sm capitalize">
                      {detector.name.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    P{detector.priority}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Events */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Security Events</CardTitle>
          <CardDescription>Latest threat detections</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentEvents.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">
                No security events recorded
              </p>
            ) : (
              recentEvents.map((event) => (
                <div
                  key={event.id}
                  className="flex items-start gap-4 p-4 border rounded-lg"
                >
                  <Badge className={severityColors[event.severity]}>
                    {event.severity.toUpperCase()}
                  </Badge>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        {threatLabels[event.threat_type] || event.threat_type}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {(event.confidence * 100).toFixed(0)}% confidence
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground truncate">
                      {event.description}
                    </p>
                    <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                      <span>
                        {new Date(event.timestamp).toLocaleString()}
                      </span>
                      {event.agent_id && (
                        <span>Agent: {event.agent_id.slice(0, 8)}...</span>
                      )}
                      <span className="capitalize">
                        Action: {event.action_taken}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Export smaller components for individual use
export function SecurityEventBadge({ event }: { event: SecurityEvent }) {
  return (
    <div className="inline-flex items-center gap-2 px-2 py-1 border rounded-md">
      <Badge className={severityColors[event.severity]} variant="outline">
        {event.severity}
      </Badge>
      <span className="text-sm">{threatLabels[event.threat_type]}</span>
    </div>
  )
}

export function SecurityStatusIndicator({ connected }: { connected: boolean }) {
  return (
    <div className="inline-flex items-center gap-2">
      <div
        className={`h-2 w-2 rounded-full ${
          connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
        }`}
      />
      <span className="text-sm">{connected ? 'Protected' : 'Unprotected'}</span>
    </div>
  )
}
