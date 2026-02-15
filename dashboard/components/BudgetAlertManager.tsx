'use client'

import { useState, useEffect } from 'react'
import { BudgetAlert } from '@/components/BudgetAlert'
import { useAuth } from '@/lib/auth'

interface BudgetStatus {
  id: string
  name: string
  current_spend_usd: number
  limit_usd: number
  percent_used: number
  action_on_breach: string
}

interface ThresholdEvent {
  id: string
  budgetId: string
  budgetName: string
  percentUsed: number
  remainingBudget: number
  type: 'warning' | 'critical' | 'exceeded' | 'recovered'
  recommendedModel?: string
  timestamp: Date
}

export function BudgetAlertManager() {
  const { user } = useAuth()
  const [events, setEvents] = useState<ThresholdEvent[]>([])
  const [dismissedEvents, setDismissedEvents] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!user) return

    // Poll for budget status
    const checkBudgets = async () => {
      try {
        const response = await fetch('/api/budgets')
        if (!response.ok) return

        const data = await response.json()
        const budgets: BudgetStatus[] = data.budgets || []

        const newEvents: ThresholdEvent[] = []

        for (const budget of budgets) {
          if (!budget.limit_usd || budget.limit_usd <= 0) continue

          const percentUsed = (budget.current_spend_usd / budget.limit_usd) * 100
          const eventId = `${budget.id}-${Math.floor(percentUsed / 5)}` // Group by 5% increments

          // Skip if already dismissed
          if (dismissedEvents.has(eventId)) continue

          // Determine event type
          let type: ThresholdEvent['type'] | null = null
          if (percentUsed >= 100) {
            type = 'exceeded'
          } else if (percentUsed >= 90) {
            type = 'critical'
          } else if (percentUsed >= 75) {
            type = 'warning'
          }

          if (type) {
            newEvents.push({
              id: eventId,
              budgetId: budget.id,
              budgetName: budget.name,
              percentUsed,
              remainingBudget: Math.max(0, budget.limit_usd - budget.current_spend_usd),
              type,
              recommendedModel: 'gpt-4o-mini', // Recommend cheaper model
              timestamp: new Date(),
            })
          }
        }

        setEvents(newEvents)
      } catch (error) {
        console.error('Error checking budgets:', error)
      }
    }

    // Initial check
    checkBudgets()

    // Poll every 10 seconds
    const interval = setInterval(checkBudgets, 10000)

    return () => clearInterval(interval)
  }, [user, dismissedEvents])

  const handleDismiss = (eventId: string) => {
    setDismissedEvents(prev => new Set([...prev, eventId]))
    setEvents(prev => prev.filter(e => e.id !== eventId))
  }

  const handleDowngrade = async (eventId: string, targetModel: string) => {
    console.log('Downgrading to:', targetModel)
    // In a real implementation, this would call the downgrade API
    handleDismiss(eventId)
  }

  // Only show the most severe event
  const visibleEvent = events.sort((a, b) => {
    const order = { exceeded: 0, critical: 1, warning: 2, recovered: 3 }
    return order[a.type] - order[b.type]
  })[0]

  if (!visibleEvent) return null

  return (
    <BudgetAlert
      event={{
        budgetId: visibleEvent.budgetId,
        budgetName: visibleEvent.budgetName,
        percentUsed: visibleEvent.percentUsed,
        threshold: 80,
        remainingBudget: visibleEvent.remainingBudget,
        type: visibleEvent.type,
        recommendedAction: visibleEvent.type === 'exceeded' ? 'block' : 'continue',
        recommendedModel: visibleEvent.recommendedModel,
        timestamp: visibleEvent.timestamp,
      }}
      onDismiss={() => handleDismiss(visibleEvent.id)}
      onDowngrade={(model) => handleDowngrade(visibleEvent.id, model)}
      autoHide={visibleEvent.type === 'warning'}
      autoHideDelay={15000}
    />
  )
}
