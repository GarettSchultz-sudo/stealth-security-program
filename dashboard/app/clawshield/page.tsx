'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Shield,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  Search,
  Loader2,
  ExternalLink,
  Download,
  RefreshCw,
  FileWarning,
  Bug,
  Lock,
  Globe,
  Cloud,
  Container,
  GitBranch,
  Zap,
  TestTube,
} from 'lucide-react'

// Types
interface ScanProgress {
  scan_id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  phase: string
  progress: number
  message: string
  findings_count: number
  files_scanned: number
  patterns_checked: number
  current_tool?: string
  estimated_time_remaining?: number
  error?: string
}

interface Finding {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description: string
  resource?: string
  remediation?: string
  cve_ids?: string[]
  cwe_ids?: string[]
  scanner: string
}

interface ScanResult {
  id: string
  status: string
  trust_score: number
  risk_level: string
  recommendation: string
  findings: Finding[]
  scan_duration_ms: number
  files_scanned: number
  patterns_checked: number
  metadata?: {
    scan_mode?: 'real' | 'simulation'
    proxy_available?: boolean
    note?: string
  }
}

// Scan profiles
const SCAN_PROFILES = {
  quick: { name: 'Quick Scan', cost: 1, description: 'Fast scan for critical issues', duration: '1-2 min' },
  standard: { name: 'Standard Scan', cost: 2, description: 'Balanced depth and speed', duration: '3-5 min' },
  deep: { name: 'Deep Scan', cost: 5, description: 'Comprehensive analysis', duration: '10-15 min' },
  comprehensive: { name: 'Full Audit', cost: 10, description: 'Complete security audit', duration: '20-30 min' },
}

// Target type icons
const TARGET_ICONS: Record<string, React.ReactNode> = {
  url: <Globe className="h-4 w-4" />,
  repo: <GitBranch className="h-4 w-4" />,
  container: <Container className="h-4 w-4" />,
  cloud: <Cloud className="h-4 w-4" />,
}

// Severity colors
const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500 text-white',
  high: 'bg-orange-500 text-white',
  medium: 'bg-yellow-500 text-black',
  low: 'bg-blue-500 text-white',
  info: 'bg-gray-500 text-white',
}

