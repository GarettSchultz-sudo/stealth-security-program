/**
 * Agent Task Tracker Library
 *
 * A client-side library for AI agents to report their tasks and status
 * to the ClawShell tracking system.
 *
 * Usage:
 * ```typescript
 * import { AgentTracker } from '@/lib/agent-tracker'
 *
 * const tracker = new AgentTracker({
 *   name: 'My Coding Agent',
 *   baseUrl: 'https://your-clawshell-instance.com'
 * })
 *
 * // Start a task
 * const task = await tracker.startTask({
 *   task_id: 'task-123',
 *   title: 'Implement user authentication',
 *   task_type: 'coding'
 * })
 *
 * // Report progress
 * await task.updateProgress(50)
 * await task.addTokens(1000, 500, 0.002)
 *
 * // Complete task
 * await task.complete({ result_summary: 'Successfully implemented auth' })
 * ```
 */

export interface AgentConfig {
  name: string
  description?: string
  agent_type?: 'claude-code' | 'cursor' | 'aider' | 'copilot' | 'custom'
  default_model?: string
  default_provider?: string
  tags?: string[]
  baseUrl?: string
  apiKey?: string
}

export interface TaskConfig {
  task_id: string
  title?: string
  description?: string
  task_type?: 'coding' | 'research' | 'chat' | 'analysis' | 'general'
  parent_task_id?: string
  model?: string
  provider?: string
  metadata?: Record<string, unknown>
}

export interface TaskUpdateOptions {
  status?: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled'
  progress_percent?: number
  input_tokens?: number
  output_tokens?: number
  cache_read_tokens?: number
  cache_creation_tokens?: number
  cost_usd?: number
  api_calls?: number
  result_summary?: string
  error_message?: string
  metadata?: Record<string, unknown>
}

export interface TaskCompleteOptions {
  result_summary?: string
  error_message?: string
  metadata?: Record<string, unknown>
}

export interface AgentInfo {
  id: string
  name: string
  status: string
  agent_type: string
}

export interface TaskInfo {
  id: string
  task_id: string
  title: string
  status: string
  progress_percent: number
  cost_usd: number
  input_tokens: number
  output_tokens: number
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
}

/**
 * Represents a tracked task with convenience methods
 */
export class TrackedTask {
  private agentId: string
  private taskId: string
  private baseUrl: string
  private apiKey?: string
  private taskData: TaskInfo | null = null

  constructor(agentId: string, taskId: string, baseUrl: string, apiKey?: string) {
    this.agentId = agentId
    this.taskId = taskId
    this.baseUrl = baseUrl
    this.apiKey = apiKey
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseUrl}${endpoint}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    }

    if (this.apiKey) {
      headers['Authorization'] = `Bearer ${this.apiKey}`
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }))
      throw new Error(error.error || `HTTP ${response.status}`)
    }

    return response.json()
  }

  /**
   * Update task status, progress, or metrics
   */
  async update(options: TaskUpdateOptions): Promise<TaskInfo> {
    const result = await this.request('/api/agents/tasks', {
      method: 'PATCH',
      body: JSON.stringify({
        agent_id: this.agentId,
        task_id: this.taskId,
        ...options,
      }),
    })

    this.taskData = result.task
    if (!this.taskData) {
      throw new Error('Failed to create task')
    }
    return this.taskData
  }

  /**
   * Update progress percentage
   */
  async updateProgress(percent: number): Promise<TaskInfo> {
    return this.update({
      progress_percent: percent,
      status: 'running',
    })
  }

  /**
   * Add token usage (increments existing values)
   */
  async addTokens(
    input: number,
    output: number,
    costUsd?: number,
    cacheRead?: number,
    cacheCreation?: number
  ): Promise<TaskInfo> {
    return this.update({
      input_tokens: input,
      output_tokens: output,
      cost_usd: costUsd,
      cache_read_tokens: cacheRead,
      cache_creation_tokens: cacheCreation,
      api_calls: 1,
    })
  }

  /**
   * Mark task as running
   */
  async start(): Promise<TaskInfo> {
    return this.update({ status: 'running' })
  }

  /**
   * Mark task as paused
   */
  async pause(): Promise<TaskInfo> {
    return this.update({ status: 'paused' })
  }

  /**
   * Mark task as completed
   */
  async complete(options: TaskCompleteOptions = {}): Promise<TaskInfo> {
    return this.update({
      status: 'completed',
      progress_percent: 100,
      ...options,
    })
  }

  /**
   * Mark task as failed
   */
  async fail(error: string, metadata?: Record<string, unknown>): Promise<TaskInfo> {
    return this.update({
      status: 'failed',
      error_message: error,
      metadata,
    })
  }

  /**
   * Get current task info
   */
  getData(): TaskInfo | null {
    return this.taskData
  }
}

/**
 * Main Agent Tracker class
 */
