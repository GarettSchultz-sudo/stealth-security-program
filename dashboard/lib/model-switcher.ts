/**
 * ModelSwitcher - Handles dynamic model switching during active sessions
 *
 * Manages model downgrade hierarchy and graceful switching with context preservation.
 */

// Model downgrade hierarchy (expensive → cheaper)
export const MODEL_HIERARCHY: Record<string, string[]> = {
  // Anthropic models
  'claude-opus-4-6': ['claude-sonnet-4-5-20250929', 'claude-3-5-haiku-20241022'],
  'claude-3-opus-20240229': ['claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
  'claude-3-5-sonnet-20241022': ['claude-3-5-haiku-20241022', 'claude-3-haiku-20240307'],
  'claude-sonnet-4-5-20250929': ['claude-3-5-haiku-20241022', 'claude-3-haiku-20240307'],

  // OpenAI models
  'o1-preview': ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
  'o1-mini': ['gpt-4o-mini', 'gpt-3.5-turbo'],
  'gpt-4-turbo': ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
  'gpt-4': ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
  'gpt-4o': ['gpt-4o-mini', 'gpt-3.5-turbo'],
  'gpt-4o-mini': ['gpt-3.5-turbo'],

  // Google models
  'gemini-1.5-pro': ['gemini-1.5-flash', 'gemini-1.0-pro'],
  'gemini-1.5-flash': ['gemini-1.0-pro'],

  // DeepSeek models
  'deepseek-reasoner': ['deepseek-chat'],
}

// Cost multiplier for each model tier (relative to cheapest)
export const MODEL_COST_MULTIPLIERS: Record<string, number> = {
  'claude-opus-4-6': 15,
  'claude-3-opus-20240229': 15,
  'o1-preview': 20,
  'gpt-4-turbo': 10,
  'gpt-4o': 5,
  'claude-sonnet-4-5-20250929': 3,
  'claude-3-5-sonnet-20241022': 3,
  'gpt-4o-mini': 1.5,
  'claude-3-sonnet-20240229': 3,
  'claude-3-5-haiku-20241022': 1,
  'claude-3-haiku-20240307': 1,
  'gpt-3.5-turbo': 1,
}

export interface ActiveSession {
  sessionId: string
  userId: string
  budgetId: string
  originalModel: string
  currentModel: string
  messageCount: number
  totalTokensUsed: number
  totalCost: number
  context: ConversationContext
  startedAt: Date
  lastActivity: Date
  isActive: boolean
  downgradeHistory: ModelDowngradeEvent[]
}

export interface ConversationContext {
  messages: Array<{
    role: 'system' | 'user' | 'assistant'
    content: string
    timestamp: Date
  }>
  systemPrompt?: string
  metadata?: Record<string, unknown>
}

export interface ModelDowngradeEvent {
  fromModel: string
  toModel: string
  reason: 'budget_threshold' | 'manual' | 'auto_enforce'
  threshold?: number
  timestamp: Date
  contextPreserved: boolean
  estimatedSavings: number
}

export interface SwitchResult {
  success: boolean
  previousModel: string
  newModel: string
  contextPreserved: boolean
  estimatedSavings: number
  error?: string
}

export class ModelSwitcher {
  private sessions: Map<string, ActiveSession> = new Map()
  private userSessions: Map<string, Set<string>> = new Map()

  /**
   * Start a new session
   */
  startSession(params: {
    sessionId: string
    userId: string
    budgetId: string
    model: string
    systemPrompt?: string
  }): ActiveSession {
    const session: ActiveSession = {
      sessionId: params.sessionId,
      userId: params.userId,
      budgetId: params.budgetId,
      originalModel: params.model,
      currentModel: params.model,
      messageCount: 0,
      totalTokensUsed: 0,
      totalCost: 0,
      context: {
        messages: [],
        systemPrompt: params.systemPrompt,
      },
      startedAt: new Date(),
      lastActivity: new Date(),
      isActive: true,
      downgradeHistory: [],
    }

    this.sessions.set(params.sessionId, session)

    // Track user sessions
    const userSessionSet = this.userSessions.get(params.userId) || new Set()
    userSessionSet.add(params.sessionId)
    this.userSessions.set(params.userId, userSessionSet)

    return session
  }

  /**
   * Get session by ID
   */
  getSession(sessionId: string): ActiveSession | undefined {
    return this.sessions.get(sessionId)
  }

  /**
   * Get all active sessions for a user
   */
  getUserSessions(userId: string): ActiveSession[] {
    const sessionIds = this.userSessions.get(userId) || new Set()
    return Array.from(sessionIds)
      .map((id) => this.sessions.get(id))
      .filter((s): s is ActiveSession => s !== undefined && s.isActive)
  }

  /**
   * Add a message to session context
   */
  addMessage(
    sessionId: string,
    role: 'system' | 'user' | 'assistant',
    content: string,
    tokens: number = 0,
    cost: number = 0
  ): void {
    const session = this.sessions.get(sessionId)
    if (!session) return

    session.context.messages.push({
      role,
      content,
      timestamp: new Date(),
    })
    session.messageCount++
    session.totalTokensUsed += tokens
    session.totalCost += cost
    session.lastActivity = new Date()
  }

  /**
   * Downgrade model for a session
   */
  downgradeModel(
    sessionId: string,
    reason: ModelDowngradeEvent['reason'],
    targetModel?: string,
    threshold?: number
  ): SwitchResult {
    const session = this.sessions.get(sessionId)
    if (!session) {
      return {
        success: false,
        previousModel: '',
        newModel: '',
        contextPreserved: false,
        estimatedSavings: 0,
        error: 'Session not found',
      }
    }

    const currentModel = session.currentModel
    const downgradeChain = MODEL_HIERARCHY[currentModel]

    if (!downgradeChain || downgradeChain.length === 0) {
      return {
        success: false,
        previousModel: currentModel,
        newModel: currentModel,
        contextPreserved: true,
        estimatedSavings: 0,
        error: 'No downgrade path available for this model',
      }
    }

    // Determine target model
    const newModel = targetModel || downgradeChain[0]

    // Validate target is in downgrade chain
    if (!targetModel && !downgradeChain.includes(newModel)) {
      return {
        success: false,
        previousModel: currentModel,
        newModel: currentModel,
        contextPreserved: true,
        estimatedSavings: 0,
        error: 'Target model is not in the downgrade chain',
      }
    }

    // Calculate estimated savings
    const currentMultiplier = MODEL_COST_MULTIPLIERS[currentModel] || 1
    const newMultiplier = MODEL_COST_MULTIPLIERS[newModel] || 1
    const estimatedSavings = ((currentMultiplier - newMultiplier) / currentMultiplier) * 100

    // Record downgrade event
    const downgradeEvent: ModelDowngradeEvent = {
      fromModel: currentModel,
      toModel: newModel,
      reason,
      threshold,
      timestamp: new Date(),
      contextPreserved: true,
      estimatedSavings,
    }

    // Update session
    session.currentModel = newModel
    session.downgradeHistory.push(downgradeEvent)
    session.lastActivity = new Date()

    return {
      success: true,
      previousModel: currentModel,
      newModel,
      contextPreserved: true,
      estimatedSavings,
    }
  }

  /**
   * Get recommended downgrade model based on budget percentage
   */
  getRecommendedDowngrade(currentModel: string, percentUsed: number): string | null {
    const chain = MODEL_HIERARCHY[currentModel]
    if (!chain || chain.length === 0) return null

    // At 90%+, recommend first downgrade
    if (percentUsed >= 90) return chain[0]

    // At 95%+, recommend second downgrade (if available)
    if (percentUsed >= 95) return chain[1] || chain[0]

    return null
  }

  /**
   * Estimate remaining requests before budget exhaustion
   */
  estimateRemainingRequests(
    currentModel: string,
    remainingBudget: number,
    avgTokensPerRequest: number = 1000
  ): number {
    // Simplified cost estimation (should use actual pricing data)
    const multiplier = MODEL_COST_MULTIPLIERS[currentModel] || 1
    const baseCostPer1kTokens = 0.0005 // Approximate base cost
    const costPerRequest = (avgTokensPerRequest / 1000) * baseCostPer1kTokens * multiplier

    if (costPerRequest <= 0) return Infinity
    return Math.floor(remainingBudget / costPerRequest)
  }

  /**
   * End a session
   */
  endSession(sessionId: string): void {
    const session = this.sessions.get(sessionId)
    if (session) {
      session.isActive = false
      session.lastActivity = new Date()
    }
  }

  /**
   * Clean up expired sessions (older than maxAge ms)
   */
  cleanupExpiredSessions(maxAge: number = 24 * 60 * 60 * 1000): number {
    const now = new Date()
    let cleaned = 0

    for (const [sessionId, session] of this.sessions.entries()) {
      const age = now.getTime() - session.lastActivity.getTime()
      if (age > maxAge || !session.isActive) {
        this.sessions.delete(sessionId)

        const userSessionSet = this.userSessions.get(session.userId)
        if (userSessionSet) {
          userSessionSet.delete(sessionId)
        }

        cleaned++
      }
    }

    return cleaned
  }

  /**
   * Get session statistics
   */
  getStats(): {
    totalSessions: number
    activeSessions: number
    downgradedSessions: number
    totalTokensUsed: number
    totalCost: number
  } {
    let activeSessions = 0
    let downgradedSessions = 0
    let totalTokensUsed = 0
    let totalCost = 0

    for (const session of this.sessions.values()) {
      if (session.isActive) activeSessions++
      if (session.downgradeHistory.length > 0) downgradedSessions++
      totalTokensUsed += session.totalTokensUsed
      totalCost += session.totalCost
    }

    return {
      totalSessions: this.sessions.size,
      activeSessions,
      downgradedSessions,
      totalTokensUsed,
      totalCost,
    }
  }
}

/**
 * Singleton instance
 */
let switcherInstance: ModelSwitcher | null = null

export function getModelSwitcher(): ModelSwitcher {
  if (!switcherInstance) {
    switcherInstance = new ModelSwitcher()
  }
  return switcherInstance
}
