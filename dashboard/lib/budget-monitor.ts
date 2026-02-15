/**
 * BudgetMonitor - Real-time budget tracking with Supabase Realtime
 *
 * Tracks spending in real-time by subscribing to request_logs inserts
 * and emitting events at configurable thresholds.
 */

import { createClient } from '@supabase/supabase-js'
import type { RealtimeChannel } from '@supabase/supabase-js'

export interface BudgetState {
  budgetId: string
  userId: string
  limit: number
  currentSpend: number
  percentUsed: number
  periodStart: Date
  periodEnd: Date
  activeRequests: number
  lastUpdated: Date
}

export interface BudgetThresholdEvent {
  type: 'warning' | 'critical' | 'exceeded' | 'recovered'
  budgetId: string
  percentUsed: number
  threshold: number
  remainingBudget: number
  timestamp: Date
  recommendedAction: 'continue' | 'downgrade' | 'block'
  recommendedModel?: string
}

export interface BudgetMonitorConfig {
  supabaseUrl: string
  supabaseKey: string
  thresholds?: number[] // Default: [50, 75, 90, 95, 100]
  onThreshold?: (event: BudgetThresholdEvent) => void
  onStateChange?: (state: BudgetState) => void
}

type BudgetEventType = 'INSERT' | 'UPDATE' | 'DELETE' | '*'

interface RequestLogPayload {
  eventType: BudgetEventType
  new: {
    id: string
    user_id: string
    cost_usd: number
    model: string
    created_at: string
  }
  old: null
  table: string
  schema: string
}

export class BudgetMonitor {
  private supabase: ReturnType<typeof createClient>
  private channel: RealtimeChannel | null = null
  private thresholds: number[]
  private onThreshold: (event: BudgetThresholdEvent) => void
  private onStateChange: (state: BudgetState) => void
  private budgetCache: Map<string, BudgetState> = new Map()
  private emittedThresholds: Map<string, Set<number>> = new Map()
  private activeRequests: Map<string, number> = new Map()

  constructor(config: BudgetMonitorConfig) {
    this.supabase = createClient(config.supabaseUrl, config.supabaseKey)
    this.thresholds = config.thresholds || [50, 75, 90, 95, 100]
    this.onThreshold = config.onThreshold || (() => {})
    this.onStateChange = config.onStateChange || (() => {})
  }

