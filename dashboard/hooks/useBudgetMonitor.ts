/**
 * useBudgetMonitor - React hook for real-time budget monitoring
 *
 * Provides real-time budget updates via Supabase Realtime
 * and exposes threshold events for UI notifications.
 */

'use client'

import { useEffect, useState, useCallback, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { createClient, RealtimeChannel } from '@supabase/supabase-js'

export interface BudgetStatus {
  budgetId: string
  name: string
  limit: number
  current: number
  percentUsed: number
  remaining: number
  period: string
  recommendedAction: 'continue' | 'downgrade' | 'block'
  recommendedModel: string | null
  downgradeAvailable: boolean
  estimatedRemainingRequests: number
  activeRequests: number
  resetAt: string
}

export interface BudgetSummary {
  totalBudgets: number
  totalLimit: number
  totalSpent: number
  totalRemaining: number
  breachedCount: number
  anyBreached: boolean
  allBreached: boolean
}

export interface BudgetThresholdEvent {
  type: 'warning' | 'critical' | 'exceeded' | 'recovered'
  budgetId: string
  budgetName: string
  percentUsed: number
  threshold: number
  remainingBudget: number
  timestamp: Date
  recommendedAction: 'continue' | 'downgrade' | 'block'
  recommendedModel?: string
}

interface UseBudgetMonitorOptions {
  /** Polling interval in ms (default: 5000) */
  pollInterval?: number
  /** Enable Supabase Realtime (default: true) */
  enableRealtime?: boolean
  /** Threshold percentages to emit events at */
  thresholds?: number[]
  /** Called when a threshold is crossed */
  onThreshold?: (event: BudgetThresholdEvent) => void
  /** Called on any budget state change */
  onStateChange?: (status: BudgetStatus, summary: BudgetSummary) => void
}

interface BudgetMonitorReturn {
  budgets: BudgetStatus[]
  summary: BudgetSummary | null
  isLoading: boolean
  error: string | null
  lastUpdated: Date | null
  realtimeConnected: boolean
  refresh: () => Promise<void>
  downgradeModel: (sessionId: string, targetModel: string) => Promise<{ success: boolean; savingsPercent: number }>
}

export function useBudgetMonitor(
  options: UseBudgetMonitorOptions = {}
): BudgetMonitorReturn {
  const {
    pollInterval = 5000,
    enableRealtime = true,
    thresholds = [50, 75, 90, 95, 100],
    onThreshold,
    onStateChange,
  } = options

  const [budgets, setBudgets] = useState<BudgetStatus[]>([])
  const [summary, setSummary] = useState<BudgetSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [realtimeConnected, setRealtimeConnected] = useState(false)

  const queryClient = useQueryClient()
  const channelRef = useRef<RealtimeChannel | null>(null)
  const emittedThresholdsRef = useRef<Map<string, Set<number>>>(new Map())
  const pollingRef = useRef<NodeJS.Timeout | null>(null)

  // Fetch budget status
  const fetchBudgetStatus = useCallback(async () => {
    try {
      const response = await fetch('/api/budget/status')
      if (!response.ok) {
        throw new Error('Failed to fetch budget status')
      }
      const data = await response.json()

      const prevBudgets = budgets
      setBudgets(data.budgets)
      setSummary(data.summary)
      setLastUpdated(new Date())
      setError(null)

      // Check for threshold crossings
      if (prevBudgets.length > 0) {
        for (const budget of data.budgets) {
          const prev = prevBudgets.find((b) => b.budgetId === budget.budgetId)
          if (prev) {
            checkThresholds(prev, budget)
          }
        }
      }

      // Call onStateChange callback
      if (onStateChange) {
        for (const budget of data.budgets) {
          onStateChange(budget, data.summary)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setIsLoading(false)
    }
  }, [budgets, onStateChange])

  // Check if thresholds have been crossed
  const checkThresholds = useCallback(
    (prev: BudgetStatus, current: BudgetStatus) => {
      const emitted = emittedThresholdsRef.current.get(current.budgetId) || new Set()

      for (const threshold of thresholds) {
        const crossedUp = prev.percentUsed < threshold && current.percentUsed >= threshold
        const crossedDown = prev.percentUsed >= threshold && current.percentUsed < threshold

        if (crossedUp && !emitted.has(threshold)) {
          emitted.add(threshold)
          emittedThresholdsRef.current.set(current.budgetId, emitted)

          const event: BudgetThresholdEvent = {
            type: getEventType(threshold),
            budgetId: current.budgetId,
            budgetName: current.name,
            percentUsed: current.percentUsed,
            threshold,
            remainingBudget: current.remaining,
            timestamp: new Date(),
            recommendedAction: current.recommendedAction,
            recommendedModel: current.recommendedModel || undefined,
          }

          onThreshold?.(event)
        }

        if (crossedDown && threshold === 50) {
          // Reset emitted thresholds on recovery
          emittedThresholdsRef.current.set(current.budgetId, new Set())

          onThreshold?.({
            type: 'recovered',
            budgetId: current.budgetId,
            budgetName: current.name,
            percentUsed: current.percentUsed,
            threshold: 50,
            remainingBudget: current.remaining,
            timestamp: new Date(),
            recommendedAction: 'continue',
          })
        }
      }
    },
    [thresholds, onThreshold]
  )

  // Manual model downgrade
  const downgradeModel = useCallback(
    async (sessionId: string, targetModel: string) => {
      const response = await fetch('/api/models/downgrade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId, targetModel, preserveContext: true }),
      })

      if (!response.ok) {
        throw new Error('Failed to downgrade model')
      }

      const data = await response.json()
      return {
        success: data.success,
        savingsPercent: data.downgrade?.savingsPercent || 0,
      }
    },
    []
  )

  // Set up polling
  useEffect(() => {
    fetchBudgetStatus()

    pollingRef.current = setInterval(fetchBudgetStatus, pollInterval)

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
    }
  }, [fetchBudgetStatus, pollInterval])

  // Set up realtime subscription
  useEffect(() => {
    if (!enableRealtime) return

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

    if (!supabaseUrl || !supabaseKey) return

    const supabase = createClient(supabaseUrl, supabaseKey)

    const channel = supabase
      .channel('budget-updates')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'request_logs' },
        () => {
          // Invalidate and refetch on new request logs
          queryClient.invalidateQueries({ queryKey: ['stats'] })
          queryClient.invalidateQueries({ queryKey: ['budgets'] })
          fetchBudgetStatus()
        }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'budgets' },
        () => {
          fetchBudgetStatus()
        }
      )
      .subscribe((status) => {
        setRealtimeConnected(status === 'SUBSCRIBED')
      })

    channelRef.current = channel

    return () => {
      if (channelRef.current) {
        supabase.removeChannel(channelRef.current)
      }
    }
  }, [enableRealtime, fetchBudgetStatus, queryClient])

  return {
    budgets,
    summary,
    isLoading,
    error,
    lastUpdated,
    realtimeConnected,
    refresh: fetchBudgetStatus,
    downgradeModel,
  }
}

function getEventType(threshold: number): BudgetThresholdEvent['type'] {
  if (threshold >= 100) return 'exceeded'
  if (threshold >= 90) return 'critical'
  return 'warning'
}

export default useBudgetMonitor
