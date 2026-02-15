'use client'

import { useState } from 'react'
import {
  X,
  Shield,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  Clock,
  FileCode,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TrustScoreGauge, TrustScoreBar } from './trust-score-gauge'
import { RiskBadge } from './risk-badge'
import type { ScanRecord } from './scan-history'

export interface ScanFinding {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  category: string
  title: string
  description: string
  file_path?: string
  line_number?: number
  code_snippet?: string
  recommendation: string
  references?: string[]
}

export interface ScanDetailsProps {
  scan: ScanRecord
  findings: ScanFinding[]
  isOpen: boolean
  onClose: () => void
}

const severityConfig = {
  critical: {
    icon: AlertTriangle,
    color: 'text-rose-400',
    bg: 'bg-rose-500/10',
    border: 'border-rose-500/30',
    label: 'Critical',
  },
  high: {
    icon: AlertTriangle,
    color: 'text-orange-400',
    bg: 'bg-orange-500/10',
    border: 'border-orange-500/30',
    label: 'High',
  },
  medium: {
    icon: AlertCircle,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    label: 'Medium',
  },
  low: {
    icon: Info,
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    label: 'Low',
  },
  info: {
    icon: Info,
    color: 'text-slate-400',
    bg: 'bg-slate-500/10',
    border: 'border-slate-500/30',
    label: 'Info',
  },
}

const categoryIcons: Record<string, string> = {
  'injection': '💉',
  'xss': '🔗',
  'auth': '🔐',
  'secrets': '🔑',
  'crypto': '🔒',
  'dos': '💥',
  'info-disclosure': '📄',
  'misconfiguration': '⚙️',
  'dependencies': '📦',
  'code-quality': '✨',
  'default': '🔍',
}

