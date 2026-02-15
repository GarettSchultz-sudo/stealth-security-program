'use client'

import { useEffect, useState, useRef } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { ArrowUpRight, ArrowDownRight, type LucideIcon, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

const cardVariants = cva(
  'relative overflow-hidden rounded-xl border backdrop-blur-sm transition-all duration-300 group',
  {
    variants: {
      accent: {
        cyan: 'border-cyan-500/20 hover:border-cyan-500/40 shadow-cyan-500/5',
        emerald: 'border-emerald-500/20 hover:border-emerald-500/40 shadow-emerald-500/5',
        amber: 'border-amber-500/20 hover:border-amber-500/40 shadow-amber-500/5',
        rose: 'border-rose-500/20 hover:border-rose-500/40 shadow-rose-500/5',
        purple: 'border-purple-500/20 hover:border-purple-500/40 shadow-purple-500/5',
        slate: 'border-slate-500/20 hover:border-slate-500/40 shadow-slate-500/5',
      },
    },
    defaultVariants: {
      accent: 'slate',
    },
  }
)

const iconVariants = cva('p-2 rounded-lg', {
  variants: {
    accent: {
      cyan: 'bg-cyan-500/10 text-cyan-400',
      emerald: 'bg-emerald-500/10 text-emerald-400',
      amber: 'bg-amber-500/10 text-amber-400',
      rose: 'bg-rose-500/10 text-rose-400',
      purple: 'bg-purple-500/10 text-purple-400',
      slate: 'bg-slate-500/10 text-slate-400',
    },
  },
  defaultVariants: {
    accent: 'slate',
  },
})

// Animated counter hook
function useAnimatedCounter(end: number, duration: number = 1000, enabled: boolean = true) {
  const [count, setCount] = useState(0)
  const countRef = useRef(0)
  const startTimeRef = useRef<number | null>(null)

  useEffect(() => {
    if (!enabled) {
      setCount(end)
      return
    }

    const animate = (timestamp: number) => {
      if (!startTimeRef.current) {
        startTimeRef.current = timestamp
      }

      const progress = Math.min((timestamp - startTimeRef.current) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
      const currentCount = Math.round(eased * end)

      if (currentCount !== countRef.current) {
        countRef.current = currentCount
        setCount(currentCount)
      }

      if (progress < 1) {
        requestAnimationFrame(animate)
      }
    }

    requestAnimationFrame(animate)

    return () => {
      startTimeRef.current = null
    }
  }, [end, duration, enabled])

  return count
}

// Stat Card Props
interface StatCardProps extends VariantProps<typeof cardVariants> {
  label: string
  value: string | number
  icon: LucideIcon
  trend?: {
    value: number
    label?: string
  }
  prefix?: string
  suffix?: string
  animateValue?: boolean
  className?: string
}

export function StatCard({
  label,
  value,
  icon: Icon,
  trend,
  prefix,
  suffix,
  animateValue = true,
  accent = 'slate',
  className,
}: StatCardProps) {
  const numericValue = typeof value === 'number' ? value : parseInt(String(value), 10) || 0
  const animatedCount = useAnimatedCounter(numericValue, 800, animateValue)
  const displayValue = animateValue ? animatedCount : numericValue

  const trendDirection = trend?.value && trend.value > 0 ? 'up' : trend?.value && trend.value < 0 ? 'down' : 'neutral'
  const trendColor = trendDirection === 'up' ? 'text-emerald-400' : trendDirection === 'down' ? 'text-rose-400' : 'text-slate-400'

  return (
    <div className={cn(cardVariants({ accent }), 'bg-slate-900/80 p-5 shadow-lg', className)}>
      {/* Gradient overlay on hover */}
      <div className="absolute inset-0 bg-gradient-to-br from-slate-800/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

      <div className="relative">
        {/* Header with label and icon */}
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-slate-400 font-medium">{label}</span>
          <div className={cn(iconVariants({ accent }))}>
            <Icon size={18} />
          </div>
        </div>

        {/* Value */}
        <div className="flex items-baseline gap-1">
          {prefix && <span className="text-lg text-slate-500">{prefix}</span>}
          <span className="text-3xl font-bold text-white font-mono tracking-tight">
            {typeof value === 'number' ? displayValue : value}
          </span>
          {suffix && <span className="text-lg text-slate-500">{suffix}</span>}
        </div>

        {/* Trend indicator */}
        {trend && (
          <div className={cn('flex items-center gap-1 mt-2 text-xs', trendColor)}>
            {trendDirection === 'up' && <ArrowUpRight size={12} />}
            {trendDirection === 'down' && <ArrowDownRight size={12} />}
            {trendDirection === 'neutral' && <Minus size={12} />}
            <span>
              {trend.value > 0 && '+'}
              {trend.value}
              {trend.label && <span className="text-slate-500 ml-1">{trend.label}</span>}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

// Stats Grid Component
interface StatsGridProps {
  children: React.ReactNode
  columns?: 2 | 3 | 4 | 5 | 6
  className?: string
}

export function StatsGrid({ children, columns = 4, className }: StatsGridProps) {
  const gridCols = {
    2: 'grid-cols-2',
    3: 'grid-cols-3',
    4: 'grid-cols-2 md:grid-cols-4',
    5: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-5',
    6: 'grid-cols-2 md:grid-cols-3 lg:grid-cols-6',
  }

  return (
    <div className={cn('grid gap-4', gridCols[columns], className)}>
      {children}
    </div>
  )
}

// Skeleton loader for stat cards
export function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-900/80 p-5 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="h-4 w-20 bg-slate-700/50 rounded" />
        <div className="h-8 w-8 bg-slate-700/50 rounded-lg" />
      </div>
      <div className="h-9 w-16 bg-slate-700/50 rounded" />
      <div className="h-3 w-24 bg-slate-700/50 rounded mt-2" />
    </div>
  )
}
