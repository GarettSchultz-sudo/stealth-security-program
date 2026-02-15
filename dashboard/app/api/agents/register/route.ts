import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@supabase/supabase-js'

function getSupabase() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''
  )
}

interface RegisterAgentRequest {
  name: string
  description?: string
  agent_type?: string
  default_model?: string
  default_provider?: string
  budget_limit?: number
  tags?: string[]
  api_key_id?: string
}

/**
 * POST /api/agents/register
 * Register a new agent or update existing one
 */
export async function POST(request: NextRequest) {
  try {
    const body: RegisterAgentRequest = await request.json()

    if (!body.name) {
      return NextResponse.json(
        { error: 'Agent name is required' },
        { status: 400 }
      )
    }

    const supabase = getSupabase()

    // Create agent
    const { data, error } = await supabase
      .from('agents')
      .insert({
        name: body.name,
        description: body.description || null,
        agent_type: body.agent_type || 'custom',
        default_model: body.default_model || null,
        default_provider: body.default_provider || null,
        budget_limit: body.budget_limit || null,
        tags: body.tags || [],
        api_key_id: body.api_key_id || null,
        status: 'active',
        last_heartbeat: new Date().toISOString(),
        last_seen: new Date().toISOString(),
      })
      .select()
      .single()

    if (error) {
      console.error('Error registering agent:', error)
      return NextResponse.json(
        { error: 'Failed to register agent', details: error.message },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      agent: data,
      message: 'Agent registered successfully'
    })
  } catch (error) {
    console.error('Register agent error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * GET /api/agents/register
 * List all registered agents
 */
export async function GET(request: NextRequest) {
  try {
    const supabase = getSupabase()
    const { searchParams } = new URL(request.url)
    const status = searchParams.get('status')
    const agent_type = searchParams.get('type')

    let query = supabase
      .from('agents')
      .select('*')
      .order('last_seen', { ascending: false })

    if (status) {
      query = query.eq('status', status)
    }
    if (agent_type) {
      query = query.eq('agent_type', agent_type)
    }

    const { data, error } = await query

    if (error) {
      return NextResponse.json(
        { error: 'Failed to fetch agents' },
        { status: 500 }
      )
    }

    return NextResponse.json({ agents: data })
  } catch (error) {
    console.error('Get agents error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * PATCH /api/agents/register
 * Update agent status or send heartbeat
 */
export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json()
    const { agent_id, status, heartbeat } = body

    if (!agent_id) {
      return NextResponse.json(
        { error: 'agent_id is required' },
        { status: 400 }
      )
    }

    const supabase = getSupabase()

    const updateData: Record<string, unknown> = {
      last_seen: new Date().toISOString(),
    }

    if (heartbeat) {
      updateData.last_heartbeat = new Date().toISOString()
    }

    if (status) {
      updateData.status = status
    }

    const { data, error } = await supabase
      .from('agents')
      .update(updateData)
      .eq('id', agent_id)
      .select()
      .single()

    if (error) {
      return NextResponse.json(
        { error: 'Failed to update agent' },
        { status: 500 }
      )
    }

    return NextResponse.json({
      success: true,
      agent: data
    })
  } catch (error) {
    console.error('Update agent error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