export default function ClawShieldPage() {
  const [target, setTarget] = useState('')
  const [targetType, setTargetType] = useState('url')
  const [profile, setProfile] = useState('standard')
  const [scanning, setScanning] = useState(false)
  const [scanId, setScanId] = useState<string | null>(null)
  const [scanMode, setScanMode] = useState<'real' | 'simulation' | null>(null)
  const [proxyAvailable, setProxyAvailable] = useState(false)
  const [scannerStatus, setScannerStatus] = useState<{
    checked: boolean
    nuclei: boolean
    trivy: boolean
    prowler: boolean
  }>({ checked: false, nuclei: false, trivy: false, prowler: false })
  const [progress, setProgress] = useState<ScanProgress | null>(null)
  const [result, setResult] = useState<ScanResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [scanHistory, setScanHistory] = useState<any[]>([])

  // Detect target type automatically
  const detectTargetType = useCallback((value: string) => {
    const lower = value.toLowerCase()
    if (lower.startsWith('http://') || lower.startsWith('https://')) return 'url'
    if (lower.includes('github.com') || lower.includes('gitlab.com') || lower.endsWith('.git')) return 'repo'
    if (lower.includes('/') && lower.includes(':') && !lower.startsWith('http')) return 'container'
    if (lower.startsWith('aws:') || lower.startsWith('azure:') || lower.startsWith('gcp:')) return 'cloud'
    return 'url'
  }, [])

  // Handle target input change
  const handleTargetChange = (value: string) => {
    setTarget(value)
    setTargetType(detectTargetType(value))
  }

  // Start a new scan
  const startScan = async () => {
    if (!target) return

    setScanning(true)
    setError(null)
    setResult(null)
    setProgress(null)
    setScanMode(null)

    try {
      const response = await fetch('/api/proxy/scan/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          skill_id: target,
          target,
          target_type: targetType,
          profile,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start scan')
      }

      setScanId(data.scan_id)
      setScanMode(data.scan_mode || null)
      setProxyAvailable(data.proxy_available || false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start scan')
      setScanning(false)
    }
  }

  // Poll for scan progress when scanId is set
  useEffect(() => {
    if (!scanId || !scanning) return

    // Use SSE for real-time updates
    const eventSource = new EventSource(`/api/scans/progress/${scanId}`)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'progress') {
        setProgress(data)
      } else if (data.type === 'complete' || data.type === 'timeout') {
        eventSource.close()
        fetchResults(scanId)
      }
    }

    eventSource.onerror = () => {
      // Fallback to polling if SSE fails
      const pollInterval = setInterval(async () => {
        try {
          const response = await fetch(`/api/proxy/scan/scans/${scanId}`)
          const data = await response.json()

          if (data.status === 'completed' || data.status === 'failed') {
            clearInterval(pollInterval)
            fetchResults(scanId)
          } else {
            setProgress({
              scan_id: scanId,
              status: data.status,
              phase: data.status,
              progress: 50,
              message: 'Scan in progress...',
              findings_count: 0,
              files_scanned: data.files_scanned || 0,
              patterns_checked: data.patterns_checked || 0,
            })
          }
        } catch (err) {
          clearInterval(pollInterval)
        }
      }, 2000)

      return () => clearInterval(pollInterval)
    }

    return () => eventSource.close()
  }, [scanId, scanning])

  // Fetch final results
  const fetchResults = async (id: string) => {
    try {
      const response = await fetch(`/api/proxy/scan/scans/${id}`)
      const data = await response.json()
      setResult(data)
      setScanning(false)

      // Refresh history
      fetchHistory()
    } catch (err) {
      setError('Failed to fetch scan results')
      setScanning(false)
    }
  }

  // Fetch scan history
  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/proxy/scan/scans?limit=10')
      const data = await response.json()
      setScanHistory(data.scans || [])
    } catch (err) {
      console.error('Failed to fetch history:', err)
    }
  }

  // Check scanner health
  const checkScannerHealth = async () => {
    try {
      const response = await fetch('/api/scans/health')
      const data = await response.json()

      setProxyAvailable(data.proxy_available)
      setScannerStatus({
        checked: true,
        nuclei: data.scanners?.nuclei || false,
        trivy: data.scanners?.trivy || false,
        prowler: data.scanners?.prowler || false,
      })
    } catch (err) {
      setScannerStatus({
        checked: true,
        nuclei: false,
        trivy: false,
        prowler: false,
      })
    }
  }

  // Load history on mount
  useEffect(() => {
    fetchHistory()
    checkScannerHealth()
  }, [])

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <Shield className="h-10 w-10 text-primary" />
        <div className="flex-1">
          <h1 className="text-3xl font-bold">ClawShield Security Scanner</h1>
          <p className="text-muted-foreground">
            Scan URLs, repositories, containers, and cloud infrastructure for security vulnerabilities
          </p>
        </div>
        {/* Scanner Status Indicator */}
        {scannerStatus.checked && (
          <div className="flex items-center gap-2">
            {proxyAvailable ? (
              <Badge className="bg-green-500">
                <Zap className="h-3 w-3 mr-1" />
                Real Scanning
              </Badge>
            ) : (
              <Badge variant="outline" className="text-yellow-600 border-yellow-500">
                <TestTube className="h-3 w-3 mr-1" />
                Simulation Mode
              </Badge>
            )}
          </div>
        )}
      </div>

      {/* Scanner Tools Status */}
      {scannerStatus.checked && (
        <div className="flex flex-wrap gap-2 mb-6">
          <span className="text-sm text-muted-foreground">Scanners:</span>
          <Badge variant={scannerStatus.nuclei ? "default" : "outline"} className={scannerStatus.nuclei ? "bg-green-500" : "text-muted-foreground"}>
            Nuclei {scannerStatus.nuclei ? '✓' : '✗'}
          </Badge>
          <Badge variant={scannerStatus.trivy ? "default" : "outline"} className={scannerStatus.trivy ? "bg-green-500" : "text-muted-foreground"}>
            Trivy {scannerStatus.trivy ? '✓' : '✗'}
          </Badge>
          <Badge variant={scannerStatus.prowler ? "default" : "outline"} className={scannerStatus.prowler ? "bg-green-500" : "text-muted-foreground"}>
            Prowler {scannerStatus.prowler ? '✓' : '✗'}
          </Badge>
          {!proxyAvailable && (
            <span className="text-xs text-muted-foreground ml-2">
              (Proxy unavailable - scans will use simulated data)
            </span>
          )}
        </div>
      )}

      <Tabs defaultValue="scan" className="space-y-6">
        <TabsList>
          <TabsTrigger value="scan">
            <Search className="h-4 w-4 mr-2" />
            New Scan
          </TabsTrigger>
          <TabsTrigger value="history">
            <Clock className="h-4 w-4 mr-2" />
            History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="scan" className="space-y-6">
          {/* Scan Form */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {TARGET_ICONS[targetType]}
                Start Security Scan
              </CardTitle>
              <CardDescription>
                Enter a URL, repository, container image, or cloud resource to scan
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Target Input */}
              <div className="space-y-2">
                <Label htmlFor="target">Target</Label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      id="target"
                      placeholder="https://example.com or github.com/user/repo"
                      value={target}
                      onChange={(e) => handleTargetChange(e.target.value)}
                      className="pr-10"
                    />
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                      {TARGET_ICONS[targetType]}
                    </div>
                  </div>
                </div>
              </div>

              {/* Scan Profile */}
              <div className="space-y-2">
                <Label htmlFor="profile">Scan Profile</Label>
                <Select value={profile} onValueChange={setProfile}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(SCAN_PROFILES).map(([key, value]) => (
                      <SelectItem key={key} value={key}>
                        <div className="flex items-center justify-between w-full">
                          <span>{value.name}</span>
                          <span className="text-muted-foreground ml-2">
                            {value.cost} credits • {value.duration}
                          </span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground">
                  {SCAN_PROFILES[profile].description}
                </p>
              </div>

              {/* Error Alert */}
              {error && (
                <Alert variant="destructive">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>Error</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </CardContent>
            <CardFooter>
              <Button
                onClick={startScan}
                disabled={!target || scanning}
                className="w-full sm:w-auto"
              >
                {scanning ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Scanning...
                  </>
                ) : (
                  <>
                    <Shield className="h-4 w-4 mr-2" />
                    Start Scan ({SCAN_PROFILES[profile].cost} credits)
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>

          {/* Progress Card */}
          {(scanning || progress) && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Scan Progress
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="capitalize">{progress?.phase || 'Initializing'}</span>
                    <span>{progress?.progress || 0}%</span>
                  </div>
                  <Progress value={progress?.progress || 0} />
                </div>

                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  {progress?.current_tool && (
                    <span>Tool: {progress.current_tool}</span>
                  )}
                  {progress?.findings_count !== undefined && progress.findings_count > 0 && (
                    <span className="text-yellow-600">
                      {progress.findings_count} findings
                    </span>
                  )}
                  {progress?.estimated_time_remaining && progress.estimated_time_remaining > 0 && (
                    <span>~{Math.ceil(progress.estimated_time_remaining / 60)} min remaining</span>
                  )}
                </div>

                <p className="text-sm">{progress?.message || 'Starting scan...'}</p>
              </CardContent>
            </Card>
          )}

          {/* Simulation Mode Warning */}
          {(scanMode === 'simulation' || result?.metadata?.scan_mode === 'simulation') && (
            <Alert className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
              <TestTube className="h-4 w-4 text-yellow-600" />
              <AlertTitle className="text-yellow-700 dark:text-yellow-300">
                Simulation Mode
              </AlertTitle>
              <AlertDescription className="text-yellow-600 dark:text-yellow-400">
                This scan used simulated data. The proxy server is not available or scanner tools are not installed.
                To enable real scanning, ensure the proxy is running with Nuclei, Trivy, and Prowler installed.
              </AlertDescription>
            </Alert>
          )}

          {/* Real Scan Indicator */}
          {scanMode === 'real' && scanning && (
            <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
              <Zap className="h-4 w-4 text-green-600" />
              <AlertTitle className="text-green-700 dark:text-green-300">
                Real Scanning Active
              </AlertTitle>
              <AlertDescription className="text-green-600 dark:text-green-400">
                Connected to proxy server. Running real security scans with Nuclei, Trivy, or Prowler.
              </AlertDescription>
            </Alert>
          )}

          {/* Results Card */}
          {result && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="flex items-center gap-2">
                      {result.recommendation === 'safe' ? (
                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                      ) : result.recommendation === 'avoid' ? (
                        <XCircle className="h-5 w-5 text-red-500" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-yellow-500" />
                      )}
                      Scan Results
                    </CardTitle>
                    {result.metadata?.scan_mode === 'simulation' ? (
                      <Badge variant="outline" className="text-yellow-600 border-yellow-500">
                        <TestTube className="h-3 w-3 mr-1" />
                        Simulated
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-green-600 border-green-500">
                        <Zap className="h-3 w-3 mr-1" />
                        Real Scan
                      </Badge>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => setResult(null)}>
                      <RefreshCw className="h-4 w-4 mr-2" />
                      New Scan
                    </Button>
                    <Button variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Export
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Trust Score */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-3xl font-bold">{result.trust_score}</div>
                    <div className="text-sm text-muted-foreground">Trust Score</div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <Badge className={result.risk_level === 'low' ? 'bg-green-500' : result.risk_level === 'critical' ? 'bg-red-500' : 'bg-yellow-500'}>
                      {result.risk_level.toUpperCase()}
                    </Badge>
                    <div className="text-sm text-muted-foreground mt-1">Risk Level</div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold">{result.findings.length}</div>
                    <div className="text-sm text-muted-foreground">Findings</div>
                  </div>
                  <div className="text-center p-4 bg-muted rounded-lg">
                    <div className="text-2xl font-bold">
                      {result.scan_duration_ms ? `${(result.scan_duration_ms / 1000).toFixed(1)}s` : '-'}
                    </div>
                    <div className="text-sm text-muted-foreground">Duration</div>
                  </div>
                </div>

                {/* Findings */}
                {result.findings.length > 0 && (
                  <div className="space-y-4">
                    <h3 className="font-semibold flex items-center gap-2">
                      <FileWarning className="h-5 w-5" />
                      Security Findings
                    </h3>
                    <div className="space-y-3">
                      {result.findings.map((finding) => (
                        <div
                          key={finding.id}
                          className="border rounded-lg p-4 hover:bg-muted/50 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <Badge className={SEVERITY_COLORS[finding.severity]}>
                                  {finding.severity.toUpperCase()}
                                </Badge>
                                <span className="text-sm text-muted-foreground">
                                  {finding.scanner}
                                </span>
                              </div>
                              <h4 className="font-medium">{finding.title}</h4>
                              {finding.description && (
                                <p className="text-sm text-muted-foreground mt-1">
                                  {finding.description}
                                </p>
                              )}
                              {finding.resource && (
                                <p className="text-xs text-muted-foreground mt-1 font-mono">
                                  {finding.resource}
                                </p>
                              )}
                              {finding.remediation && (
                                <div className="mt-2 p-2 bg-green-50 dark:bg-green-950 rounded text-sm">
                                  <strong>Remediation:</strong> {finding.remediation}
                                </div>
                              )}
                            </div>
                            {finding.cve_ids && finding.cve_ids.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {finding.cve_ids.map((cve) => (
                                  <a
                                    key={cve}
                                    href={`https://nvd.nist.gov/vuln/detail/${cve}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-blue-500 hover:underline"
                                  >
                                    {cve}
                                  </a>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* No Findings */}
                {result.findings.length === 0 && (
                  <div className="text-center py-8">
                    <CheckCircle2 className="h-12 w-12 text-green-500 mx-auto mb-2" />
                    <h3 className="font-semibold text-lg">No Issues Found</h3>
                    <p className="text-muted-foreground">
                      No security vulnerabilities were detected in this scan.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Scan History</CardTitle>
              <CardDescription>Your recent security scans</CardDescription>
            </CardHeader>
            <CardContent>
              {scanHistory.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No scans yet. Start your first scan!
                </div>
              ) : (
                <div className="space-y-3">
                  {scanHistory.map((scan) => (
                    <div
                      key={scan.id}
                      className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                      onClick={() => {
                        setScanId(scan.id)
                        fetchResults(scan.id)
                      }}
                    >
                      <div className="flex items-center gap-3">
                        {scan.status === 'completed' ? (
                          <CheckCircle2 className="h-5 w-5 text-green-500" />
                        ) : scan.status === 'failed' ? (
                          <XCircle className="h-5 w-5 text-red-500" />
                        ) : (
                          <Clock className="h-5 w-5 text-yellow-500" />
                        )}
                        <div>
                          <div className="font-medium">{scan.skill_name || scan.skill_id}</div>
                          <div className="text-sm text-muted-foreground">
                            {new Date(scan.created_at).toLocaleString()}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {scan.trust_score !== null && (
                          <Badge variant="outline">{scan.trust_score} trust</Badge>
                        )}
                        <Badge>{scan.profile}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