export function ScanDetails({ scan, findings, isOpen, onClose }: ScanDetailsProps) {
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'findings' | 'recommendations' | 'raw'>('findings')
  const [copiedId, setCopiedId] = useState<string | null>(null)

  if (!isOpen) return null

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  // Group findings by severity
  const findingsBySeverity = findings.reduce((acc, finding) => {
    if (!acc[finding.severity]) acc[finding.severity] = []
    acc[finding.severity].push(finding)
    return acc
  }, {} as Record<string, ScanFinding[]>)

  // Calculate summary stats
  const totalFindings = findings.length
  const criticalCount = findingsBySeverity.critical?.length || 0
  const highCount = findingsBySeverity.high?.length || 0
  const mediumCount = findingsBySeverity.medium?.length || 0

  // Generate recommendations based on findings
  const recommendations = [
    ...new Set(findings.map(f => f.recommendation).filter(Boolean)),
  ].slice(0, 5)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-cyan-500/10 rounded-xl">
              <Shield className="text-cyan-400" size={24} />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-white">Scan Details</h2>
              <p className="text-sm text-slate-400">{scan.target}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-80px)]">
          {/* Summary Section */}
          <div className="p-6 border-b border-slate-800 bg-slate-900/50">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Trust Score */}
              <div className="flex flex-col items-center p-4 bg-slate-800/50 rounded-xl">
                <TrustScoreGauge
                  score={scan.trust_score}
                  size="lg"
                  label={getTrustLabel(scan.trust_score)}
                />
                <div className="mt-4 w-full">
                  <TrustScoreBar score={scan.trust_score} />
                </div>
              </div>

              {/* Scan Info */}
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <span className="text-sm text-slate-400">Status</span>
                  <span className={cn(
                    'flex items-center gap-1.5 text-sm font-medium',
                    scan.status === 'completed' ? 'text-emerald-400' :
                    scan.status === 'failed' ? 'text-rose-400' :
                    scan.status === 'running' ? 'text-cyan-400' :
                    'text-amber-400'
                  )}>
                    {scan.status === 'completed' && <CheckCircle size={14} />}
                    {scan.status === 'failed' && <AlertTriangle size={14} />}
                    {scan.status === 'running' && <Clock size={14} className="animate-spin" />}
                    {scan.status === 'pending' && <Clock size={14} />}
                    {scan.status.charAt(0).toUpperCase() + scan.status.slice(1)}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <span className="text-sm text-slate-400">Profile</span>
                  <span className="text-sm font-medium text-white capitalize">{scan.profile}</span>
                </div>
                <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <span className="text-sm text-slate-400">Duration</span>
                  <span className="text-sm font-mono text-white">
                    {scan.duration_ms ? `${(scan.duration_ms / 1000).toFixed(1)}s` : '—'}
                  </span>
                </div>
              </div>

              {/* Findings Summary */}
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                  <span className="text-sm text-slate-400">Total Findings</span>
                  <span className="text-lg font-bold text-white">{totalFindings}</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center p-2 bg-rose-500/10 border border-rose-500/30 rounded-lg">
                    <div className="text-lg font-bold text-rose-400">{criticalCount}</div>
                    <div className="text-xs text-slate-500">Critical</div>
                  </div>
                  <div className="text-center p-2 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                    <div className="text-lg font-bold text-orange-400">{highCount}</div>
                    <div className="text-xs text-slate-500">High</div>
                  </div>
                  <div className="text-center p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg">
                    <div className="text-lg font-bold text-amber-400">{mediumCount}</div>
                    <div className="text-xs text-slate-500">Medium</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Tabs */}
          <div className="border-b border-slate-800">
            <div className="flex">
              {(['findings', 'recommendations', 'raw'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    'px-6 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                    activeTab === tab
                      ? 'text-cyan-400 border-cyan-400'
                      : 'text-slate-400 border-transparent hover:text-white hover:border-slate-600'
                  )}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                  {tab === 'findings' && (
                    <span className="ml-2 px-1.5 py-0.5 text-xs rounded-full bg-slate-700">
                      {totalFindings}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Findings Tab */}
            {activeTab === 'findings' && (
              <div className="space-y-4">
                {findings.length === 0 ? (
                  <div className="text-center py-12">
                    <CheckCircle className="mx-auto text-emerald-400 mb-3" size={48} />
                    <h3 className="text-lg font-medium text-white mb-1">No Issues Found</h3>
                    <p className="text-sm text-slate-400">This scan completed without detecting any security issues.</p>
                  </div>
                ) : (
                  findings.map((finding) => {
                    const config = severityConfig[finding.severity]
                    const Icon = config.icon
                    const isExpanded = expandedFinding === finding.id

                    return (
                      <div
                        key={finding.id}
                        className={cn(
                          'border rounded-xl overflow-hidden transition-all',
                          config.border,
                          config.bg
                        )}
                      >
                        {/* Finding Header */}
                        <button
                          onClick={() => setExpandedFinding(isExpanded ? null : finding.id)}
                          className="w-full flex items-center gap-4 p-4 text-left hover:bg-slate-800/30 transition-colors"
                        >
                          <div className={cn('p-2 rounded-lg', config.bg)}>
                            <Icon className={config.color} size={18} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-lg">{categoryIcons[finding.category] || categoryIcons.default}</span>
                              <span className="font-medium text-white truncate">{finding.title}</span>
                            </div>
                            <p className="text-sm text-slate-400 truncate">{finding.description}</p>
                          </div>
                          <div className="flex items-center gap-3">
                            <RiskBadge
                              level={finding.severity as 'critical' | 'high' | 'medium' | 'low' | 'info'}
                              size="sm"
                            />
                            {isExpanded ? (
                              <ChevronDown className="text-slate-400" size={18} />
                            ) : (
                              <ChevronRight className="text-slate-400" size={18} />
                            )}
                          </div>
                        </button>

                        {/* Expanded Details */}
                        {isExpanded && (
                          <div className="px-4 pb-4 space-y-4 border-t border-slate-700/50">
                            {/* File Location */}
                            {finding.file_path && (
                              <div className="mt-4">
                                <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                                  <FileCode size={14} />
                                  <span>Location</span>
                                </div>
                                <div className="flex items-center gap-2 p-2 bg-slate-900/50 rounded-lg font-mono text-sm">
                                  <span className="text-cyan-400">{finding.file_path}</span>
                                  {finding.line_number && (
                                    <span className="text-slate-500">:{finding.line_number}</span>
                                  )}
                                  <button
                                    onClick={() => handleCopy(
                                      `${finding.file_path}:${finding.line_number}`,
                                      finding.id
                                    )}
                                    className="ml-auto p-1 text-slate-500 hover:text-cyan-400 transition-colors"
                                  >
                                    {copiedId === finding.id ? (
                                      <Check size={14} className="text-emerald-400" />
                                    ) : (
                                      <Copy size={14} />
                                    )}
                                  </button>
                                </div>
                              </div>
                            )}

                            {/* Code Snippet */}
                            {finding.code_snippet && (
                              <div>
                                <div className="text-sm text-slate-400 mb-2">Code</div>
                                <pre className="p-3 bg-slate-950/50 rounded-lg overflow-x-auto text-sm font-mono text-slate-300 border border-slate-800">
                                  {finding.code_snippet}
                                </pre>
                              </div>
                            )}

                            {/* Recommendation */}
                            <div>
                              <div className="text-sm text-slate-400 mb-2">Recommendation</div>
                              <p className="text-sm text-slate-300">{finding.recommendation}</p>
                            </div>

                            {/* References */}
                            {finding.references && finding.references.length > 0 && (
                              <div>
                                <div className="text-sm text-slate-400 mb-2">References</div>
                                <div className="space-y-1">
                                  {finding.references.map((ref, idx) => (
                                    <a
                                      key={idx}
                                      href={ref}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                                    >
                                      <ExternalLink size={12} />
                                      {ref}
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })
                )}
              </div>
            )}

            {/* Recommendations Tab */}
            {activeTab === 'recommendations' && (
              <div className="space-y-4">
                {recommendations.length === 0 ? (
                  <div className="text-center py-12">
                    <CheckCircle className="mx-auto text-emerald-400 mb-3" size={48} />
                    <h3 className="text-lg font-medium text-white mb-1">No Recommendations</h3>
                    <p className="text-sm text-slate-400">All detected issues have specific recommendations in the Findings tab.</p>
                  </div>
                ) : (
                  recommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-3 p-4 bg-slate-800/30 border border-slate-700/50 rounded-xl"
                    >
                      <div className="p-2 bg-emerald-500/10 rounded-lg shrink-0">
                        <CheckCircle className="text-emerald-400" size={18} />
                      </div>
                      <p className="text-sm text-slate-300">{rec}</p>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Raw Report Tab */}
            {activeTab === 'raw' && (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="text-sm text-slate-400">Raw scan output in JSON format</span>
                  <button
                    onClick={() => handleCopy(JSON.stringify({ scan, findings }, null, 2), 'raw')}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-slate-400 hover:text-cyan-400 transition-colors"
                  >
                    {copiedId === 'raw' ? (
                      <>
                        <Check size={14} className="text-emerald-400" />
                        Copied
                      </>
                    ) : (
                      <>
                        <Copy size={14} />
                        Copy JSON
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-4 bg-slate-950/50 rounded-xl overflow-x-auto text-sm font-mono text-slate-300 border border-slate-800 max-h-96">
                  {JSON.stringify({ scan, findings }, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function getTrustLabel(score: number | null): string {
  if (score === null) return 'Unknown'
  if (score >= 90) return 'Excellent'
  if (score >= 70) return 'Good'
  if (score >= 50) return 'Fair'
  if (score >= 30) return 'Poor'
  return 'Critical'
}

// Demo findings generator for testing
export function generateDemoFindings(scan: ScanRecord): ScanFinding[] {
  const findings: ScanFinding[] = []

  // Generate findings based on trust score
  if (scan.trust_score && scan.trust_score < 90) {
    findings.push({
      id: '1',
      severity: 'medium',
      category: 'secrets',
      title: 'Potential API Key Exposure',
      description: 'A potential API key pattern was detected in the codebase. This could lead to credential leakage if the code is shared publicly.',
      file_path: 'src/config/settings.ts',
      line_number: 42,
      code_snippet: 'const API_KEY = "sk-xxxxxxxxxxxxxxxx";',
      recommendation: 'Move API keys to environment variables and use a secrets manager. Never commit sensitive credentials to version control.',
      references: ['https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_strings_in_GET_request'],
    })
  }

  if (scan.trust_score && scan.trust_score < 70) {
    findings.push({
      id: '2',
      severity: 'high',
      category: 'injection',
      title: 'Command Injection Vulnerability',
      description: 'User input is being passed directly to a shell command without proper sanitization, potentially allowing arbitrary command execution.',
      file_path: 'src/utils/exec.ts',
      line_number: 15,
      code_snippet: 'exec(`ping ${userInput}`)',
      recommendation: 'Use parameterized commands or escape user input before passing to shell commands. Consider using safer APIs that don\'t invoke a shell.',
      references: ['https://owasp.org/www-community/attacks/Command_Injection'],
    })
  }

  if (scan.trust_score && scan.trust_score < 50) {
    findings.push({
      id: '3',
      severity: 'critical',
      category: 'auth',
      title: 'Authentication Bypass',
      description: 'The authentication mechanism can be bypassed by manipulating the session token, allowing unauthorized access to protected resources.',
      file_path: 'src/auth/middleware.ts',
      line_number: 28,
      code_snippet: 'if (token) { next() }',
      recommendation: 'Implement proper token validation and verification. Use established authentication libraries and frameworks.',
      references: ['https://owasp.org/www-community/attacks/Session_hijacking_attack'],
    })
  }

  // Always add some info findings
  findings.push({
    id: '4',
    severity: 'info',
    category: 'dependencies',
    title: 'Outdated Dependencies Detected',
    description: 'Some dependencies have known vulnerabilities or are significantly outdated.',
    recommendation: 'Run `npm audit` to check for vulnerabilities and update dependencies to their latest stable versions.',
  })

  return findings
}