  /**
   * Start monitoring budgets for a user
   */
  async startMonitoring(userId: string): Promise<void> {
    // Fetch initial budget states
    await this.fetchBudgetStates(userId)

    // Subscribe to request_logs changes
    this.channel = this.supabase
      .channel(`budget-monitor-${userId}`)
      .on<RequestLogPayload>(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'request_logs',
          filter: `user_id=eq.${userId}`,
        },
        (payload) => this.handleRequestLog(payload as unknown as RequestLogPayload)
      )
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'budgets',
          filter: `user_id=eq.${userId}`,
        },
        () => this.fetchBudgetStates(userId)
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          console.log(`Budget monitor active for user ${userId}`)
        }
      })
  }

  /**
   * Stop monitoring
   */
  async stopMonitoring(): Promise<void> {
    if (this.channel) {
      await this.supabase.removeChannel(this.channel)
      this.channel = null
    }
    this.budgetCache.clear()
    this.emittedThresholds.clear()
  }

  /**
   * Get current budget state
   */
  getBudgetState(budgetId: string): BudgetState | undefined {
    return this.budgetCache.get(budgetId)
  }

  /**
   * Get all budget states for a user
   */
  getAllBudgetStates(userId: string): BudgetState[] {
    return Array.from(this.budgetCache.values()).filter(
      (state) => state.userId === userId
    )
  }

  /**
   * Track an active request (for request counting)
   */
  trackRequestStart(budgetId: string): string {
    const requestId = crypto.randomUUID()
    const count = this.activeRequests.get(budgetId) || 0
    this.activeRequests.set(budgetId, count + 1)
    this.updateActiveRequestCount(budgetId)
    return requestId
  }

  /**
   * Mark a request as complete
   */
  trackRequestEnd(budgetId: string): void {
    const count = this.activeRequests.get(budgetId) || 0
    if (count > 0) {
      this.activeRequests.set(budgetId, count - 1)
    }
    this.updateActiveRequestCount(budgetId)
  }

  /**
   * Fetch current budget states from database
   */
  private async fetchBudgetStates(userId: string): Promise<void> {
    const { data: budgets, error } = await this.supabase
      .from('budgets')
      .select('*')
      .eq('user_id', userId)
      .eq('is_active', true) as { data: Array<{
        id: string
        user_id: string
        limit_usd: number
        current_spend_usd: number
        created_at: string
        reset_at: string
      }> | null, error: unknown }

    if (error) {
      console.error('Error fetching budget states:', error)
      return
    }

    for (const budget of budgets || []) {
      const state: BudgetState = {
        budgetId: budget.id,
        userId: budget.user_id,
        limit: budget.limit_usd,
        currentSpend: budget.current_spend_usd || 0,
        percentUsed: (budget.current_spend_usd / budget.limit_usd) * 100,
        periodStart: new Date(budget.created_at),
        periodEnd: new Date(budget.reset_at),
        activeRequests: this.activeRequests.get(budget.id) || 0,
        lastUpdated: new Date(),
      }
      this.budgetCache.set(budget.id, state)
      this.onStateChange(state)
    }
  }

  /**
   * Handle incoming request log (new spend)
   */
  private async handleRequestLog(payload: RequestLogPayload): Promise<void> {
    const { new: log } = payload
    const cost = log.cost_usd || 0

    // Update all applicable budgets for this user
    for (const [budgetId, state] of this.budgetCache.entries()) {
      if (state.userId !== log.user_id) continue

      // Check if this budget applies (simplified - in production, check scope)
      const newState = {
        ...state,
        currentSpend: state.currentSpend + cost,
        percentUsed: ((state.currentSpend + cost) / state.limit) * 100,
        lastUpdated: new Date(),
      }

      this.budgetCache.set(budgetId, newState)
      this.onStateChange(newState)
      this.checkThresholds(newState)
    }
  }

  /**
   * Check if any thresholds have been crossed
   */
  private checkThresholds(state: BudgetState): void {
    const emitted = this.emittedThresholds.get(state.budgetId) || new Set()

    for (const threshold of this.thresholds) {
      if (state.percentUsed >= threshold && !emitted.has(threshold)) {
        emitted.add(threshold)
        this.emittedThresholds.set(state.budgetId, emitted)

        const event: BudgetThresholdEvent = {
          type: this.getEventType(threshold),
          budgetId: state.budgetId,
          percentUsed: state.percentUsed,
          threshold,
          remainingBudget: Math.max(0, state.limit - state.currentSpend),
          timestamp: new Date(),
          recommendedAction: this.getRecommendedAction(threshold),
          recommendedModel: this.getRecommendedModel(state.percentUsed),
        }

        this.onThreshold(event)
      }
    }

    // Check for recovery (if spend was reset)
    if (state.percentUsed < 50 && emitted.has(75)) {
      const recoveryEvent: BudgetThresholdEvent = {
        type: 'recovered',
        budgetId: state.budgetId,
        percentUsed: state.percentUsed,
        threshold: 50,
        remainingBudget: state.limit - state.currentSpend,
        timestamp: new Date(),
        recommendedAction: 'continue',
      }
      this.onThreshold(recoveryEvent)
      this.emittedThresholds.set(state.budgetId, new Set())
    }
  }

  /**
   * Get event type based on threshold
   */
  private getEventType(threshold: number): BudgetThresholdEvent['type'] {
    if (threshold >= 100) return 'exceeded'
    if (threshold >= 90) return 'critical'
    return 'warning'
  }

  /**
   * Get recommended action based on threshold
   */
  private getRecommendedAction(threshold: number): BudgetThresholdEvent['recommendedAction'] {
    if (threshold >= 100) return 'block'
    if (threshold >= 90) return 'downgrade'
    return 'continue'
  }

  /**
   * Get recommended model based on current spend
   */
  private getRecommendedModel(percentUsed: number): string | undefined {
    if (percentUsed >= 95) return 'claude-3-haiku-20240307'
    if (percentUsed >= 90) return 'claude-3-sonnet-20240229'
    if (percentUsed >= 80) return 'claude-3-sonnet-20240229'
    return undefined
  }

  /**
   * Update active request count in state
   */
  private updateActiveRequestCount(budgetId: string): void {
    const state = this.budgetCache.get(budgetId)
    if (state) {
      state.activeRequests = this.activeRequests.get(budgetId) || 0
      this.budgetCache.set(budgetId, state)
      this.onStateChange(state)
    }
  }
}

/**
 * Singleton instance for server-side use
 */
let monitorInstance: BudgetMonitor | null = null

export function getBudgetMonitor(config?: BudgetMonitorConfig): BudgetMonitor {
  if (!monitorInstance && config) {
    monitorInstance = new BudgetMonitor(config)
  }
  if (!monitorInstance) {
    throw new Error('BudgetMonitor not initialized. Call with config first.')
  }
  return monitorInstance
}
