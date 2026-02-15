'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Shield,
  TrendingUp,
  TrendingDown,
} from 'lucide-react'

interface TrustScoreCardProps {
  score: number
  riskLevel: string
  recommendation: string
  findingsCount: number
  previousScore?: number
  scanDuration?: number
  filesScanned?: number
  patternsChecked?: number
}

const getScoreColor = (score: number) => {
  if (score >= 80) return 'text-green-500'
  if (score >= 60) return 'text-yellow-500'
  if (score >= 40) return 'text-orange-500'
  return 'text-red-500'
}

const getScoreGradient = (score: number) => {
  if (score >= 80) return 'from-green-500 to-green-600'
  if (score >= 60) return 'from-yellow-500 to-yellow-600'
  if (score >= 40) return 'from-orange-500 to-orange-600'
  return 'from-red-500 to-red-600'
}

const getRiskBadge = (riskLevel: string) => {
  const config: Record<string, { color: string; label: string }> = {
    low: { color: 'bg-green-500', label: 'Low Risk' },
    medium: { color: 'bg-yellow-500', label: 'Medium Risk' },
    high: { color: 'bg-orange-500', label: 'High Risk' },
    critical: { color: 'bg-red-500', label: 'Critical Risk' },
  }
  return config[riskLevel] || config.medium
}

const getRecommendationIcon = (recommendation: string) => {
  switch (recommendation) {
    case 'safe':
      return <CheckCircle2 className="h-5 w-5 text-green-500" />
    case 'avoid':
      return <XCircle className="h-5 w-5 text-red-500" />
    default:
      return <AlertTriangle className="h-5 w-5 text-yellow-500" />
  }
}

export function TrustScoreCard({
  score,
  riskLevel,
  recommendation,
  findingsCount,
  previousScore,
  scanDuration,
  filesScanned,
  patternsChecked,
}: TrustScoreCardProps) {
  const riskConfig = getRiskBadge(riskLevel)
  const scoreChange = previousScore !== undefined ? score - previousScore : undefined

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5" />
          Trust Score
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {/* Main Score */}
          <div className="col-span-2 sm:col-span-1">
            <div className="relative w-32 h-32 mx-auto">
              {/* Background circle */}
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  stroke="currentColor"
                  strokeWidth="12"
                  fill="none"
                  className="text-muted"
                />
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  stroke="url(#scoreGradient)"
                  strokeWidth="12"
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray={`${(score / 100) * 352} 352`}
                  className="transition-all duration-1000"
                />
                <defs>
                  <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" className={`${getScoreColor(score)}`} stopColor="currentColor" />
                    <stop offset="100%" className={`${getScoreColor(score)}`} stopColor="currentColor" />
                  </linearGradient>
                </defs>
              </svg>

              {/* Score text */}
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-4xl font-bold ${getScoreColor(score)}`}>
                  {score}
                </span>
                <span className="text-xs text-muted-foreground">/ 100</span>
              </div>
            </div>

            {/* Score change indicator */}
            {scoreChange !== undefined && (
              <div className="flex items-center justify-center gap-1 mt-2">
                {scoreChange > 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                ) : scoreChange < 0 ? (
                  <TrendingDown className="h-4 w-4 text-red-500" />
                ) : null}
                <span
                  className={`text-sm ${
                    scoreChange > 0
                      ? 'text-green-500'
                      : scoreChange < 0
                      ? 'text-red-500'
                      : 'text-muted-foreground'
                  }`}
                >
                  {scoreChange > 0 ? '+' : ''}
                  {scoreChange} from last scan
                </span>
              </div>
            )}
          </div>

          {/* Risk Level */}
          <div className="text-center">
            <Badge className={`${riskConfig.color} text-white mb-2`}>
              {riskConfig.label}
            </Badge>
            <div className="text-sm text-muted-foreground">Risk Level</div>
          </div>

          {/* Recommendation */}
          <div className="text-center">
            <div className="flex justify-center mb-2">
              {getRecommendationIcon(recommendation)}
            </div>
            <div className="text-sm font-medium capitalize">{recommendation}</div>
            <div className="text-xs text-muted-foreground">Recommendation</div>
          </div>

          {/* Findings Count */}
          <div className="text-center">
            <div className="text-2xl font-bold mb-1">{findingsCount}</div>
            <div className="text-sm text-muted-foreground">Findings</div>
          </div>
        </div>

        {/* Additional Stats */}
        {(scanDuration || filesScanned || patternsChecked) && (
          <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
            {scanDuration && (
              <div className="text-center">
                <div className="text-sm font-medium">
                  {(scanDuration / 1000).toFixed(1)}s
                </div>
                <div className="text-xs text-muted-foreground">Duration</div>
              </div>
            )}
            {filesScanned !== undefined && (
              <div className="text-center">
                <div className="text-sm font-medium">{filesScanned}</div>
                <div className="text-xs text-muted-foreground">Files Scanned</div>
              </div>
            )}
            {patternsChecked !== undefined && (
              <div className="text-center">
                <div className="text-sm font-medium">{patternsChecked}</div>
                <div className="text-xs text-muted-foreground">Patterns Checked</div>
              </div>
            )}
          </div>
        )}

        {/* Progress bar showing score breakdown */}
        <div className="mt-4">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Trust Score Progress</span>
            <span>{score}%</span>
          </div>
          <Progress value={score} className="h-2" />
        </div>
      </CardContent>
    </Card>
  )
}