export class AgentTracker {
  private config: AgentConfig
  private baseUrl: string
  private agentId: string | null = null
  private heartbeatInterval: NodeJS.Timeout | null = null
  private activeTasks: Map<string, TrackedTask> = new Map()

  constructor(config: AgentConfig) {
    this.config = config
    this.baseUrl = config.baseUrl || process.env.NEXT_PUBLIC_APP_URL || ''
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseUrl}${endpoint}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    }

    if (this.config.apiKey) {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }))
      throw new Error(error.error || `HTTP ${response.status}`)
    }

    return response.json()
  }

  /**
   * Register this agent with the tracking system
   */
  async register(): Promise<AgentInfo> {
    const result = await this.request('/api/agents/register', {
      method: 'POST',
      body: JSON.stringify({
        name: this.config.name,
        description: this.config.description,
        agent_type: this.config.agent_type || 'custom',
        default_model: this.config.default_model,
        default_provider: this.config.default_provider,
        tags: this.config.tags || [],
      }),
    })

    this.agentId = result.agent.id

    // Start heartbeat
    this.startHeartbeat()

    return result.agent
  }

  /**
   * Ensure agent is registered
   */
  private async ensureRegistered(): Promise<string> {
    if (!this.agentId) {
      const agent = await this.register()
      return agent.id
    }
    return this.agentId
  }

  /**
   * Start sending heartbeats
   */
  private startHeartbeat(intervalMs: number = 30000) {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
    }

    this.heartbeatInterval = setInterval(async () => {
      if (this.agentId) {
        try {
          await this.request('/api/agents/register', {
            method: 'PATCH',
            body: JSON.stringify({
              agent_id: this.agentId,
              heartbeat: true,
            }),
          })
        } catch (error) {
          console.error('Heartbeat failed:', error)
        }
      }
    }, intervalMs)
  }

  /**
   * Stop sending heartbeats
   */
  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
  }

  /**
   * Start tracking a new task
   */
  async startTask(config: TaskConfig): Promise<TrackedTask> {
    const agentId = await this.ensureRegistered()

    const result = await this.request('/api/agents/tasks', {
      method: 'POST',
      body: JSON.stringify({
        agent_id: agentId,
        ...config,
      }),
    })

    const task = new TrackedTask(
      agentId,
      config.task_id,
      this.baseUrl,
      this.config.apiKey
    )

    // Start the task
    await task.start()

    this.activeTasks.set(config.task_id, task)
    return task
  }

  /**
   * Get an existing task by ID
   */
  getTask(taskId: string): TrackedTask | undefined {
    return this.activeTasks.get(taskId)
  }

  /**
   * Get all active tasks
   */
  getActiveTasks(): TrackedTask[] {
    return Array.from(this.activeTasks.values())
  }

  /**
   * Fetch all tasks for this agent
   */
  async fetchTasks(status?: string): Promise<TaskInfo[]> {
    const agentId = await this.ensureRegistered()

    const params = new URLSearchParams({ agent_id: agentId })
    if (status) {
      params.append('status', status)
    }

    const result = await this.request(`/api/agents/tasks?${params}`)
    return result.tasks
  }

  /**
   * Get agent utilization metrics
   */
  async getUtilization(): Promise<{
    active_tasks: number
    tasks_24h: number
    cost_24h: number
    total_tasks_completed: number
    total_tasks_failed: number
  }> {
    const agentId = await this.ensureRegistered()

    const result = await this.request(`/api/agents/utilization?agent_id=${agentId}`)
    return result
  }

  /**
   * Update agent status
   */
  async setStatus(status: 'active' | 'paused' | 'disabled'): Promise<void> {
    const agentId = await this.ensureRegistered()

    await this.request('/api/agents/register', {
      method: 'PATCH',
      body: JSON.stringify({
        agent_id: agentId,
        status,
      }),
    })
  }

  /**
   * Cleanup and disconnect
   */
  async disconnect(): Promise<void> {
    this.stopHeartbeat()

    // Complete or fail any remaining active tasks
    for (const task of this.activeTasks.values()) {
      try {
        await task.fail('Agent disconnected')
      } catch (error) {
        console.error('Failed to close task:', error)
      }
    }

    this.activeTasks.clear()
  }
}

/**
 * Create a tracker instance with default configuration
 */
export function createAgentTracker(config: AgentConfig): AgentTracker {
  return new AgentTracker(config)
}

/**
 * Quick helper to track a single async operation
 */
export async function trackOperation<T>(
  tracker: AgentTracker,
  taskConfig: TaskConfig,
  operation: (task: TrackedTask) => Promise<T>
): Promise<T> {
  const task = await tracker.startTask(taskConfig)

  try {
    const result = await operation(task)
    await task.complete({ result_summary: 'Operation completed successfully' })
    return result
  } catch (error) {
    await task.fail(error instanceof Error ? error.message : 'Operation failed')
    throw error
  }
}
