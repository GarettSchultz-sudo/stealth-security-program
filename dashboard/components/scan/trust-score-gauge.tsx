'use client'

import { useEffect, useState, useMemo } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const gaugeVariants = cva('relative inline-flex items-center justify-center', {
  variants: {
    size: {
      sm: 'w-9 h-9',
      md: 'w-12 h-12',
      lg: 'w-20 h-20',
      xl: 'w-28 h-28',
    },
  },
  defaultVariants: {
    size: 'md',
  },
})

interface TrustScoreGaugeProps extends VariantProps<typeof gaugeVariants> {
  score: number | null
  label?: string
  showValue?: boolean
  animated?: boolean
  className?: string
}

// Score ranges and their corresponding colors
const getScoreConfig = (score: number) => {
  if (score >= 80) return { color: '#10b981', label: 'Excellent', textColor: 'text-emerald-500' }
  if (score >= 60) return { color: '#22c55e', label: 'Good', textColor: 'text-green-500' }
  if (score >= 40) return { color: '#eab308', label: 'Fair', textColor: 'text-yellow-500' }
  if (score >= 20) return { color: '#f97316', label: 'Poor', textColor: 'text-orange-500' }
  return { color: '#ef4444', label: 'Critical', textColor: 'text-red-500' }
}

// Size configurations
const sizeConfig = {
  sm: { diameter: 36, strokeWidth: 4, fontSize: 'text-xs', labelSize: 'text-[10px]' },
  md: { diameter: 48, strokeWidth: 5, fontSize: 'text-sm', labelSize: 'text-xs' },
  lg: { diameter: 80, strokeWidth: 7, fontSize: 'text-xl', labelSize: 'text-xs' },
  xl: { diameter: 112, strokeWidth: 10, fontSize: 'text-3xl', labelSize: 'text-sm' },
}

export function TrustScoreGauge({
  score,
  label,
  showValue = true,
  animated = true,
  size = 'md',
  className,
}: TrustScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)

  const config = sizeConfig[size || 'md']
  const radius = (config.diameter - config.strokeWidth) / 2
  const circumference = 2 * Math.PI * radius

  const currentScore = animated ? animatedScore : (score ?? 0)
  const scoreConfig = getScoreConfig(currentScore)
  const progress = (currentScore / 100) * circumference
  const offset = circumference - progress

  // Animate score on mount or when score changes
  useEffect(() => {
    if (!animated || score === null) {
      setAnimatedScore(score ?? 0)
      return
    }

    setIsAnimating(true)
    const duration = 800 // ms
    const startTime = Date.now()
    const startScore = animatedScore
    const targetScore = score

    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)

      // Easing function (ease-out-expo)
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)

      setAnimatedScore(Math.round(startScore + (targetScore - startScore) * eased))

      if (progress < 1) {
        requestAnimationFrame(animate)
      } else {
        setIsAnimating(false)
      }
    }

    requestAnimationFrame(animate)
  }, [score, animated])

  if (score === null) {
    return (
      <div className={cn(gaugeVariants({ size }), className)}>
        <svg
          width={config.diameter}
          height={config.diameter}
          className="transform -rotate-90"
        >
          <circle
            cx={config.diameter / 2}
            cy={config.diameter / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={config.strokeWidth}
            fill="none"
            className="text-slate-700"
            strokeDasharray="4 4"
          />
        </svg>
        <span className={cn('absolute font-mono font-bold text-slate-500', config.fontSize)}>
          —
        </span>
      </div>
    )
  }

  return (
    <div className={cn('inline-flex flex-col items-center', className)}>
      <div
        className={cn(gaugeVariants({ size }))}
        role="meter"
        aria-valuenow={currentScore}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Trust score: ${currentScore} out of 100 - ${scoreConfig.label}`}
      >
        <svg
          width={config.diameter}
          height={config.diameter}
          className="transform -rotate-90"
        >
          {/* Background track */}
          <circle
            cx={config.diameter / 2}
            cy={config.diameter / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={config.strokeWidth}
            fill="none"
            className="text-slate-800"
          />
          {/* Progress arc */}
          <circle
            cx={config.diameter / 2}
            cy={config.diameter / 2}
            r={radius}
            stroke={scoreConfig.color}
            strokeWidth={config.strokeWidth}
            fill="none"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className={cn(
              'transition-all duration-300 ease-out',
              isAnimating && 'will-change-[stroke-dashoffset]'
            )}
            style={{
              filter: `drop-shadow(0 0 6px ${scoreConfig.color}40)`,
            }}
          />
        </svg>
        {showValue && (
          <span
            className={cn(
              'absolute font-mono font-bold transition-colors duration-300',
              config.fontSize,
              scoreConfig.textColor
            )}
          >
            {currentScore}
          </span>
        )}
      </div>
      {label && (
        <span className={cn('mt-1 text-slate-400 font-medium', config.labelSize)}>
          {label}
        </span>
      )}
    </div>
  )
}

// Linear progress variant for alternative display
interface TrustScoreBarProps {
  score: number | null
  showLabel?: boolean
  className?: string
}

export function TrustScoreBar({ score, showLabel = true, className }: TrustScoreBarProps) {
  const [animatedWidth, setAnimatedWidth] = useState(0)

  useEffect(() => {
    if (score === null) return
    const timer = setTimeout(() => setAnimatedWidth(score), 50)
    return () => clearTimeout(timer)
  }, [score])

  if (score === null) {
    return (
      <div className={cn('w-full', className)}>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
          <div className="h-full w-full bg-slate-700/50 rounded-full" />
        </div>
      </div>
    )
  }

  const config = getScoreConfig(score)

  return (
    <div className={cn('w-full', className)}>
      <div className="flex items-center justify-between mb-1.5">
        {showLabel && (
          <span className="text-xs text-slate-400 font-medium">Trust Score</span>
        )}
        <span className={cn('text-sm font-mono font-bold', config.textColor)}>
          {score}
        </span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${animatedWidth}%`,
            backgroundColor: config.color,
            boxShadow: `0 0 12px ${config.color}50`,
          }}
        />
      </div>
      <div className="flex justify-between mt-1">
        <span className="text-[10px] text-slate-600">0</span>
        <span className={cn('text-[10px] font-medium', config.textColor)}>
          {config.label}
        </span>
        <span className="text-[10px] text-slate-600">100</span>
      </div>
    </div>
  )
}
