import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
  )
}

interface CreateTaskRequest {
  agent_id: string
  task_id: string
  task_type?: string
  title?: string
  description?: string
  parent_task_id?: string
  model?: string
  provider?: string
  metadata?: Record<string, unknown>
}

interface UpdateTaskRequest {
  agent_id: string
  task_id: string
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

/**
 * POST /api/agents/tasks
 * Create a new task or start tracking
 */
export async function POST(request: NextRequest) {
  try {
    const body: CreateTaskRequest = await request.json()

    if (!body.agent_id || !body.task_id) {
      return NextResponse.json(
        { error: 'agent_id and task_id are required' },
        { status: 400 }
      )
    }

    const supabase = getSupabase()

    // Verify agent exists
    const { data: agent, error: agentError } = await supabase
      .from('agents')
      .select('id')
      .eq('id', body.agent_id)
      .single()

    if (agentError || !agent) {
      return NextResponse.json(
        { error: 'Agent not found' },
        { status: 404 }
      )
    }

    // Create task
    const { data, error } = await supabase
      .from('agent_tasks')
      .insert({
        agent_id: body.agent_id,
        task_id: body.task_id,
        task_type: body.task_type || 'general',
        title: body.title || `Task ${body.task_id}`,
        description: body.description || null,
        parent_task_id: body.parent_task_id || null,
        model: body.model || null,
        provider: body.provider || null,
        status: 'pending',
        metadata: body.metadata || {},
      })
      .select()
      .single()

    if (error) {
      // Check if it's a duplicate task
      if (error.code === '23505') {
        // Task exists, return it
        const { data: existing } = await supabase
          .from('agent_tasks')
          .select('*')
          .eq('agent_id', body.agent_id)
          .eq('task_id', body.task_id)
          .single()

        return NextResponse.json({
          success: true,
          task: existing,
          message: 'Task already exists'
        })
      }

      console.error('Error creating task:', error)
      return NextResponse.json(
        { error: 'Failed to create task', details: error.message },
        { status: 500 }
      )
    }

    // Create task event
    await supabase
      .from('task_events')
      .insert({
        task_id: data.id,
        agent_id: body.agent_id,
        event_type: 'created',
        event_data: { title: body.title, task_type: body.task_type }
      })

    return NextResponse.json({
      success: true,
      task: data,
      message: 'Task created successfully'
    })
  } catch (error) {
    console.error('Create task error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * GET /api/agents/tasks
 * List tasks with optional filters
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = getSupabase()
    const { searchParams } = new URL(request.url)

    const agent_id = searchParams.get('agent_id')
    const status = searchParams.get('status')
    const active_only = searchParams.get('active_only') === 'true'
    const limit = parseInt(searchParams.get('limit') || '50')

    let query = supabase
      .from('agent_tasks')
      .select(`
        *,
        agents(name, agent_type)
      `)
      .order('created_at', { ascending: false })
      .limit(limit)

    if (agent_id) {
      query = query.eq('agent_id', agent_id)
    }

    if (status) {
      query = query.eq('status', status)
    }

    if (active_only) {
      query = query.in('status', ['pending', 'running'])
    }

    const { data, error } = await query

    if (error) {
      console.error('Error fetching tasks:', error)
      return NextResponse.json(
        { error: 'Failed to fetch tasks' },
        { status: 500 }
      )
    }

    return NextResponse.json({ tasks: data })
  } catch (error) {
    console.error('Get tasks error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * PATCH /api/agents/tasks
 * Update task status, progress, or metrics
 */
export async function PATCH(request: NextRequest) {
  try {
    const body: UpdateTaskRequest = await request.json()

    if (!body.agent_id || !body.task_id) {
      return NextResponse.json(
        { error: 'agent_id and task_id are required' },
        { status: 400 }
      )
    }

    const supabase = getSupabase()

    // Find the task
    const { data: existingTask, error: findError } = await supabase
      .from('agent_tasks')
      .select('*')
      .eq('agent_id', body.agent_id)
      .eq('task_id', body.task_id)
      .single()

    if (findError || !existingTask) {
      return NextResponse.json(
        { error: 'Task not found' },
        { status: 404 }
      )
    }

    // Build update object
    const updateData: Record<string, unknown> = {}

    if (body.status) {
      updateData.status = body.status

      // Handle status-specific updates
      if (body.status === 'running' && !existingTask.started_at) {
        updateData.started_at = new Date().toISOString()
      }

      if (body.status === 'completed' || body.status === 'failed') {
        updateData.completed_at = new Date().toISOString()
        if (!existingTask.duration_ms && existingTask.started_at) {
          const start = new Date(existingTask.started_at).getTime()
          const end = Date.now()
          updateData.duration_ms = end - start
        }
      }
    }

    if (body.progress_percent !== undefined) {
      updateData.progress_percent = Math.min(100, Math.max(0, body.progress_percent))
    }

    if (body.input_tokens !== undefined) {
      updateData.input_tokens = existingTask.input_tokens + body.input_tokens
    }

    if (body.output_tokens !== undefined) {
      updateData.output_tokens = existingTask.output_tokens + body.output_tokens
    }

    if (body.cache_read_tokens !== undefined) {
      updateData.cache_read_tokens = (existingTask.cache_read_tokens || 0) + body.cache_read_tokens
    }

    if (body.cache_creation_tokens !== undefined) {
      updateData.cache_creation_tokens = (existingTask.cache_creation_tokens || 0) + body.cache_creation_tokens
    }

    if (body.cost_usd !== undefined) {
      updateData.cost_usd = existingTask.cost_usd + body.cost_usd
    }

    if (body.api_calls !== undefined) {
      updateData.api_calls = existingTask.api_calls + body.api_calls
    }

    if (body.result_summary !== undefined) {
      updateData.result_summary = body.result_summary
    }

    if (body.error_message !== undefined) {
      updateData.error_message = body.error_message
    }

    if (body.metadata !== undefined) {
      updateData.metadata = { ...existingTask.metadata, ...body.metadata }
    }

    // Perform update
    const { data, error } = await supabase
      .from('agent_tasks')
      .update(updateData)
      .eq('id', existingTask.id)
      .select()
      .single()

    if (error) {
      console.error('Error updating task:', error)
      return NextResponse.json(
        { error: 'Failed to update task' },
        { status: 500 }
      )
    }

    // Create task event for status changes
    if (body.status && body.status !== existingTask.status) {
      await supabase
        .from('task_events')
        .insert({
          task_id: existingTask.id,
          agent_id: body.agent_id,
          event_type: body.status,
          event_data: {
            previous_status: existingTask.status,
            progress: body.progress_percent,
            error: body.error_message
          }
        })
    }

    return NextResponse.json({
      success: true,
      task: data
    })
  } catch (error) {
    console.error('Update task error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * DELETE /api/agents/tasks
 * Cancel/delete a task
 */
export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const agent_id = searchParams.get('agent_id')
    const task_id = searchParams.get('task_id')

    if (!agent_id || !task_id) {
      return NextResponse.json(
        { error: 'agent_id and task_id are required' },
        { status: 400 }
      )
    }

    const supabase = getSupabase()

    // Update status to cancelled instead of deleting
    const { error } = await supabase
      .from('agent_tasks')
      .update({
        status: 'cancelled',
        completed_at: new Date().toISOString()
      })
      .eq('agent_id', agent_id)
      .eq('task_id', task_id)

    if (error) {
      return NextResponse.json(
        { error: 'Failed to cancel task' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      message: 'Task cancelled'
    })
  } catch (error) {
    console.error('Cancel task error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
