'use client'

import { cn } from '@/lib/utils'
import { cva, type VariantProps } from 'class-variance-authority'

const progressVariants = cva('h-full rounded-full transition-all duration-300', {
  variants: {
    variant: {
      default: 'bg-cyan-500',
      success: 'bg-emerald-500',
      warning: 'bg-amber-500',
      danger: 'bg-rose-500',
      purple: 'bg-purple-500',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

interface ProgressBarProps extends VariantProps<typeof progressVariants> {
  value: number
  max?: number
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function ProgressBar({
  value,
  max = 100,
  variant,
  showLabel = false,
  size = 'md',
  className,
}: ProgressBarProps) {
  const percent = Math.min(100, Math.max(0, (value / max) * 100))

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-1.5',
    lg: 'h-2',
  }

  // Auto-select variant based on percentage
  const autoVariant = variant || (
    percent >= 100 ? 'success' :
    percent >= 75 ? 'default' :
    percent >= 50 ? 'warning' :
    'danger'
  )

  return (
    <div className={cn('w-full', className)}>
      <div className={cn('w-full bg-slate-700/50 rounded-full overflow-hidden', sizeClasses[size])}>
        <div
          className={progressVariants({ variant: autoVariant })}
          style={{ width: `${percent}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between mt-1 text-xs text-slate-400">
          <span>{value.toLocaleString()}</span>
          <span>{percent.toFixed(0)}%</span>
        </div>
      )}
    </div>
  )
}

// Circular progress for compact displays
interface CircularProgressProps {
  value: number
  max?: number
  size?: number
  strokeWidth?: number
  className?: string
}

export function CircularProgress({
  value,
  max = 100,
  size = 32,
  strokeWidth = 3,
  className,
}: CircularProgressProps) {
  const percent = Math.min(100, Math.max(0, (value / max) * 100))
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (percent / 100) * circumference

  return (
    <div className={cn('relative inline-flex items-center justify-center', className)}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(71, 85, 105, 0.5)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="text-cyan-500 transition-all duration-300"
        />
      </svg>
      {size >= 24 && (
        <span className="absolute text-xs font-mono text-white">
          {Math.round(percent)}%
        </span>
      )}
    </div>
  )
}

// Status dot indicator
interface StatusDotProps {
  status: 'active' | 'paused' | 'idle' | 'error'
  pulse?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function StatusDot({ status, pulse = false, size = 'md', className }: StatusDotProps) {
  const statusColors = {
    active: 'bg-emerald-400',
    paused: 'bg-amber-400',
    idle: 'bg-slate-400',
    error: 'bg-rose-400',
  }

  const sizeClasses = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-3 h-3',
  }

  return (
    <span className={cn('relative flex', className)}>
      <span
        className={cn(
          'rounded-full',
          statusColors[status],
          sizeClasses[size]
        )}
      />
      {pulse && status === 'active' && (
        <span
          className={cn(
            'absolute inset-0 rounded-full animate-ping',
            statusColors[status]
          )}
        />
      )}
    </span>
  )
}
