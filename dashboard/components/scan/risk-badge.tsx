'use client'

import { cva, type VariantProps } from 'class-variance-authority'
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle,
  XCircle,
  Info,
  type LucideIcon,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900',
  {
    variants: {
      variant: {
        critical: 'bg-red-500/15 text-red-400 border border-red-500/30 focus:ring-red-500',
        high: 'bg-orange-500/15 text-orange-400 border border-orange-500/30 focus:ring-orange-500',
        medium: 'bg-amber-500/15 text-amber-400 border border-amber-500/30 focus:ring-amber-500',
        low: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 focus:ring-emerald-500',
        info: 'bg-blue-500/15 text-blue-400 border border-blue-500/30 focus:ring-blue-500',
      },
      size: {
        sm: 'text-[10px] px-2 py-0.5 rounded',
        md: 'text-xs px-2.5 py-1 rounded-full',
        lg: 'text-sm px-3 py-1.5 rounded-full',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
)

const statusVariants = cva(
  'inline-flex items-center gap-1.5 font-medium transition-colors',
  {
    variants: {
      variant: {
        pending: 'bg-slate-500/15 text-slate-400 border border-slate-500/30',
        running: 'bg-cyan-500/15 text-cyan-400 border border-cyan-500/30',
        completed: 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
        failed: 'bg-red-500/15 text-red-400 border border-red-500/30',
        cancelled: 'bg-slate-600/15 text-slate-500 border border-slate-600/30',
      },
      size: {
        sm: 'text-[10px] px-2 py-0.5 rounded',
        md: 'text-xs px-2.5 py-1 rounded-full',
        lg: 'text-sm px-3 py-1.5 rounded-full',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
)

// Risk level configuration
const riskConfig: Record<
  string,
  { icon: LucideIcon; label: string; description: string }
> = {
  critical: {
    icon: XCircle,
    label: 'Critical',
    description: 'Immediate action required',
  },
  high: {
    icon: AlertTriangle,
    label: 'High',
    description: 'Action recommended soon',
  },
  medium: {
    icon: AlertCircle,
    label: 'Medium',
    description: 'Action suggested',
  },
  low: {
    icon: CheckCircle,
    label: 'Low',
    description: 'Minor concern',
  },
  info: {
    icon: Info,
    label: 'Info',
    description: 'For your information',
  },
}

// Status configuration
const statusConfig: Record<
  string,
  { icon: LucideIcon; label: string; animate?: boolean }
> = {
  pending: {
    icon: AlertCircle,
    label: 'Pending',
  },
  running: {
    icon: AlertCircle,
    label: 'Running',
    animate: true,
  },
  completed: {
    icon: CheckCircle,
    label: 'Completed',
  },
  failed: {
    icon: XCircle,
    label: 'Failed',
  },
  cancelled: {
    icon: AlertCircle,
    label: 'Cancelled',
  },
}

// Risk Badge Component
interface RiskBadgeProps extends VariantProps<typeof badgeVariants> {
  level: 'critical' | 'high' | 'medium' | 'low' | 'info' | null
  showIcon?: boolean
  showTooltip?: boolean
  pulse?: boolean
  className?: string
}

export function RiskBadge({
  level,
  showIcon = true,
  pulse = false,
  size = 'md',
  className,
}: RiskBadgeProps) {
  if (!level) return null

  const config = riskConfig[level] || riskConfig.info
  const Icon = config.icon

  return (
    <span
      className={cn(
        badgeVariants({ variant: level, size }),
        pulse && level === 'critical' && 'animate-pulse',
        className
      )}
      role="status"
      aria-label={`Risk level: ${config.label}`}
      title={config.description}
    >
      {showIcon && (
        <Icon
          size={size === 'sm' ? 10 : size === 'md' ? 12 : 14}
          className={cn(pulse && level === 'critical' && 'animate-ping absolute')}
        />
      )}
      {showIcon && pulse && level === 'critical' && (
        <Icon size={size === 'sm' ? 10 : size === 'md' ? 12 : 14} />
      )}
      <span>{config.label}</span>
    </span>
  )
}

// Status Badge Component
interface StatusBadgeProps extends VariantProps<typeof statusVariants> {
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  showIcon?: boolean
  className?: string
}

export function StatusBadge({
  status,
  showIcon = true,
  size = 'md',
  className,
}: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.pending
  const Icon = config.icon

  return (
    <span
      className={cn(statusVariants({ variant: status, size }), className)}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      {config.animate ? (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-current" />
        </span>
      ) : (
        showIcon && <Icon size={size === 'sm' ? 10 : size === 'md' ? 12 : 14} />
      )}
      <span>{config.label}</span>
    </span>
  )
}

// Profile Badge Component
interface ProfileBadgeProps {
  profile: 'quick' | 'standard' | 'deep' | 'comprehensive'
  showCost?: boolean
  className?: string
}

const profileConfig: Record<
  string,
  { label: string; cost: number; color: string; description: string }
> = {
  quick: {
    label: 'Quick',
    cost: 1,
    color: 'bg-slate-500/15 text-slate-400 border-slate-500/30',
    description: 'Basic pattern checks',
  },
  standard: {
    label: 'Standard',
    cost: 2,
    color: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    description: 'Recommended for most uses',
  },
  deep: {
    label: 'Deep',
    cost: 5,
    color: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    description: 'Full SAST analysis',
  },
  comprehensive: {
    label: 'Comprehensive',
    cost: 10,
    color: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    description: 'Includes external API checks',
  },
}

export function ProfileBadge({
  profile,
  showCost = true,
  className,
}: ProfileBadgeProps) {
  const config = profileConfig[profile] || profileConfig.standard

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium',
        config.color,
        className
      )}
      title={config.description}
    >
      <span>{config.label}</span>
      {showCost && (
        <span className="text-[10px] opacity-75">· {config.cost} credits</span>
      )}
    </span>
  )
}

// Recommendation Badge Component
interface RecommendationBadgeProps {
  recommendation: 'safe' | 'caution' | 'avoid' | null
  className?: string
}

const recommendationConfig: Record<
  string,
  { label: string; color: string; icon: LucideIcon }
> = {
  safe: {
    label: 'Safe to Use',
    color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    icon: CheckCircle,
  },
  caution: {
    label: 'Use with Caution',
    color: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    icon: AlertTriangle,
  },
  avoid: {
    label: 'Avoid',
    color: 'bg-red-500/15 text-red-400 border-red-500/30',
    icon: XCircle,
  },
}

export function RecommendationBadge({
  recommendation,
  className,
}: RecommendationBadgeProps) {
  if (!recommendation) return null

  const config = recommendationConfig[recommendation]
  const Icon = config.icon

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full border font-medium',
        config.color,
        className
      )}
      role="status"
      aria-label={`Recommendation: ${config.label}`}
    >
      <Icon size={12} />
      <span>{config.label}</span>
    </span>
  )
}
