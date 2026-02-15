'use client'

import { useState, useMemo } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  AlertTriangle,
  Bug,
  Shield,
  Search,
  Filter,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Download,
} from 'lucide-react'

// Types
export interface Finding {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  title: string
  description?: string
  resource?: string
  remediation?: string
  cve_ids?: string[]
  cwe_ids?: string[]
  scanner: string
  cvss_score?: number
  confidence?: number
  evidence?: Record<string, unknown>
  references?: string[]
}

interface FindingsListProps {
  findings: Finding[]
  title?: string
  description?: string
  showExport?: boolean
  onExport?: (format: 'json' | 'csv' | 'sarif') => void
}

// Severity config
const SEVERITY_CONFIG = {
  critical: {
    label: 'Critical',
    color: 'bg-red-500 text-white',
    icon: AlertTriangle,
    priority: 0,
  },
  high: {
    label: 'High',
    color: 'bg-orange-500 text-white',
    icon: AlertTriangle,
    priority: 1,
  },
  medium: {
    label: 'Medium',
    color: 'bg-yellow-500 text-black',
    icon: Shield,
    priority: 2,
  },
  low: {
    label: 'Low',
    color: 'bg-blue-500 text-white',
    icon: Shield,
    priority: 3,
  },
  info: {
    label: 'Info',
    color: 'bg-gray-500 text-white',
    icon: Bug,
    priority: 4,
  },
}

