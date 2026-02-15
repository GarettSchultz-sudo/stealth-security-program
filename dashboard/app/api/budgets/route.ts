import { NextRequest, NextResponse } from 'next/server'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL!
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY!

async function getCurrentUser(request: NextRequest) {
  const cookieStore = await cookies()

  const supabase = createServerClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
    cookies: {
      getAll() {
        return cookieStore.getAll()
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => cookieStore.set(name, value))
      },
    },
  })

  const { data: { session } } = await supabase.auth.getSession()
  return session?.user
}

function getAdminClient() {
  return createServerClient(SUPABASE_URL, SUPABASE_SERVICE_KEY!, {
    cookies: {
      getAll: () => [],
      setAll: () => {},
    },
  })
}

// GET - List all budgets for user
export async function GET(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const supabase = getAdminClient()

    const { data, error } = await supabase
      .from('budgets')
      .select('*')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    return NextResponse.json({ budgets: data })
  } catch (error) {
    console.error('Error fetching budgets:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}

// POST - Create new budget
export async function POST(request: NextRequest) {
  try {
    const user = await getCurrentUser(request)
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { name, period, limit_usd, scope, scope_identifier, action_on_breach } = body

    // Validate required fields
    if (!name || !period || !limit_usd) {
      return NextResponse.json(
        { error: 'Missing required fields: name, period, limit_usd' },
        { status: 400 }
      )
    }

    // Validate period
    if (!['daily', 'weekly', 'monthly'].includes(period)) {
      return NextResponse.json(
        { error: 'Invalid period. Must be: daily, weekly, or monthly' },
        { status: 400 }
      )
    }

    // Validate scope
    if (scope && !['global', 'agent', 'model', 'workflow'].includes(scope)) {
      return NextResponse.json(
        { error: 'Invalid scope. Must be: global, agent, model, or workflow' },
        { status: 400 }
      )
    }

    // Validate action_on_breach
    if (action_on_breach && !['alert', 'block', 'downgrade'].includes(action_on_breach)) {
      return NextResponse.json(
        { error: 'Invalid action_on_breach. Must be: alert, block, or downgrade' },
        { status: 400 }
      )
    }

    // Calculate reset_at based on period
    const now = new Date()
    let reset_at: Date

    switch (period) {
      case 'daily':
        reset_at = new Date(now)
        reset_at.setUTCDate(reset_at.getUTCDate() + 1)
        reset_at.setUTCHours(0, 0, 0, 0)
        break
      case 'weekly':
        reset_at = new Date(now)
        reset_at.setUTCDate(reset_at.getUTCDate() + (7 - reset_at.getUTCDay()))
        reset_at.setUTCHours(0, 0, 0, 0)
        break
      case 'monthly':
        reset_at = new Date(now)
        reset_at.setUTCMonth(reset_at.getUTCMonth() + 1)
        reset_at.setUTCDate(1)
        reset_at.setUTCHours(0, 0, 0, 0)
        break
      default:
        reset_at = new Date(now)
    }

    const supabase = getAdminClient()

    const { data, error } = await supabase
      .from('budgets')
      .insert({
        user_id: user.id,
        name,
        period,
        limit_usd: parseFloat(limit_usd),
        scope: scope || 'global',
        scope_identifier: scope_identifier || null,
        action_on_breach: action_on_breach || 'alert',
        reset_at: reset_at.toISOString(),
        current_spend_usd: 0,
        is_active: true,
      })
      .select()
      .single()

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 400 })
    }

    return NextResponse.json({ budget: data }, { status: 201 })
  } catch (error) {
    console.error('Error creating budget:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
