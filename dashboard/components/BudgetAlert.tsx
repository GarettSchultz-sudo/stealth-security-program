'use client'

import { useEffect, useState } from 'react'
import { X, AlertTriangle, TrendingDown, CheckCircle, Zap, ArrowDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/input'
import type { BudgetThresholdEvent } from '@/hooks/useBudgetMonitor'

interface BudgetAlertProps {
  event: BudgetThresholdEvent
  onDismiss: () => void
  onDowngrade?: (targetModel: string) => void
  autoHide?: boolean
  autoHideDelay?: number
}

export function BudgetAlert({
  event,
  onDismiss,
  onDowngrade,
  autoHide = false,
  autoHideDelay = 10000,
}: BudgetAlertProps) {
  const [visible, setVisible] = useState(true)
  const [isDowngrading, setIsDowngrading] = useState(false)

  useEffect(() => {
    if (autoHide && event.type !== 'exceeded') {
      const timer = setTimeout(() => {
        setVisible(false)
        setTimeout(onDismiss, 300)
      }, autoHideDelay)
      return () => clearTimeout(timer)
    }
  }, [autoHide, autoHideDelay, event.type, onDismiss])

  const handleDowngrade = async () => {
    if (!event.recommendedModel || !onDowngrade) return
    setIsDowngrading(true)
    try {
      await onDowngrade(event.recommendedModel)
    } finally {
      setIsDowngrading(false)
    }
  }

  const config = getAlertConfig(event)

  if (!visible) return null

  return (
    <div
      className={cn(
        'fixed bottom-4 right-4 max-w-md z-50 transition-all duration-300',
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'
      )}
    >
      <div
        className={cn(
          'rounded-lg border shadow-lg p-4',
          config.bgColor,
          config.borderColor
        )}
      >
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className={cn('p-2 rounded-lg', config.iconBg)}>
            <config.icon size={20} className={config.iconColor} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <h4 className={cn('font-semibold', config.titleColor)}>
              {config.title}
            </h4>
            <p className="text-sm text-slate-300 mt-1">
              {event.budgetName} is at{' '}
              <span className="font-mono font-bold">{event.percentUsed.toFixed(1)}%</span>
              {' '}of limit
            </p>

            {/* Progress bar */}
            <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all', config.progressBarColor)}
                style={{ width: `${Math.min(100, event.percentUsed)}%` }}
              />
            </div>

            {/* Remaining budget */}
            <p className="text-xs text-slate-400 mt-2">
              ${event.remainingBudget.toFixed(2)} remaining
            </p>

            {/* Action button */}
            {event.recommendedModel && onDowngrade && (
              <Button
                variant="primary"
                size="sm"
                icon={ArrowDown}
                onClick={handleDowngrade}
                loading={isDowngrading}
                className="mt-3"
              >
                Switch to {event.recommendedModel}
              </Button>
            )}
          </div>

          {/* Dismiss button */}
          <button
            onClick={() => {
              setVisible(false)
              setTimeout(onDismiss, 300)
            }}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}

function getAlertConfig(event: BudgetThresholdEvent) {
  switch (event.type) {
    case 'exceeded':
      return {
        icon: X,
        title: 'Budget Exceeded',
        bgColor: 'bg-rose-500/10',
        borderColor: 'border-rose-500/30',
        iconBg: 'bg-rose-500/20',
        iconColor: 'text-rose-400',
        titleColor: 'text-rose-400',
        progressBarColor: 'bg-rose-500',
      }
    case 'critical':
      return {
        icon: AlertTriangle,
        title: 'Budget Critical',
        bgColor: 'bg-amber-500/10',
        borderColor: 'border-amber-500/30',
        iconBg: 'bg-amber-500/20',
        iconColor: 'text-amber-400',
        titleColor: 'text-amber-400',
        progressBarColor: 'bg-amber-500',
      }
    case 'recovered':
      return {
        icon: CheckCircle,
        title: 'Budget Recovered',
        bgColor: 'bg-emerald-500/10',
        borderColor: 'border-emerald-500/30',
        iconBg: 'bg-emerald-500/20',
        iconColor: 'text-emerald-400',
        titleColor: 'text-emerald-400',
        progressBarColor: 'bg-emerald-500',
      }
    default:
      return {
        icon: TrendingDown,
        title: 'Budget Warning',
        bgColor: 'bg-cyan-500/10',
        borderColor: 'border-cyan-500/30',
        iconBg: 'bg-cyan-500/20',
        iconColor: 'text-cyan-400',
        titleColor: 'text-cyan-400',
        progressBarColor: 'bg-cyan-500',
      }
  }
}

/**
 * BudgetAlertContainer - Manages multiple budget alerts
 */
interface BudgetAlertContainerProps {
  events: BudgetThresholdEvent[]
  onDismiss: (eventId: string) => void
  onDowngrade?: (eventId: string, targetModel: string) => void
}

export function BudgetAlertContainer({
  events,
  onDismiss,
  onDowngrade,
}: BudgetAlertContainerProps) {
  // Show max 3 alerts at a time
  const visibleEvents = events.slice(-3)

  return (
    <div className="fixed bottom-4 right-4 z-50 space-y-2">
      {visibleEvents.map((event, index) => (
        <div
          key={`${event.budgetId}-${event.timestamp.getTime()}`}
          style={{ transform: `translateY(${(visibleEvents.length - 1 - index) * -4}px)` }}
        >
          <BudgetAlert
            event={event}
            onDismiss={() => onDismiss(`${event.budgetId}-${event.timestamp.getTime()}`)}
            onDowngrade={
              onDowngrade
                ? (model) => onDowngrade(`${event.budgetId}-${event.timestamp.getTime()}`, model)
                : undefined
            }
          />
        </div>
      ))}
    </div>
  )
}

export default BudgetAlert