export function FindingsList({
  findings,
  title = 'Security Findings',
  description,
  showExport = true,
  onExport,
}: FindingsListProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'severity' | 'scanner' | 'cvss'>('severity')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [expandedFinding, setExpandedFinding] = useState<string | null>(null)

  // Filter and sort findings
  const filteredFindings = useMemo(() => {
    let result = [...findings]

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      result = result.filter(
        (f) =>
          f.title.toLowerCase().includes(query) ||
          f.description?.toLowerCase().includes(query) ||
          f.resource?.toLowerCase().includes(query) ||
          f.scanner.toLowerCase().includes(query)
      )
    }

    // Severity filter
    if (severityFilter !== 'all') {
      result = result.filter((f) => f.severity === severityFilter)
    }

    // Sort
    result.sort((a, b) => {
      let comparison = 0

      switch (sortBy) {
        case 'severity':
          comparison =
            SEVERITY_CONFIG[a.severity].priority -
            SEVERITY_CONFIG[b.severity].priority
          break
        case 'scanner':
          comparison = a.scanner.localeCompare(b.scanner)
          break
        case 'cvss':
          comparison = (b.cvss_score || 0) - (a.cvss_score || 0)
          break
      }

      return sortOrder === 'asc' ? comparison : -comparison
    })

    return result
  }, [findings, searchQuery, severityFilter, sortBy, sortOrder])

  // Count by severity
  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {
      critical: 0,
      high: 0,
      medium: 0,
      low: 0,
      info: 0,
    }
    findings.forEach((f) => {
      counts[f.severity] = (counts[f.severity] || 0) + 1
    })
    return counts
  }, [findings])

  const toggleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  const toggleExpanded = (id: string) => {
    setExpandedFinding(expandedFinding === id ? null : id)
  }

  const defaultExport = (format: 'json' | 'csv' | 'sarif') => {
    let content: string
    let mimeType: string
    let filename: string

    if (format === 'json') {
      content = JSON.stringify(findings, null, 2)
      mimeType = 'application/json'
      filename = 'findings.json'
    } else if (format === 'csv') {
      const headers = ['Title', 'Severity', 'Scanner', 'Resource', 'CVE', 'CVSS']
      const rows = findings.map((f) => [
        f.title,
        f.severity,
        f.scanner,
        f.resource || '',
        f.cve_ids?.join('; ') || '',
        f.cvss_score?.toString() || '',
      ])
      content = [headers, ...rows].map((r) => r.join(',')).join('\n')
      mimeType = 'text/csv'
      filename = 'findings.csv'
    } else {
      // SARIF format
      content = JSON.stringify(
        {
          $schema: 'https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json',
          version: '2.1.0',
          runs: [
            {
              tool: {
                driver: {
                  name: 'ClawShield',
                  version: '1.0.0',
                },
              },
              results: findings.map((f) => ({
                ruleId: f.id,
                level: f.severity === 'critical' || f.severity === 'high' ? 'error' : 'warning',
                message: {
                  text: f.title,
                },
                locations: f.resource
                  ? [
                      {
                        physicalLocation: {
                          artifactLocation: {
                            uri: f.resource,
                          },
                        },
                      },
                    ]
                  : [],
              })),
            },
          ],
        },
        null,
        2
      )
      mimeType = 'application/json'
      filename = 'findings.sarif'
    }

    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExport = onExport || defaultExport

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              {title}
            </CardTitle>
            {description && <CardDescription>{description}</CardDescription>}
          </div>
          {showExport && findings.length > 0 && (
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('json')}
              >
                <Download className="h-4 w-4 mr-1" />
                JSON
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('csv')}
              >
                <Download className="h-4 w-4 mr-1" />
                CSV
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('sarif')}
              >
                <Download className="h-4 w-4 mr-1" />
                SARIF
              </Button>
            </div>
          )}
        </div>

        {/* Severity Summary */}
        <div className="flex flex-wrap gap-2 mt-4">
          {Object.entries(severityCounts).map(([severity, count]) => (
            <Badge
              key={severity}
              variant={count > 0 ? 'default' : 'outline'}
              className={`${count > 0 ? SEVERITY_CONFIG[severity as keyof typeof SEVERITY_CONFIG].color : ''}`}
            >
              {SEVERITY_CONFIG[severity as keyof typeof SEVERITY_CONFIG].label}: {count}
            </Badge>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search findings..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>

          <Select value={severityFilter} onValueChange={setSeverityFilter}>
            <SelectTrigger className="w-[150px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="high">High</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="low">Low</SelectItem>
              <SelectItem value="info">Info</SelectItem>
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => toggleSort('severity')}
          >
            Severity
            {sortBy === 'severity' && (
              sortOrder === 'asc' ? (
                <ChevronUp className="h-4 w-4 ml-1" />
              ) : (
                <ChevronDown className="h-4 w-4 ml-1" />
              )
            )}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => toggleSort('scanner')}
          >
            Scanner
            {sortBy === 'scanner' && (
              sortOrder === 'asc' ? (
                <ChevronUp className="h-4 w-4 ml-1" />
              ) : (
                <ChevronDown className="h-4 w-4 ml-1" />
              )
            )}
          </Button>
        </div>

        {/* Findings List */}
        {filteredFindings.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            {findings.length === 0
              ? 'No findings to display'
              : 'No findings match your filters'}
          </div>
        ) : (
          <div className="space-y-3">
            {filteredFindings.map((finding) => {
              const config = SEVERITY_CONFIG[finding.severity]
              const Icon = config.icon
              const isExpanded = expandedFinding === finding.id

              return (
                <div
                  key={finding.id}
                  className="border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div
                    className="p-4 cursor-pointer"
                    onClick={() => toggleExpanded(finding.id)}
                  >
                    <div className="flex items-start gap-3">
                      <Badge className={config.color}>
                        <Icon className="h-3 w-3 mr-1" />
                        {config.label}
                      </Badge>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium truncate">{finding.title}</h4>
                          {finding.cvss_score !== undefined && (
                            <Badge variant="outline" className="shrink-0">
                              CVSS: {finding.cvss_score.toFixed(1)}
                            </Badge>
                          )}
                        </div>

                        <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                          <span>{finding.scanner}</span>
                          {finding.resource && (
                            <>
                              <span>•</span>
                              <span className="truncate font-mono text-xs">
                                {finding.resource}
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      {isExpanded ? (
                        <ChevronUp className="h-5 w-5 text-muted-foreground shrink-0" />
                      ) : (
                        <ChevronDown className="h-5 w-5 text-muted-foreground shrink-0" />
                      )}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="px-4 pb-4 pt-0 border-t bg-muted/30">
                      <div className="space-y-4 pt-4">
                        {finding.description && (
                          <div>
                            <h5 className="font-medium text-sm mb-1">Description</h5>
                            <p className="text-sm text-muted-foreground">
                              {finding.description}
                            </p>
                          </div>
                        )}

                        {finding.remediation && (
                          <div className="p-3 bg-green-50 dark:bg-green-950 rounded-lg">
                            <h5 className="font-medium text-sm mb-1 text-green-700 dark:text-green-300">
                              Remediation
                            </h5>
                            <p className="text-sm">{finding.remediation}</p>
                          </div>
                        )}

                        {(finding.cve_ids?.length || finding.cwe_ids?.length) && (
                          <div className="flex flex-wrap gap-2">
                            {finding.cve_ids?.map((cve) => (
                              <a
                                key={cve}
                                href={`https://nvd.nist.gov/vuln/detail/${cve}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline"
                              >
                                {cve}
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            ))}
                            {finding.cwe_ids?.map((cwe) => (
                              <a
                                key={cwe}
                                href={`https://cwe.mitre.org/data/definitions/${cwe.replace('CWE-', '')}.html`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline"
                              >
                                {cwe}
                                <ExternalLink className="h-3 w-3" />
                              </a>
                            ))}
                          </div>
                        )}

                        {finding.evidence && Object.keys(finding.evidence).length > 0 && (
                          <div>
                            <h5 className="font-medium text-sm mb-1">Evidence</h5>
                            <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                              {JSON.stringify(finding.evidence, null, 2)}
                            </pre>
                          </div>
                        )}

                        {finding.references?.length && (
                          <div>
                            <h5 className="font-medium text-sm mb-1">References</h5>
                            <div className="space-y-1">
                              {finding.references.map((ref, i) => (
                                <a
                                  key={i}
                                  href={ref}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="block text-xs text-blue-500 hover:underline truncate"
                                >
                                  {ref}
                                </a>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
